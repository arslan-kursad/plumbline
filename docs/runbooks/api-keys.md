# Runbook — issuing and revoking API keys

Agents authenticate to the collector with an API key. The registry is Firestore;
what it stores is a hash. **Plaintext exists once, in the terminal that issued
it** — this is the property the design is built around, not a limitation of it
(architecture §6.3, F2 spec D5).

Tool: [`collector/cmd/keyctl`](../../collector/cmd/keyctl). It lives inside the
collector module so that the key it issues and the key the collector accepts are
defined by one piece of code.

## 1. The `api_keys` collection

One document per key, document id = `api_key_id`.

| Field | Type | Notes |
| --- | --- | --- |
| `api_key_id` | string | Stable, human-readable. **Appears on every span** as provenance (§3.2, §4.1), so it is a name you will read in dashboards for months. |
| `key_sha256` | string | SHA-256 of the plaintext, lowercase hex. The only representation stored. |
| `source_dialect` | string | Registration hint. Advisory: the worker's detection is authoritative (§5), and a mismatch is logged rather than obeyed. |
| `rate_limit_per_second` | number | Per-key token-bucket rate (§6.2 — approximate, up to 2× nominal with two instances). |
| `burst` | number | Token-bucket burst. |
| `status` | string | `active` or `revoked`. Anything else is treated as not active. |
| `issued_at` | timestamp | When `keyctl` created the document. |

