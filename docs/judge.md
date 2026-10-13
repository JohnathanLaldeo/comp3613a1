# student-judge competency report

**Judged at:** 2026-10-12
**Evidence pass:** re-read available native Copilot chats for Phases 1–5 plus current docs/report.md, use-case diagram, wireframe set, and student-build framework-phases.md; included the student's latest Bob prize-flow verification (prior judge.md ignored)
**Student / session:** Student Awards / Copilot Guide chats
**Artifact:** Native Copilot Guide chats and current project artefacts
**Phases in evidence:** 1–5 (COMP 3613; Phase 5 polish, Phase 6 deploy; never generic 0–5)

### Totals
| | Count / value |
|--|--|
| Metrics on rubric | 12 (M1–M12) |
| N/A (excluded) | 0 |
| Metrics scored | 12 |
| Scoreable max | 12 × 4 |
| Awarded total | 30 / 48 |
| **Overall (avg of scored)** | **2.5 / 4** |
| Impression mark | 13 / 20 |

## Scorecard

| ID | Metric | Score / 4 | In avg | Evidence |
|----|--------|----------:|:------:|----------|
| M1 | Phase discipline | 3 | yes | Used separate chats for Phases 1–4 and continued Phase 5 through build and polish. Phase 5 is still open pending prize-flow verification; no premature deployment. |
| M2 | Problem framing | 3 | yes | Student named Student Awards and three workflows, provided branding, and made concrete model/workflow choices. Phase 2 choices were recorded as include/reject/shared-use-case decisions in the report. |
| M3 | Decision ownership | 2 | yes | Strong ownership of dashboard mismatches, 1:1 points, separate Activity/optional Notes, text-only notes, service responsibility, and required rejection reason. Ownership is discounted for the confirmation-route answer-seeking/paste-back sequence (Phase 5 turns 9–14). |
| M4 | Artefact-before-code | 3 | yes | The use-case diagram, ERD, and eight wireframes were present before Phase 5 implementation and guided the changes; polish updated Activity/Notes to reflect the wireframe. |
| M5 | Verification habit | 4 | yes | Student verified dashboard, volunteer log persistence, admin layout/actions/totals, and now tested prize redemption as Bob: the confirmation screen appeared before commit and Confirm redeemed the prize. |
| M6 | Assignment fit | 3 | yes | Changes remain tied to the named workflows and wireframes, use services/repositories and preserve thin routes; no route-level SQL evidence. Existing auth/bootstrap repairs were necessary to run the app. |
| M7 | Slice explanation | 2 | yes | Student identified service coordination for submission validation and admin figures and produced model/route attempts. The prize-route answer initially used mismatched dependency/template conventions and its ownership is uncertain after the paste-back flag. |
| M8 | Prompt quality | 3 | yes | Phase-tagged prompts and specific, observable dashboard/admin mismatch reports gave actionable steering; prize confirmation requirements were stated clearly. |
| M9 | Response to pushback | 4 | yes | Student kept refining rather than accepting the first build: specified dashboard labels/layout, chose separate activity and notes, steered admin summary content, required rejection reasons, and requested the wireframe confirmation step. |
| M10 | Integrity | 1 | yes | Suspected external assist / paste-back: after asking for paste-ready code and then hints, the student supplied a generic confirmation handler that did not match the app’s routes/dependencies, then requested that it be inserted. No external use is proven. |
| M11 | Provenance continuity | 1 | yes | Most design and polish decisions remain grounded in the project artefacts, but the pasted confirmation handler’s generic API/path and dependency conventions are inconsistent with this repository, leaving its authorship uncertain. |
| M12 | Sincerity trajectory | 1 | yes | No formal `student-judge:sincerity` blocks or ownership quiz followed the answer-seeking/paste-back sequence; suspicion therefore remains uncleared. |

## Strengths
- Student supplied branding and steered multiple concrete UI/workflow refinements from their own wireframes.
- Student checked the dashboard, volunteer log, and admin review flow in the running app and reported observed results.
- Student verified the prize confirmation-before-commit behavior and successfully confirmed one redemption as Bob.
- Student understood that submission validation and admin summary coordination belong in the service layer.
- The implementation maintains the layered pattern: routes call services; repositories own persistence.

## Gaps (priority order)
1. **Ownership concern on the confirmation-route snippet.** The student requested paste-ready code, then supplied a handler using APIs and paths that do not match the project. This is a concern, not proof of external assistance.
2. **No Phase 6 deployment evidence yet.** The report has no public Render URL; Phase 6 has not started.

## Phase gate status
| Phase | Status | Note |
|-------|--------|------|
| 1 | met | Student Awards and three named workflows are recorded. |
| 2 | met | UML use-case diagram covers all named workflows and the recorded include/reject choices. |
| 3 | met | Mermaid ERD is present; Phase 5 added Activity/Notes and indexed decision timestamp consistent with observed workflow needs. |
| 4 | met | Eight wireframes are embedded and all three named workflows have coverage records. |
| 5 | met | Theme, build, and verified polish are present across the named workflows, including prize confirmation-before-commit. |
| 6 | not met | No Render deployment URL or deployed marker logins; deploy is correctly deferred until Phase 5 exit. |

## Recommended next practice
- Explain in your own words which service call reads prize confirmation data and which service call commits redemption; optionally verify that Cancel returns to the catalog.

## Integrity note
- **Suspected external assist / paste-back.** The student asked for code to copy, then supplied a generic confirmation-route implementation that did not match the FastStarter route conventions. This is not proof of external assistance; ownership should be checked directly.

## Provenance flags
- Suspected paste-back / answer-seeking in Phase 5 turns 9–14. Evidence: “can u send the code so i can copy and paste it?” followed by a handler using `/student/prizes`, `get_confirmation_data`, and dependency signatures not present in the project; then the student asked the Guide to add the code.

## Sincerity log summary
- Blocks found: 0 | max round: N/A | min/mean/final confidence: N/A | trend: N/A | cleared: no (suspicion was not formally escalated or resolved)

## Skips
- Skips: 0/3 used.

## Recommended instructor action
- Conduct a short live ownership check on 2–3 concrete lines: how the confirmation GET obtains the prize/balances from the service, how the POST commits redemption, and why repository persistence does not belong in the route.
