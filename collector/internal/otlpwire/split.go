// Package otlpwire splits an OTLP export request into smaller ones without knowing what
// a span is.
//
// The collector is forbidden to parse span semantics (architecture §2.1, ADR-0001), and
// it also has to keep every published message under a size budget (§3.2), splitting
// oversized export requests rather than truncating them. Those two requirements meet
// here, and the way they are reconciled is that this package understands the protobuf
// *wire format* and exactly six field numbers of the OTLP envelope — nothing about
// attributes, resources, trace ids, timestamps, or GenAI conventions.
//
// The envelope, from opentelemetry-proto:
//
//	ExportTraceServiceRequest { repeated ResourceSpans resource_spans = 1 }
//	ResourceSpans { Resource resource = 1; repeated ScopeSpans scope_spans = 2; string schema_url = 3 }
//	ScopeSpans    { InstrumentationScope scope = 1; repeated Span spans = 2; string schema_url = 3 }
//
// Splitting regroups the repeated members and copies every other field through
// byte-for-byte. A span is never inspected and never rewritten: it is moved.
package otlpwire

import (
	"errors"
	"fmt"
)

const (
	// Field numbers of the three container messages above. Their meaning to this
	// package is "the repeated member" and "everything else", not what they hold.
	fieldResourceSpans = 1
	fieldScopeSpans    = 2
	fieldSpans         = 2

	wireVarint  = 0
	wireFixed64 = 1
	wireBytes   = 2
	wireFixed32 = 5
)

// ErrIndivisible reports a payload that cannot be made to fit: a single span, alone,
// exceeds the budget. Truncating it would satisfy the size limit by losing data, which
// §3.2 forbids, so the request is refused instead and the caller answers the client.
var ErrIndivisible = errors.New("otlpwire: a single span with its resource and scope context exceeds the size budget")

// Fits reports whether payload already satisfies the budget, given a sizer that returns
// the size the payload will have on the wire (gzip, in production).
type Sizer func(payload []byte) (int, error)

// Split returns one or more payloads, each within limit according to sized, whose
// concatenated span set equals the input's.
//
// The identity case is deliberate and load-bearing: when the input already fits, the
// input slice is returned unchanged, so the common path is byte-identical from receive
// to publish and the collector demonstrably re-encodes nothing.
func Split(payload []byte, limit int, sized Sizer) ([][]byte, error) {
	size, err := sized(payload)
	if err != nil {
		return nil, err
	}
	if size <= limit {
		return [][]byte{payload}, nil
	}

	groups, err := regroup(payload, fieldResourceSpans, limit, sized, splitResourceSpans)
	if err != nil {
		return nil, err
	}
	return groups, nil
}

// splitResourceSpans divides one oversized ResourceSpans into several that carry the
// same resource and schema_url and a subset of the scope_spans each.
func splitResourceSpans(resourceSpans []byte, limit int, sized Sizer) ([][]byte, error) {
	return regroup(resourceSpans, fieldScopeSpans, limit, sized, splitScopeSpans)
}

// splitScopeSpans divides one oversized ScopeSpans into several that carry the same
// scope and schema_url and a subset of the spans each. A span is the smallest unit
// this package can move, so there is no deeper level.
func splitScopeSpans(scopeSpans []byte, limit int, sized Sizer) ([][]byte, error) {
	return regroup(scopeSpans, fieldSpans, limit, sized, func([]byte, int, Sizer) ([][]byte, error) {
		return nil, ErrIndivisible
	})
}

// regroup splits a container message on its repeated field.
//
// Fields other than repeated are the container's context — a Resource, an
// InstrumentationScope, a schema_url — and are copied verbatim into every output, which
// is what makes the split lossless. Members are accumulated greedily; when one no longer
// fits, the group is closed and the member starts the next. A member that does not fit
// alone is handed to splitMember, which either divides it one level deeper or reports
// that nothing can.
func regroup(container []byte, repeatedField int, limit int, sized Sizer,
	splitMember func([]byte, int, Sizer) ([][]byte, error)) ([][]byte, error) {

	var context []byte
	var members [][]byte

	err := eachField(container, func(field, wire int, value, whole []byte) error {
		if field == repeatedField && wire == wireBytes {
			members = append(members, value)
			return nil
		}
		context = append(context, whole...)
		return nil
	})
	if err != nil {
		return nil, err
	}

	if len(members) == 0 {
		return nil, fmt.Errorf("otlpwire: message of %d bytes exceeds the budget and has no field %d to split on",
			len(container), repeatedField)
	}

	var out [][]byte
	current := append([]byte(nil), context...)
	currentCount := 0

	flush := func() {
		if currentCount > 0 {
			out = append(out, current)
		}
		current = append([]byte(nil), context...)
		currentCount = 0
	}

	for _, member := range members {
		candidate := appendField(current, repeatedField, member)
		size, err := sized(candidate)
		if err != nil {
			return nil, err
		}

		if size <= limit {
			current = candidate
			currentCount++
			continue
		}

		// The member does not fit alongside what is already grouped. Close the group
		// and try the member on its own before concluding it needs dividing.
		flush()

		alone := appendField(append([]byte(nil), context...), repeatedField, member)
		size, err = sized(alone)
		if err != nil {
			return nil, err
		}
		if size <= limit {
			current = alone
			currentCount = 1
			continue
		}

		// Measure the deeper split through the wrapper it will actually be wrapped
		// in: gzip of the context plus a piece is not gzip of the context plus gzip
		// of the piece, so budgeting by subtracting len(context) would be an estimate
		// where an exact answer is available.
		wrapped := func(piece []byte) (int, error) {
			return sized(appendField(append([]byte(nil), context...), repeatedField, piece))
		}

		pieces, err := splitMember(member, limit, wrapped)
		if err != nil {
			return nil, err
		}
		for _, piece := range pieces {
			out = append(out, appendField(append([]byte(nil), context...), repeatedField, piece))
		}
	}
	flush()

	return out, nil
}