Key format is `plb_<environment>_<32 lowercase hex>`, sixteen random bytes.
`live` and `local` are issued; **`test` is reserved and never issued**, which is
what lets documentation and fixtures carry realistic key-shaped strings while
Gate F still matches every real key with no exclusion list (issue #19).

## 2. Issuing (human-only)

```bash
go run ./cmd/keyctl -project "$PROJECT_ID" -id adjudicator-prod -dialect langgraph
```

The plaintext goes to stdout and everything else to stderr, so redirecting stdout
captures the key and nothing else:

```bash
go run ./cmd/keyctl -project "$PROJECT_ID" -id adjudicator-prod > key.txt
```

**Redirect by default, not only when it is convenient.** Run without the
redirection and the key renders in the terminal, where it survives in scrollback
and in any screenshot of that window. That is how this project leaked two keys in
one week — not through the repository, which Gate F watches, but through a
terminal photograph, which nothing watches. The redirection is the only difference
between the two outcomes, and it costs six characters.

Rehearse with `-dry-run` first if the flags are unfamiliar: it prints the document
it would create, generates nothing, and writes nothing.

**Then, in the same sitting:**

1. Put the key where the agent reads it — an environment variable in the agent's
   own deployment, a password manager entry. Not in this repository, not in an
   issue, not in a chat transcript. The repository is public and its history is
   not erasable in practice.
2. Delete the file if you used one (`shred -u key.txt`, or `rm` and empty the
   trash).
3. Do not paste it anywhere "just to check". Checking it means using it.

`keyctl` refuses to overwrite an existing `api_key_id`. That refusal is
deliberate: the document it would replace belongs to a key some agent may still
be presenting, and overwriting the hash revokes that key silently, at the next
collector start, with no error anywhere near the person who caused it.

## 3. Losing a key

There is no recovery. The hash is one-way and nothing else was kept.

Issue a new key with a new `api_key_id`, move the agent to it, then revoke the old
one (§4). Reusing the id would be the silent-revocation case above.

## 4. Revoking

Set `status` to `revoked` on the document. `keyctl` issues only — it has no revoke
flag — so this is a direct one-field write against the Firestore REST API:

```bash
curl -X PATCH -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" "https://firestore.googleapis.com/v1/projects/$PROJECT_ID/databases/(default)/documents/api_keys/$KEY_ID?updateMask.fieldPaths=status" -d '{"fields":{"status":{"stringValue":"revoked"}}}'
```

**`updateMask.fieldPaths=status` is not decoration.** A `PATCH` without it replaces
the document with the request body, which would drop `key_sha256` and the other
five fields and leave a document that authenticates nothing and explains nothing.
Read the document back afterwards and confirm seven fields with `key_sha256`
intact — the three revocations on 2026-09-01 were checked that way, and the check
costs one request.

The collector reads the registry at startup, not per request (a data-plane
component re-reading a file or a collection on the hot path buys hot reload nobody
asked for and pays in latency), so a revocation takes effect on the next start.
With `min-instances = 0` that happens without an operator: the serving revision
scales to zero when idle, and the next request cold-starts against the current
registry. Nothing needs to be redeployed, and the wait is bounded by traffic
rather than by a command.

**Revocation is not instant, and pretending otherwise would be the dangerous
version.** If a key is known leaked and the exposure matters more than the
traffic, remove the collector's traffic or delete the document and force a
restart — and record what happened in `docs/`, per the architecture §7 escape
hatch, because a leaked credential is an incident whether or not it cost money.

### Revocations performed

**2026-09-01 — `wave4-e2e`, `wave4-e2e-2`, `wave4-e2e-3`, orphaned by the F2 first-delivery
sequence.** None was exposed; all three were issued during Wave 4 and outlived their use.

| Key | Issued | Why it was orphaned |
| --- | --- | --- |
| `wave4-e2e` | `02:31:03Z` | plaintext written to a relative path and deleted before the harness read it |
| `wave4-e2e-2` | `02:34:23Z` | shredded immediately after a *failed* run, so the retry could not reuse it |
| `wave4-e2e-3` | `03:33:49Z` | carried the successful deliveries and the drill; no longer needed |

Revoked by `PATCH` with `updateMask.fieldPaths=status`, so only that field moved. Read back
rather than assumed: all three `revoked`, seven fields each, `key_sha256` intact.

**The second one is a procedure lesson, not an accident.** The instruction to shred the key
file was given for the success case and followed after a failure, and a failed run needs a
retry with the same key. Cost: one key. `#112` carries it forward.

**Effective immediately in practice, and the reasoning is dated rather than asserted.** The
collector last served a request at `04:19:43Z` and revocation happened at `06:38Z` — two
hours and nineteen minutes of idle against `min-instances = 0`, so no instance holds the
pre-revocation registry and the next cold start reads the revoked documents.


**2026-08-26 — `adjudicator-prod`, twice, plaintext exposed in a screenshot.**
The key issued 2026-08-21 was displayed in a terminal capture shared into a chat,
reissued under the same id, and the reissue was displayed the same way. Both
documents were deleted and a third key issued as `adjudicator-prod-2` with stdout
redirected to a file, so its plaintext never rendered.

Registry state afterwards, read back rather than assumed — one key, and neither
exposed hash present:

```
1 key(s) in the registry
  adjudicator-prod-2: status=active dialect=langgraph issued=2026-08-26T10:13:28Z
```

**Exposure was bounded by luck rather than by design:** no Cloud Run collector
existed yet, so neither key ever had an endpoint to authenticate against. Deleting
the documents was therefore sufficient and no traffic analysis was needed. Had
Wave 2 already applied, this would have been an incident note under architecture
§7 rather than a runbook entry.

**The id changed, and that is visible downstream.** `api_key_id` travels on every
published message and lands in `spans` as provenance (§3.2), so rows written
before and after this revocation carry different values for the same agent. Any
query grouping by key over that boundary sees two identities.

## 5. What this does not do

- **No rotation automation.** Rotation is: issue new, migrate the agent, revoke
  old. Three deliberate steps beat a scheduler that rotates a key nobody noticed
  the agent still needed.
- **No expiry.** Keys do not age out. Adding expiry without a rotation path
  produces an outage on a date nobody remembers choosing.
- **No per-key scopes.** Every key can publish traces and nothing else, because
  that is the only thing the collector does.
