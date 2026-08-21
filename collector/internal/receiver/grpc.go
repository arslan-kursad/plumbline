package receiver

import (
	"context"
	"errors"
	"fmt"
	"log/slog"

	"github.com/arslan-kursad/plumbline/collector/internal/ingest"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

// rawMessage is the only message type this gRPC server knows: a byte slice.
//
// The obvious implementation of an OTLP gRPC receiver imports the generated
// ExportTraceServiceRequest and lets the standard proto codec deserialize into it. That
// would put the OTLP semantic types inside the collector — the one import architecture
// §2.1 forbids — and would mean the bytes are decoded and re-encoded on their way to
// Pub/Sub, so "the raw protobuf bytes are never mutated" would rest on the round trip
// being faithful rather than on nothing having happened to them.
//
// A codec that hands the handler the wire bytes removes the question. The collector
// cannot look inside a span because it has no type to look inside.
type rawMessage []byte

type rawCodec struct{}

func (rawCodec) Marshal(v any) ([]byte, error) {
	message, ok := v.(*rawMessage)
	if !ok {
		return nil, fmt.Errorf("receiver: rawCodec cannot marshal %T", v)
	}
	return *message, nil
}

func (rawCodec) Unmarshal(data []byte, v any) error {
	message, ok := v.(*rawMessage)
	if !ok {
		return fmt.Errorf("receiver: rawCodec cannot unmarshal into %T", v)
	}
	*message = append((*message)[:0], data...)
	return nil
}

// Name reports "proto" because that is the content subtype every OTLP gRPC exporter
// asks for. The codec is registered for that subtype on this server only; it does not
// change how protobuf is handled anywhere else in the process.
func (rawCodec) Name() string { return "proto" }

// traceExporter is the handler side of the OTLP TraceService, in bytes.
type traceExporter interface {
	export(ctx context.Context, payload []byte) error
}

type grpcExporter struct {
	in  *ingest.Ingestor
	log *slog.Logger
}

func (e *grpcExporter) export(ctx context.Context, payload []byte) error {
	key := ""
	if md, ok := metadata.FromIncomingContext(ctx); ok {
		if values := md.Get(APIKeyHeader); len(values) > 0 {
			key = values[0]
		}
	}

	result, err := e.in.Accept(ctx, key, payload)
	if err != nil {
		code, message := grpcStatusFor(err)
		e.log.Warn("export rejected",
			"transport", "grpc", "code", code.String(), "api_key_id", result.APIKeyID, "error", err)
		return status.Error(code, message)
	}

	e.log.Info("export accepted",
		"transport", "grpc", "api_key_id", result.APIKeyID,
		"messages", result.Messages, "payload_bytes", len(payload))
	return nil
}

// traceServiceDesc registers the OTLP TraceService by hand.
//
// Generated registration code would come with the generated request type, which is what
// this receiver exists to avoid. The service and method names are the wire contract from
// opentelemetry-proto; getting one wrong makes every exporter fail with Unimplemented,
// which the transport test catches by calling the real method name.
var traceServiceDesc = grpc.ServiceDesc{
	ServiceName: "opentelemetry.proto.collector.trace.v1.TraceService",
	HandlerType: (*traceExporter)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "Export",
			Handler: func(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
				payload := new(rawMessage)
				if err := dec(payload); err != nil {
					return nil, err
				}

				handle := func(ctx context.Context, _ any) (any, error) {
					if err := srv.(traceExporter).export(ctx, *payload); err != nil {
						return nil, err
					}
					// An empty ExportTraceServiceResponse: zero bytes, no partial success.
					return new(rawMessage), nil
				}

				if interceptor == nil {
					return handle(ctx, payload)
				}
				return interceptor(ctx, payload, &grpc.UnaryServerInfo{
					Server:     srv,
					FullMethod: "/opentelemetry.proto.collector.trace.v1.TraceService/Export",
				}, handle)
			},
		},
	},
	Metadata: "opentelemetry/proto/collector/trace/v1/trace_service.proto",
}

// NewGRPC builds the OTLP/gRPC server.
func NewGRPC(in *ingest.Ingestor, log *slog.Logger) *grpc.Server {
	server := grpc.NewServer(
		grpc.ForceServerCodec(rawCodec{}),
		grpc.MaxRecvMsgSize(MaxRequestBytes),
	)
	server.RegisterService(&traceServiceDesc, &grpcExporter{in: in, log: log})
	return server
}

func grpcStatusFor(err error) (codes.Code, string) {
	switch {
	case errors.Is(err, ingest.ErrUnauthenticated):
		return codes.Unauthenticated, "unknown or missing API key"
	case errors.Is(err, ingest.ErrRateLimited):
		return codes.ResourceExhausted, "rate limit exceeded for this API key"
	case errors.Is(err, ingest.ErrTooLarge):
		return codes.InvalidArgument,
			"a single span exceeds the message budget; it is refused rather than truncated"
	case errors.Is(err, ingest.ErrMalformed):
		return codes.InvalidArgument, "payload is not a well-formed OTLP export request"
	default:
		return codes.Internal, "export could not be published"
	}
}
