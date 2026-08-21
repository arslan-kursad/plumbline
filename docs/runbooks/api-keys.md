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

Set `status` to `revoked` on the document. The collector reads the registry at
startup, not per request (a data-plane component re-reading a file or a collection
on the hot path buys hot reload nobody asked for and pays in latency), so a
revocation takes effect on the next start. With `min-instances = 0` a redeploy
costs nothing and no downtime:

```bash
gcloud run services update collector --region us-central1 --project "$PROJECT_ID" --no-traffic --tag revoke-refresh
```

**Revocation is not instant, and pretending otherwise would be the dangerous
version.** If a key is known leaked and the exposure matters more than the
traffic, remove the collector's traffic or delete the document and force a
restart — and record what happened in `docs/`, per the architecture §7 escape
hatch, because a leaked credential is an incident whether or not it cost money.

## 5. What this does not do

- **No rotation automation.** Rotation is: issue new, migrate the agent, revoke
  old. Three deliberate steps beat a scheduler that rotates a key nobody noticed
  the agent still needed.
- **No expiry.** Keys do not age out. Adding expiry without a rotation path
  produces an outage on a date nobody remembers choosing.
- **No per-key scopes.** Every key can publish traces and nothing else, because
  that is the only thing the collector does.
