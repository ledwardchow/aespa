# Design selection

The primary read all candidate packages, their complete alternatives, and the source contracts. The recommended base is candidate 2's catalog, not its journal alternative. Each candidate also supplied a structurally different full alternative, so synthesis did not compare only cosmetic variants.

| Rubric criterion | Primary C1 | Primary C2 | Primary C3 | Independent C1 | Independent C2 | Independent C3 |
| --- | --- | --- | --- | --- | --- | --- |
| Five defect coverage | 3 | 3 | 3 | 3 | 3 | 3 |
| Cheap grouped crawling | 3 | 4 | 4 | 3 | 4 | 4 |
| Evidence distinctions | 4 | 4 | 4 | 4 | 4 | 4 |
| Interface ownership | 4 | 3 | 4 | 4 | 3 | 4 |
| Concurrency and old data | 3 | 4 | 2 | 3 | 4 | 3 |
| Implementable contracts | 3 | 3 | 3 | 4 | 4 | 3 |
| Total / 24 | 20 | 21 | 20 | 21 | 22 | 21 |

All candidates choose a catalog as their recommendation. Candidate 1 best states evidence-limited ownership and source-page separation. Candidate 2 best specifies nullable SQLite uniqueness and existing workprogram reuse. Candidate 3 offers the smallest catalog and useful snapshot versioning, but omits method and account-pair scope and its exact active-claim concurrency contract is weaker.

The judge recommended candidate 2 and the primary agreed. The final design uses its three evidence-indexed tables and grafts candidate 1's entitlement/source-page rules and candidate 3's sampler and archive migration. The final signatures correct all candidates' missing method/account-pair scope and their raw-plus-obligation double-counting ambiguity.

Core-owned evidence admission replaces each candidate's overly broad "new traffic ID means new work" token. Deferred follow-up attempts are separate handoff rows rather than a shared pending-evidence JSON list. The atomic partial unique active-scope index remains the owner of exclusivity.

Final artifacts are docs/implementation-plans/grouped-route-testing-design.md and grouped-route-testing-sketch.py. Production implementation is outside this design request. The sketch has intentionally unimplemented bodies; syntax validity does not establish runtime correctness.

Final design review corrected three concrete issues: caller/result type mismatch, too-broad access evidence references, and underspecified raw-cell/selected-child reduction. A fresh reviewer verified these corrections in both final files and returned pass. The primary ran Ruff, syntax, import, stub-only, and whitespace checks. These checks validate the design artifacts, not runtime behavior.
