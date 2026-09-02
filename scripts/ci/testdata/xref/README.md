# xref self-test corpus

A deliberately broken documentation tree. `xref-check.sh --self-test` runs the checker
over it and asserts the exact finding set below — no more, no fewer.

**Both halves are load-bearing.** Catching the four defects proves the check can fail.
Staying silent on the six decoys proves it is worth switching on: a check that reports
every legitimate cross-document reference has traded one manual pass for another
(F3 entry directive, F3E-04 acceptance criterion 3).

| File | Expected |
| --- | --- |
| `docs/specs/broken.md` | 3 dangling sections, 1 dead link |
| `docs/specs/qualified.md` | nothing — every reference belongs to another document |
| `docs/runbooks/borrowed.md` | nothing — borrows architecture's numbering, and resolves there |
| `docs/architecture.md` | nothing — it is the borrowed document |

Fixtures are authored rather than captured, and that is correct here: the corpus *is* the
test input. It is not evidence about the repository, so the fixture-provenance rule
(SC-1 row 1.2) does not apply to it.
