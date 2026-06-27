# 91 — Stage 3 (UX & Workflow) Skip Memo

Authority: DEC-019 (pinned 2026-06-25 by PM specialist, confirmed by user 2026-06-27).

## Skip category

**`SKIP-NOT-APPLICABLE`** — the topic's trigger does not arise for this project at MVP.

## Trigger that did not arise

The `idea-to-specs` workflow Stage 3 (`ux-workflow-designer`) is triggered for:

- User-facing products
- Operator consoles
- Admin panels
- Developer portals
- AI agents with human interaction

It is explicitly **skippable** for headless APIs, pure libraries, pure backend services, and embedded components — with a skip rationale.

## Why GroundedDocs MVP qualifies for skip

1. **No standalone product UI in MVP.** Per `01-product-brief.md` §5 and `02-requirements.md` REQ-009, the only UI surface in MVP is an **embeddable iframe widget** sitting inside the vendor's host console. The vendor owns the surrounding UX.
2. **The widget's UX is bounded.** It is a chat input + answer pane + citation interaction. The interaction model is dictated by:
   - REQ-004 (cited Q&A)
   - REQ-006 (refusal)
   - REQ-009 (iframe widget contract)
3. **Widget UX is owned by Stage 4 architecture.** The widget contract is part of the vendor integration surface (DEC-015), which is a Stage 4 deliverable inside `04-architecture.md`. Splitting it into a standalone Stage 3 artifact would duplicate work.
4. **Admin console is V2, not MVP.** Per `01-product-brief.md` §7, the admin console (which would be the principal Stage-3-relevant artifact) is deferred to V2 along with the review queue, prompt template registry, and customer golden set UI. Stage 3 will be re-run before V2 admin-console specs are written.
5. **No developer portal in MVP.** Developer experience is covered by:
   - The HTTP API spec slot (`06-api-contracts.md`)
   - The OSS install runbook (Stage 7 deliverable inside `09-deployment-ops.md`)
   - The dev profile NFR-011

None of these need workflow-map / journey-map / state-matrix treatment in MVP.

## What is *not* skipped (rolled into other stages)

| UX-adjacent concern | Where it lives instead |
|---|---|
| Widget interaction contract (input → answer → citation click → refusal banner) | `04-architecture.md` integration-surface section |
| Citation rendering states (verified / partially-verified / refused) | `04-architecture.md` + REQ-004, REQ-005, REQ-006 acceptance criteria |
| Accessibility for the widget | Stage 7 widget spec section (basic ARIA + keyboard nav); deeper a11y deferred to V2 admin console scope |
| Error / loading / empty states for the widget | Stage 7 widget spec section |
| Admin-API discoverability / DX | `06-api-contracts.md` + OSS docs (Stage 7) |

## What triggers re-running Stage 3

Run Stage 3 fully when **any** of:

- V2 admin console scope opens (review queue UI, golden-set curation UI, prompt-template registry UI)
- A first vendor pilot requests a standalone branded UI rather than a widget
- A regulated-buyer audit requires UX evidence (workflow map, state matrix)

## Cross-references

- Skip authority: `13-decision-log.md` DEC-019
- Reaffirmed by Stage 2 closure in `01-product-brief.md` §12
- Out-of-scope reaffirmation: `01-product-brief.md` §6 (Admin console MVP non-goal)

Memo authored 2026-06-27 as part of Stage 2 closure.
