# `grpc` v1.83.1 — redeployed into the kill-switch function and verified

**Measured:** 2026-09-05 · **Lane:** A (read-only verification) · **Applied by:** maintainer
**Change:** Dependabot alert 1 — GHSA-vp52-pcj8-j9qc / CVE-2026-84304, high
**Merged as:** `#189` (`e97c72e`) · **Repo:** `main` @ `e97c72e`

The apply is Lane C by [`kill-switch.md`](../runbooks/kill-switch.md) §4a — the kill-switch's
four resources are applied from the maintainer's own credentials, targeted, because
`ci-deploy` has no grant on the function-source bucket. *"The last cost control is not
rewritable by the automation it bounds."*

**Merging the bump was not the fix.** `#189` changed `go.mod` and `go.sum`; the deployed
container keeps whatever it was built from until the source archive is rebuilt and the
function redeployed. Dependabot closed alert 1 as `fixed` at **10:51:06Z**, 65 seconds
after the merge and **almost ten minutes before** the function actually carried the patched
library. The alert reads the manifest on the default branch, not the running service —
worth stating once, because the gap between those two is exactly what this file measures.

---

## Five readings, all after the apply

| Reading | Before | After |
|---|---|---|
| Source archive in `…-function-source` | `…-385fb3bc636cc1fd724f9f17e04d9038.zip` | **`…-dbb53f4e370aa158406be5b010fb5152.zip`** |
| `go.mod` **inside the deployed archive** | `grpc v1.83.0` | **`grpc v1.83.1`** |
| Function `updateTime` | `2026-09-02T09:22:01Z` | **`2026-09-05T11:00:53Z`** |
| Revision (latest / serving) | `00003-yoh` / `00003-yoh` | **`00004-don` / `00004-don`** |
| Terraform state, serial | serial 30 at the 2026-09-02 apply | **serial 32** |

**The second row is the one that matters, and it is a direct read.** The other four
establish that *an* apply completed; none of them says which library the running code is
linked against. That reading was taken by downloading the archive the function is built
from and opening `go.mod` inside it — `google.golang.org/grpc v1.83.1` at line 39 — rather
than inferring it from the fact that a revision number moved. A redeploy from a stale
working tree would advance `updateTime` and the revision identically while shipping the
vulnerable version, and that failure mode was live on this host an hour earlier: the
maintainer's checkout sat at `e97c72e` with `grpc v1.83.0` still on disk, HEAD and working
tree disagreeing, because `main` had advanced under it from a second worktree. It was
restored before the plan was taken.

**The revision pair matters on its own:** `latestReadyRevisionName` and the traffic target
are both `00004-don`, so there is no half-completed migration with the old revision still
serving.

**The state serial is reported as an increment, not as a pair.** The previous *recorded*
value is 30, from the 2026-09-02 evidence; the state object is overwritten in place and was
not read immediately before this apply, so the exact prior value is not claimed here.

## Nothing else moved

`DETACH_THRESHOLD` reads **`200`** on the live API after the apply, unchanged — the value
ADR-0004 Amendment 5 set and the 2026-09-02 evidence recorded. The targeted plan proposed
`1 to add, 1 to change, 1 to destroy`: the source object replaced because its name carries
the archive's md5, and the function updated in place at
`build_config.source.storage_source.object`. No budget was in the plan, and the function's
`service_config` was not touched. Function `state` is `ACTIVE`.

The destroy in that plan is the point of §4a: replacing the archive is a delete plus a
create, and `storage.objects.delete` on that bucket is precisely the grant `ci-deploy` does
not hold (decision log A2.11). The bucket now holds one object, the new one.

## Convergence

A read-only plan across all four kill-switch resources, after the apply:

```
No changes. Your infrastructure matches the configuration.

Terraform has compared your real infrastructure against your configuration and
found no differences, so no changes are needed.
```

## The plan guard ran after the apply, not before it

The documented order (`infra/terraform/README.md`) is plan, guard, apply. The guard was
invoked with a path relative to `infra/terraform` and refused:

```
no such plan file: killswitch-grpc.tfplan
```

`terraform-plan-guard.sh` does `cd "$(git rev-parse --show-toplevel)"` before resolving its
argument, so the path has to be repo-root-relative. The message names the file rather than
the reason, which is why it read as a missing artefact instead of a wrong invocation, and
the apply went ahead without the guard.

Re-run against the same saved plan file afterwards, it passes:

```
plan guard: asserted
  google_cloudfunctions2_function.killswitch: min_instance_count=0, max_instance_count=1
plan guard: clean (29 resource types allowed by §7.1)
```

**Recorded rather than tidied away.** The outcome is the same one the guard would have
produced in the right order — no new resource type, both resources already in the §7.1
allowlist in `architecture.md` §7.1, scaling and region unchanged — but a control that runs after the action it
gates has not gated anything, and "it would have passed" is not a result. What the correct
invocation looks like belongs in the runbook; that is a separate change and is not made
here.

## What this does not establish

**The patched library is deployed; nothing shows it was ever reachable.**
GHSA-vp52-pcj8-j9qc describes a **server-side** gRPC memory exhaustion: a peer fragments a
stream into millions of tiny HTTP/2 DATA frames against a gRPC server. `main.go` imports
neither `grpc` nor any gRPC transport — it is a CloudEvent handler talking to the Cloud
Billing API through `google.golang.org/api/cloudbilling/v1`, the generated **REST** client.
`grpc` is in the module graph transitively, through `google.golang.org/api`'s internals,
and this function runs no gRPC server. So the bump removes a vulnerable package from the
build; it is not evidence that the function was exploitable, and no reachability analysis
was performed beyond reading the imports.

**The kill-switch's behaviour was not re-fired.** This redeploy rebuilt the container from
unchanged `main.go`; the trigger semantics, the threshold and the detach path are the ones
Amendment 4's three-step live-fire established on 2026-08-26 and are untouched by it. The
live-fire that ADR-0004 Amendment 5 and DoD 13b jointly owe against `200.00` is still
outstanding and is unaffected by this file.

**§4a was self-contradicting when this apply was classified under it.** The paragraph
naming the four resources as human-applied sat nine lines above one asserting the function
"goes through the gate as normal"; both had stood since 2026-08-26. The contradiction was
raised as `#192` and resolved in `#193` (`393b190`) earlier the same day, in favour of the
human-applied reading — which is the one this apply followed, and the one the recorded
`403` supports.
