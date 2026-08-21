# Vendored GenAI semantic conventions — v1.41.0

Upstream: [open-telemetry/semantic-conventions](https://github.com/open-telemetry/semantic-conventions)
at tag `v1.41.0` (published 2026-04-28), path `model/gen-ai/`.
License: Apache-2.0, copy in [`LICENSE`](LICENSE) — the upstream file, verbatim.

## Why a copy exists at all

`docs/architecture.md` §5 pins the GenAI conventions at v1.41 and calls the pin a
contract. A pin that cannot be read by a program is a claim, not a contract: nothing
can check that a mapping targets an attribute the pinned version actually defines.
Upstream publishes **no release assets** at this tag, so the machine-readable form is
the repository tree, and the only way to hold a fixed version of it is to vendor it.

`docs/gen-ai/*.md` upstream is generated human-facing output and is **not** the
contract; it is deliberately not vendored.

## Stability of what is vendored

At this tag every `stability` field in `registry.yaml` and `spans.yaml` reads
`development`; none is `stable`. Pinning does not inherit a stability guarantee from
upstream — it imposes one locally over a surface that is still moving. Emitters that
shipped against v1.36.0-or-earlier conventions stay on those by default and adopt newer
shapes only through `OTEL_SEMCONV_STABILITY_OPT_IN`, which is why a fixture manifest
records the semconv version *actually emitted* rather than assuming the pin.

## Contents and checksums

Verified at vendoring time against the checksums recorded in issue #8, which were taken
from upstream independently of this copy. Both agree.

| Vendored path | sha256 |
| --- | --- |
| `registry.yaml` | `55ec5102aaa0fbdc1afcef0cebcca5676b6a549507f781425558e2c25d4d137f` |
| `spans.yaml` | `ff7f1823dd0a3723455bdb2729b489093b3d687b0af680643e5a01455011d558` |
| `metrics.yaml` | `5a9eddb930002110ef6f0c735036faf8220ce07d2641f5b17c07799712743822` |
| `events.yaml` | `bcb52fa505ec921195bf74be47e9c5e0b712d0c1d93806e06a5922d6cb8228fe` |
| `deprecated/registry-deprecated.yaml` | `4c859ccb6c9335d1e8b8cc6f49693744ec095cad2c9e616db9d10bbe311eb87d` |
| `deprecated/events-deprecated.yaml` | `58143003d98f2cc12d4659c5dc915fc1ccfcb63b9278dd5d3c90cdf999ea3b52` |

`metrics.yaml` is vendored although this project ingests traces only
(`docs/architecture.md` §9): it defines attribute *usage* for the same registry, and a
partial copy of a model tree invites the question of what else was left out.

The two `deprecated/` files are vendored because they are load-bearing here, not for
completeness. The claude-code dialect emits `gen_ai.system`, which v1.41 deprecates in
favour of `gen_ai.provider.name` (`docs/evidence/claude-code-otel-capture.md` §4.4). A
mapping that rewrites a deprecated name to its replacement has to be able to prove the
source name was a real deprecated attribute rather than a typo.

## Refresh procedure

Moving the pin creates a **new directory** (`normalization/semconv/v1.42/`, and a
sibling mapping directory per ADR-0003 §4); it never edits this one in place. To vendor
a new version:

```bash
tag=v1.42.0
base="https://raw.githubusercontent.com/open-telemetry/semantic-conventions/${tag}/model/gen-ai"
dest="normalization/semconv/${tag%.0}"          # v1.42.0 -> v1.42
mkdir -p "$dest/deprecated"
for f in registry.yaml spans.yaml metrics.yaml events.yaml; do
  curl -fsS -o "$dest/$f" "$base/$f"
done
for f in registry-deprecated.yaml events-deprecated.yaml; do
  curl -fsS -o "$dest/deprecated/$f" "$base/deprecated/$f"
done
curl -fsS -o "$dest/LICENSE" "https://raw.githubusercontent.com/open-telemetry/semantic-conventions/${tag}/LICENSE"
shasum -a 256 "$dest"/*.yaml "$dest"/deprecated/*.yaml
```

Record the printed checksums in the new directory's README, and re-derive
[`external-allowlist.yaml`](external-allowlist.yaml) — external references move between
versions, and carrying the old list forward would assert provenance nobody checked.

## Consumers

- `normalization/mappings/v1.41/*.yaml` — every `semconv` target must name an attribute
  defined here or listed in `external-allowlist.yaml`. The rule is enforced by a test in
  the worker's test project, which is the executable form of `docs/eval-plan.md` SC-1
  row 1.4. That test arrives with the mappings in F1 W4; until then this directory is
  vendored and unread, which is the honest state of it.
- Nothing at runtime reads this directory. Mappings are embedded at build time
  (ADR-0003); the registry is a build- and test-time artefact only.