// eachField walks the top-level fields of a protobuf message, handing the callback the
// field number, the wire type, the field's value bytes, and the whole tag-and-value
// slice for copy-through.
func eachField(buf []byte, fn func(field, wire int, value, whole []byte) error) error {
	for offset := 0; offset < len(buf); {
		start := offset

		tag, n := varint(buf[offset:])
		if n == 0 {
			return fmt.Errorf("otlpwire: truncated field tag at offset %d", offset)
		}
		offset += n

		field, wire := int(tag>>3), int(tag&0x7)

		var value []byte
		switch wire {
		case wireVarint:
			_, n := varint(buf[offset:])
			if n == 0 {
				return fmt.Errorf("otlpwire: truncated varint at offset %d", offset)
			}
			value = buf[offset : offset+n]
			offset += n
		case wireFixed64:
			if offset+8 > len(buf) {
				return fmt.Errorf("otlpwire: truncated 64-bit field at offset %d", offset)
			}
			value = buf[offset : offset+8]
			offset += 8
		case wireBytes:
			length, n := varint(buf[offset:])
			if n == 0 {
				return fmt.Errorf("otlpwire: truncated length prefix at offset %d", offset)
			}
			offset += n
			end := offset + int(length)
			if end > len(buf) || end < offset {
				return fmt.Errorf("otlpwire: length-delimited field at offset %d runs past the buffer", start)
			}
			value = buf[offset:end]
			offset = end
		case wireFixed32:
			if offset+4 > len(buf) {
				return fmt.Errorf("otlpwire: truncated 32-bit field at offset %d", offset)
			}
			value = buf[offset : offset+4]
			offset += 4
		default:
			return fmt.Errorf("otlpwire: unsupported wire type %d for field %d", wire, field)
		}

		if err := fn(field, wire, value, buf[start:offset]); err != nil {
			return err
		}
	}
	return nil
}

// appendField writes a length-delimited field to dst and returns the extended slice.
func appendField(dst []byte, field int, value []byte) []byte {
	dst = appendVarint(dst, uint64(field)<<3|wireBytes)
	dst = appendVarint(dst, uint64(len(value)))
	return append(dst, value...)
}

func appendVarint(dst []byte, v uint64) []byte {
	for v >= 0x80 {
		dst = append(dst, byte(v)|0x80)
		v >>= 7
	}
	return append(dst, byte(v))
}

// varint decodes a base-128 varint, returning the value and how many bytes it used.
// A zero length means the buffer ended mid-varint.
func varint(buf []byte) (uint64, int) {
	var value uint64
	for i := 0; i < len(buf) && i < 10; i++ {
		b := buf[i]
		value |= uint64(b&0x7f) << (7 * i)
		if b < 0x80 {
			return value, i + 1
		}
	}
	return 0, 0
}

// SchemaURL returns the schema URL the payload declares, or "" when it declares none.
//
// The Pub/Sub message contract (§3.2) carries a `schema_url` attribute as the semantic
// convention audit trail, so the collector has to read one field it would otherwise not
// look at. It is an envelope field — ScopeSpans.schema_url, then ResourceSpans.schema_url
// — not a span attribute, and reading it needs no more knowledge than splitting already
// requires: the scope-level value is preferred because it states which conventions the
// instrumentation emitted, which is the narrower and more useful claim.
func SchemaURL(payload []byte) string {
	var resourceLevel string

	_ = eachField(payload, func(field, wire int, value, _ []byte) error {
		if field != fieldResourceSpans || wire != wireBytes {
			return nil
		}
		return eachField(value, func(field, wire int, value, _ []byte) error {
			switch {
			case field == 3 && wire == wireBytes && resourceLevel == "":
				resourceLevel = string(value)
			case field == fieldScopeSpans && wire == wireBytes:
				return eachField(value, func(field, wire int, value, _ []byte) error {
					if field == 3 && wire == wireBytes && len(value) > 0 {
						// Found the preferred level; stop by returning a sentinel the
						// outer walk swallows.
						resourceLevel = string(value)
						return errFound
					}
					return nil
				})
			}
			return nil
		})
	})

	return resourceLevel
}

var errFound = errors.New("otlpwire: found")
