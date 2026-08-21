# Generated Terraform inputs

Files here are **generated and guarded**, not authored. Editing one by hand works
until CI runs.

| File | Generated from | Guard |
| --- | --- | --- |
| `spans-schema.json` | `analytics/sql/001_spans_table.sql` | `scripts/ci/bq-schema-guard.sh` |

They are committed rather than produced at plan time because Terraform reads them
with `file()` and has no build step to run first. The guard is what keeps a
committed copy from becoming a second hand-maintained definition — the divergence
D4 exists to prevent, one level down from the views it names.

Regenerate:

```bash
python3 scripts/ci/bq_schema.py analytics/sql/001_spans_table.sql > infra/terraform/generated/spans-schema.json
```
