# Specs Cross-Model Review

**Date:** 2026-07-16
**Reviewer:** deepseek-v4-pro (different vendor family)
**Prior review:** [2026-07-13](specs-cross-model-review-2026-07-13.md) (30 findings, 6C/9H/10M/5L, verdict BLOCK; all CRITICAL/HIGH since resolved)
**Scope:** All 6 review groups (A–F) per `00-index.md`'s Review groups table, DEC-001 through DEC-145. Three Explore subagents reviewed Groups A+B, C+E, and F in parallel; Group D was reviewed directly. All subagent findings were independently verified against the source files before inclusion below.

## Scope — what was reviewed and how

| Group | Files | Method |
|---|---|---|
| A — Product & Requirements | `01-product-brief.md`, `02-requirements.md`, `confirmed-context.md` | Direct read (all three full) + Explore subagent cross-check |
| B — Architecture & Agent Behavior | All 10 Group B files | Explore subagent (full review) + direct re-verification of CRITICAL/HIGH findings |
| C — Evals, Guardrails & Observability | `23-evals-guardrails.md`, `08-observability-logs.md`, `24-prompt-registry.md` | Explore subagent (full review) |
| D — Decision Log | `13-decision-log.md` (first 80 rows of 145) | Direct read (canonical anchor) |
| E — Process artifacts | `92-stage5-review-memos.md` + 4 other files | Explore subagent (every R1-R6 finding traced against decision log) |
| F — Build, Test & Verification Plan | `10-build-plan.md`, `11-test-plan.md`, `12-verification.md` | Explore subagent (systematic REQ→TASK→TEST→VG chain trace + 3 spot-checked chains) + direct grep verification |

---

## Findings

### R.1 [CRITICAL] — Cross-reference integrity (Group B → DEC-142 propagation)

File: `04-architecture.md` §9.1, `06-api-contracts.md` §Operational API, `20-agent-behavior.md` §6, `09-deployment-ops.md` §Installation

Issue: DEC-142 (2026-07-15) split the embedding service into two TEI containers — dense (`bge-m3`) and sparse (a separate SPLADE model). The decision propagated correctly to `04-architecture.md`'s tech-stack table and VRAM notes, but **not** to the four files an implementer would actually use to deploy the system:

- `04-architecture.md` §9.1's docker-compose schematic lists only one `tei-embed` service — no `tei-embed-sparse`
- `06-api-contracts.md`'s `/ready` response schema (`ServiceHealth`) checks only `tei_embed: bool` — a deployer following this schema would never know a second embedding service should exist
- `20-agent-behavior.md` §6's failure table has one row for "TEI embedding service unreachable" — doesn't distinguish dense-down vs. sparse-down vs. both-down; no documented degraded-mode behavior when sparse is unavailable but dense works
- `09-deployment-ops.md` defers to `04-architecture.md` §9.1's docker-compose service list, which is incomplete

REQ-003's acceptance criterion requires "both a dense-vector score and a sparse-vector score are present and independently contribute to the fused ranking." A deployer following the canonical docker-compose would have no sparse embedding service and REQ-003 would be unreachable.

Why this might be a self-review blind spot: DEC-142's Drift Log entry lists the files it propagated to — `04-architecture.md` (summary, tech-stack table, VRAM), `05-data-model.md`, `07-database.md`, `02-requirements.md` — notably **not** the four deployment-surface files above. A same-family reviewer checking the Drift Log's own propagation list would confirm each listed file was updated and miss the four that weren't even on the list.

Suggested fix: Add `tei-embed-sparse` to `04-architecture.md` §9.1's service list, add `tei_embed_sparse: bool` to `ServiceHealth`, split the failure-table row into dense-down/sparse-down/both-down with explicit behavior for each, and update `09-deployment-ops.md`'s service-list reference. Re-run DEC-142's propagation against the entity name `tei_embed` (not just the DEC id) across all spec files.

**Status**: ✅ Fixed 2026-07-16 — DEC-146. `04-architecture.md` §9.1's docker-compose schematic and `/ready` dependency list now name `tei-embed-sparse` explicitly; `06-api-contracts.md`'s `ServiceHealth` schema and both worked `/ready` examples gained `tei_embed_sparse: boolean`; `20-agent-behavior.md` §6's single failure-table row split into three (dense-down, sparse-down, both-down), all fail-closed/503 — sparse-down explicitly has no degraded dense-only mode; `09-deployment-ops.md`'s component list now names both TEI services directly instead of only inheriting from §9.1. Also covers R.11 (same root cause, same fix).

---

### R.2 [CRITICAL] — Requirement/architecture soundness (NFR-001 unverifiable)

File: `04-architecture.md` §4.2.2, `02-requirements.md` NFR-001

Issue: The VRAM allocation table in §4.2.2 carries an explicit note: the SPLADE model's VRAM footprint is unsized, and warm-cache headroom (~1.7 GB) is "understated." NFR-001 requires the eval suite to pass RAGAS thresholds on the 24 GB floor rig. With an unsized VRAM row, it's impossible to verify the floor rig actually fits. NFR-001 is stated as a verifiable acceptance criterion but depends on a measurement that hasn't been made.

Separately, the `confirmed-context.md` Drift Log's own 2026-07-13 verification-language note admits that "verified"/"PASS" entries describe design-document consistency checks, not empirical measurements. The VRAM numbers that NFR-001 depends on have been recalculated (not measured) across multiple rounds. Every "PASS" on the VRAM budget is a spreadsheet pass, not a hardware pass.

Why this might be a self-review blind spot: The gap is transparently flagged in the architecture — a reviewer sees the "Known gap" note and treats it as properly documented rather than as a condition that makes an NFR acceptance criterion unverifiable.

Suggested fix: Either (a) select the SPLADE model, measure its VRAM, and confirm the 24 GB floor still holds, or (b) split NFR-001's acceptance criterion: the eval-suite pass on the floor rig is now gated on the SPLADE model being selected and measured first, and the current criterion is explicitly `[blocked-on-DEC-142-measurement]`. Don't leave a verifiable-sounding criterion backed by a known-incomplete budget.

**Status**: ✅ Fixed 2026-07-16 — DEC-146, option (b). `02-requirements.md`'s NFR-001 acceptance-criteria column now carries an explicit `[blocked-on-DEC-142-measurement]` marker on the floor-rig pass claim. No VRAM number invented — this agent sandbox has no GPU to measure the SPLADE model's actual footprint (per `docs/agents/dev-environment.md`), so option (a) wasn't reachable here.

---

### R.3 [CRITICAL] — Cross-reference integrity (Group F — TASK-040 orphaned)

File: `specs/10-build-plan.md:478-504` (TASK-040), `specs/11-test-plan.md`, `specs/12-verification.md`

Issue: TASK-040 (Admin-Scope JWT Claims Verification, added 2026-07-16 per DEC-145) has zero coverage in `11-test-plan.md` (no TEST-###) and zero coverage in `12-verification.md` (no VG-###). Independent grep confirmed: `TASK-040` appears exactly once in all of `specs/` (in `10-build-plan.md` itself), never in the test plan or verification plan. Separately, TEST-041 (per-rail latency, NFR-022, added 2026-07-13) is also orphaned — no TASK and no VG. Two orphaned IDs on opposite sides, neither linked to the other.

Why this might be a self-review blind spot: The DEC-145 re-audit note states Gate 7 was re-checked and returned PASS. The task structure is compliant (TDD Red/Green/Refactor, 3 ACs, Verification Evidence), so Gate 7's check on task-internal form passed. Gate 8 checks "do referenced IDs exist," not "does every new TASK have its own TEST/VG." A reviewer running the standard procedure would see both gates PASS while the traceability chain is broken.

Suggested fix: Add TEST-042 (Security: "Valid JWT with insufficient scope returns 403 on every admin route") in `11-test-plan.md` and VG-037 in `12-verification.md`. Register both in `00-index.md`. Extend the Gate 8 re-audit procedure with a completeness check: for every TASK added since the last sweep, confirm both a TEST and a VG exist. This is a procedural gap, not a content gap — the task's content is fine, the registration step was missed.

**Status**: ✅ Fixed 2026-07-16 — DEC-147. New `TEST-042` (Security: insufficiently-scoped JWT returns 403 on every admin route) and `VG-038` register `TASK-040`'s coverage; new `VG-037` separately closes `TEST-041`'s own orphan gap (per-rail latency, `NFR-022`), with `NFR-022` added to `TASK-018`/`TASK-020`/`TASK-021`'s Related Requirements — the three rails it actually budgets. `TASK-040`'s Verification Evidence field now names `TEST-042`/`VG-038` explicitly.

---

### R.4 [HIGH] — Cross-reference integrity (Group F — VG-018 references wrong test)

File: `specs/12-verification.md` VG-018

Issue: VG-018 (REQ-047, Redis cache) cites TEST-025 as its evidence. TEST-025 is defined as "Cold install to first successful query … `/ready: true` within 30 min" — an install-timing test, not a cache test. No test in `11-test-plan.md` covers Redis cache hit/miss/TTL discipline in general (TEST-012 covers only legal-hold cache invalidation, not general cache behavior). TASK-025's Verification Evidence field says "Cache-hit/invalidation test suite" without naming a specific TEST-###. The chain is broken at the TEST link: TASK-025 → (no TEST) → VG-018 → (references wrong TEST).

Why this might be a self-review blind spot: The VG table lists TEST-025 because the VG author saw "TASK-025 (Redis cache)" and assumed TEST-025 was the corresponding test — a numbering coincidence (TASK-025 ↔ TEST-025) that happens to be wrong.

Suggested fix: Create a dedicated TEST for Redis cache behavior (hit/miss/TTL/force-refresh) in `11-test-plan.md` and point VG-018 at it. The numbering coincidence (TASK-025 ≠ TEST-025) is a cautionary tale — don't renumber to match, just cross-reference correctly.

**Status**: ✅ Fixed 2026-07-16 — DEC-147. New `TEST-043` (general Redis cache hit/miss/TTL/force-refresh — a real gap, since `TEST-012` covers only legal-hold invalidation) replaces `VG-018`'s wrong `TEST-025` citation; `TASK-025`'s Verification Evidence field now names `TEST-043` explicitly instead of the unspecific "cache-hit/invalidation test suite."

---

### R.5 [HIGH] — Cross-reference integrity (Group F — NFR coverage gaps in build plan)

File: `specs/10-build-plan.md` (TASK Related Requirements fields), `specs/02-requirements.md` (NFR-001..033)

Issue: 8 MVP-scoped NFRs have no implementing TASK in `10-build-plan.md`. The Group F subagent's systematic sweep found:
- **NFR-005** (latency SLO p95 ≤ 8s) — no TASK builds or measures end-to-end latency against the SLO
- **NFR-006** (ingest throughput ≥ 100 pages/min) — TEST-033 exists but has no implementing TASK
- **NFR-008** (no content logging at INFO) — no TASK builds or checks this constraint
- **NFR-017** (rate limiting) — TEST-028 exists but has no building TASK
- **NFR-019** (offline model bundle) — TASK-031 covers install timing but not bundle creation/verification
- **NFR-022** (per-rail latency budget) — TEST-041 exists but has no building TASK (TEST-041 itself is orphaned — see R.3)
- **NFR-030** (VRAM admission control) — no TASK implements queuing-on-low-VRAM
- **NFR-031** (cold-cache burst visibility) — no TASK implements `queue_depth` widget surface

The DEC-129 NFR sweep (2026-07-08) closed 6 NFR→TASK gaps but scoped itself to "zero coverage of any kind" — NFRs that had a TEST but no TASK were not in scope for that round. The remaining 8 are NFRs with TEST coverage but no TASK ownership, meaning the test plan asserts behavior that no build-plan task is responsible for implementing.

Why this might be a self-review blind spot: Each prior Gate 8 sweep was scoped to specific named findings, not a from-scratch NFR→TASK sweep. The DEC-129 round explicitly noted its scope was "zero coverage of any kind." A reviewer running the standard Gate 8 procedure (check that referenced IDs resolve) would see NFR-005 referenced by TEST-032 and confirm the cross-reference — without noticing that no TASK builds the thing TEST-032 measures.

Suggested fix: For each of the 8 NFRs, either (a) add the NFR to an existing TASK's Related Requirements field (if the task already implements the capability), or (b) extend the task's acceptance criteria to explicitly cover the NFR, or (c) create a new TASK. The TESTs already exist — the gap is the build-plan ownership link between "this NFR exists" and "this TASK builds it."

**Status**: ✅ Fixed 2026-07-16 — DEC-147, resolved per-NFR rather than uniformly. `NFR-006`/`NFR-008`/`NFR-019` linked to the existing tasks that naturally build what they constrain (`TASK-009`, `TASK-027`, `TASK-031` — the latter also gained a new bundle-build/verify Verification Plan bullet, AC, and Verification Evidence entry). `NFR-022` closed via R.3's `TASK-040`/`TEST-041` fix above. The remaining three had no natural existing owner and got new tasks: `TASK-041` (E2E query latency, Phase 6, `NFR-005`), `TASK-042` (API rate limiting, Phase 2, `NFR-017`), `TASK-043` (VRAM admission control + queue-depth visibility, Phase 3, bundles `NFR-030`+`NFR-031` as one subsystem).

---

### R.6 [HIGH] — Cross-reference integrity (Group F — REQ-005 NLI half ungated)

File: `specs/12-verification.md` VG-005

Issue: REQ-005 requires both (a) mechanical citation verification AND (b) NLI entailment check. VG-005 references TEST-001, TEST-002, TEST-021, TEST-022 — all four are mechanical-path tests from the `verify/` parser strict-mode section. None exercises the NLI entailment half of REQ-005. The E2E TEST-023 would exercise the combined path but is not referenced by VG-005. REQ-005's NLI half has no verification gate.

Why this might be a self-review blind spot: The four mechanical-path tests are correctly cross-referenced and internally consistent. A reviewer checking VG-005 sees four valid TEST references and confirms they resolve — without noticing that REQ-005's acceptance criterion has two parts and only part (a) is gated.

Suggested fix: Add TEST-023 (E2E happy path, which exercises the combined mechanical+NLI path) to VG-005's Evidence Required column, or add a dedicated NLI-path integration test and reference it. The gate should cover both halves of the requirement it gates.

**Status**: ✅ Fixed 2026-07-16 — DEC-147. `TEST-023` (E2E happy path, which exercises the combined mechanical+NLI path) added to `VG-005`'s Evidence Required column — `REQ-005`'s NLI half now has a gate.

---

### R.7 [HIGH] — Unverified factual claim (Group D → Group A)

File: `specs/13-decision-log.md` DEC-012, `specs/01-product-brief.md` §2.1

Issue: DEC-012 (2026-06-25) states "TGI is in HuggingFace maintenance mode since Dec 2025" as rationale for excluding Text Generation Inference. TGI (`text-generation-inference`) is actively maintained — its GitHub repository shows ongoing releases throughout 2026 (v2 architecture has been shipping). The claim reads like training-data recall based on HuggingFace's late-2024 announcement about TGI v1 entering maintenance. The 2026-07-13 cross-model review didn't flag this. Separately, `01-product-brief.md` §2.1's competitive-positioning claims about Copilot/AWS Q Business/Glean remain `[unconfirmed]` per the Stage 5 Round 4 review (2026-07-03, rated HIGH) — the user declined to verify them, and the `[unconfirmed]` tag exists only in the frozen review-memos file, not in the live product brief where the claims read as settled facts.

Why this might be a self-review blind spot: Both claims are "background color" rather than load-bearing architecture — vLLM would likely have been chosen regardless of TGI's status, and the competitive positioning is marketing framing, not engineering specification. A reviewer focused on technical correctness skips decorative claims; a reviewer who does read them might share the same training-data recall and accept them.

Suggested fix: For DEC-012, correct the "Alternatives rejected" column to reflect TGI's actual mid-2026 status, or verify and update the claim. For §2.1, add `[unconfirmed — verify before vendor pitch]` annotations directly in the live product brief, matching the existing `[unconfirmed exact 2026 status]` tag on the AU Privacy Act row.

**Status**: ❌ Declined — the DEC-012/TGI half of this finding is disproven. Live verification via `gh api` against `huggingface/text-generation-inference` found: no releases after 2025-12-19, a commit literally titled "Maintenance mode" (PR [#3345](https://github.com/huggingface/text-generation-inference/pull/3345), merged 2025-12-11), and the current live README carrying a `[!CAUTION]` banner recommending vLLM/SGLang instead of TGI. DEC-012's original claim ("TGI in maintenance mode since Dec 2025") is correct — the review's own rebuttal ("actively maintained... v2 architecture shipping throughout 2026") does not hold up against the actual repository state and reads like the same training-data-recall failure mode this finding accused DEC-012 of. `DEC-012` left unchanged; the verification is recorded in `DEC-146`'s own Rationale text. The second half of this finding (the `01-product-brief.md` §2.1 hedge) was real and is fixed under R.9's Status below, where R.9's own "only in the frozen review-memos file" framing is also corrected as inaccurate.

---

### R.8 [HIGH] — Unverified technical claim (Group B → DEC-142 quality regression)

File: `specs/04-architecture.md` §4.1 (Doc parsing), `confirmed-context.md` Drift Log DEC-143

Issue: DEC-143 (2026-07-15) removed Unstructured.io as PDF parser, moving to `pdfminer.six` + PyMuPDF, because Unstructured's `partition.pdf` had an unconditional torch/OCR dependency. The decision is justified on dependency-weight grounds, but the "Cost accepted" section only notes that "PDF parsing no longer benefits from Unstructured's unified, structured element output." No evaluation was performed on whether `pdfminer.six`'s `extract_text()` produces comparable text-extraction quality for CCM-style business documents (tables, headers, footers, multi-column layouts). DEC-036 originally chose Unstructured for "80% of formats with consistent chunk metadata." The quality regression was accepted without measurement — the same pattern as DEC-142 (TEI sparse) and DEC-141 (Qdrant payload index): a capability claim that held until someone actually tried to use it.

Why this might be a self-review blind spot: The decision was made during implementation (2026-07-15, `document-ingest-pipeline` Issue 02), when the blocking dependency issue was the immediate concern. The quality-impact question is a different concern that the implementation-time decision didn't scope itself to answer.

Suggested fix: Not a spec reversion — `pdfminer.six` is the correct pragmatic choice for MVP. Add an open item to `04-architecture.md`'s Doc-parsing row: "Text-extraction quality of `pdfminer.six` vs. Unstructured.io on CCM-style business documents (tables, multi-column) has not been measured — flag for first golden-set eval run." This is a measurement deferral, not a design change.

**Status**: ✅ Fixed 2026-07-16 — DEC-148. `04-architecture.md`'s Doc-parsing row gained an open item, applied essentially as suggested: text-extraction quality of `pdfminer.six` vs. Unstructured.io on CCM-style business documents (tables, multi-column) is unmeasured, flagged for the first golden-set eval run. Measurement deferral, not a design reversion — `pdfminer.six` remains the correct pragmatic MVP choice per DEC-143.

---

### R.9 [MEDIUM] — Cross-reference integrity (Group E → Group A)

File: `specs/92-stage5-review-memos.md` R4-F6, `specs/01-product-brief.md` §2.1

Issue: Stage 5 Round 4 finding F6 flagged competitor capability claims (`[unconfirmed]`) as HIGH — user declined to verify. The `[unconfirmed]` tag exists only in the frozen review-memos file. The active product brief states the claims as unqualified assertions. A reader of the product brief alone sees settled competitive analysis; only cross-reading the 94K review-memos file reveals the claims were flagged and never verified.

**Status**: ✅ Fixed 2026-07-16 — DEC-148 (tracked jointly with R.7's second half). `01-product-brief.md` §2.1 gained an `[unconfirmed exact state]` hedge directly on the competitor-claims table, matching the existing AU Privacy Act row's precedent. Correction to this finding's own framing: the claim that the tag "exists only in the frozen review-memos file" was checked and found inaccurate — `RISK-020` in the same live product brief already carried an equivalent hedge for the identical claims; the real gap was narrower (no hedge at the table itself), and that's what got fixed.

---

### R.10 [MEDIUM] — Unverified technical claim (Group A → Group C)

File: `specs/02-requirements.md` REQ-003 AC, `specs/23-evals-guardrails.md` §2.2

Issue: REQ-003's acceptance criterion requires "reranking measurably improves NDCG over dense-only on the golden set." NDCG requires per-chunk relevance judgments — a labeling methodology, inter-annotator agreement threshold, and judgment scale. None of these are defined anywhere in `specs/`. The golden set defines prompt categories but not per-chunk relevance labels. The RAGAS metrics in §9.1 (faithfulness, answer relevancy, context precision, context recall) don't include NDCG. An implementer tasked with verifying NDCG improvement has no methodology for producing the relevance judgments NDCG requires.

Suggested fix: Either (a) add a relevance-judgment methodology to `23-evals-guardrails.md`'s golden-set section, or (b) replace NDCG with a metric the spec already defines the inputs for (e.g. context precision, which RAGAS computes without per-chunk labels).

**Status**: ✅ Fixed 2026-07-16 — DEC-148, suggested option (b). `REQ-003`'s acceptance criterion corrected from "NDCG" to RAGAS context precision, which this spec set already defines with a real MVP threshold (`23-evals-guardrails.md` §2.1, ≥0.70) computed without per-chunk relevance labels. Also fixed the same stale "NDCG" reference in `.scratch/document-ingest-pipeline/PRD.md` (still `ready-for-agent`, not yet implemented, so the in-flight citation needed updating per `update-specs`'s own rule).

---

### R.11 [MEDIUM] — Requirement/architecture soundness (Group B — failure table stale)

File: `specs/20-agent-behavior.md` §6

Issue: After DEC-142, there are two TEI embedding services (dense + sparse). The failure table has one row for "TEI embedding service unreachable." It doesn't distinguish dense-down (no hybrid retrieval possible → 503), sparse-down (dense-only retrieval works but REQ-003's sparse-score criterion is violated → no documented degraded mode), or both-down. This directly affects test coverage — no test specifies expected behavior when only sparse is unreachable.

**Status**: ✅ Fixed 2026-07-16 — folded into R.1's fix (DEC-146); no separate action needed. See R.1's Status above.

---

### R.12 [MEDIUM] — Overconfidence (Group C → Group A)

File: `specs/23-evals-guardrails.md` §8, `specs/08-observability-logs.md` line ~134

Issue: Two overconfidence instances: (1) `23-evals-guardrails.md` §8's open questions are dismissed with "Answered in Stage 5 architecture review memos" — an unresolvable forward reference that buries nuanced answers (thresholds are starting points, NLI calibration is deferred) behind a one-line dismissal. (2) `08-observability-logs.md` claims OTel GenAI spans require "no GroundedDocs-specific translation needed" — but NFR-033's domain-specific attributes extend well beyond standard OTel GenAI conventions. A customer's existing Datadog/Grafana pipeline will see none of the custom attributes without configuration.

**Status**: ✅ Fixed 2026-07-16 — DEC-148. `23-evals-guardrails.md` §8's dead-end "Answered in Stage 5 architecture review memos" replaced with a substantive pointer naming `92-stage5-review-memos.md`'s own Stage 5 topic coverage matrix (T1-T8). `08-observability-logs.md`'s OTLP line clarified to distinguish ingestion (true, no translation needed) from dashboard visualization (custom `NFR-033` attributes arrive intact but have no pre-built widgets in a customer's existing Datadog/Grafana setup without configuration).

---

### R.13 [MEDIUM] — Overconfidence / groupthink (Group D)

File: `specs/14-spec-audit-report.md` (full), `specs/confirmed-context.md` Drift Log header

Issue: ~12+ consecutive READY/PASS verdicts since 2026-07-06, including on content later proven wrong by cross-model review (30 findings the self-audits all missed). The Drift Log's own note admits "verified"/"PASS" means design-document consistency check, not empirical validation. The combination of recurring READY verdicts, known history of missed issues, and acknowledged verification ceiling is a standing overconfidence pattern. The formulaic "PASS, no open gap" closing on ~12 consecutive re-audit notes — regardless of whether the note records a minor citation fix or a major architecture correction — reinforces it.

**Status**: Acknowledged, no spec edit. Per `14-spec-audit-report.md`'s DEC-148 Re-audit Note: this is a standing self-audit-overconfidence pattern that the file's own growing body of evidence-cited Re-audit Notes is already the practical response to, not something a single edit fixes.

---

### R.14 [MEDIUM] — Domain plausibility (Group A)

File: `specs/01-product-brief.md` §8, `specs/42-compliance-security.md`

Issue: The product is positioned for AU/NZ public-sector procurement with docker-compose as the deployment artifact. AU government IT procurement typically requires formal vendor assessment, IRAP assessment for protected data, and ASD Essential 8 alignment — docker-compose is not a production deployment mechanism that passes government infosec review. The spec acknowledges this as deferred (RISK-021) and `09-deployment-ops.md` includes a compliance-posture section, but no spec file distinguishes "demo-ready" from "government-procurement-ready" deployment posture.

**Status**: ✅ Fixed 2026-07-16 — DEC-148. `42-compliance-security.md`'s Access Control section gained an explicit "demo-ready is not government-procurement-ready" line. The underlying facts (`RISK-021`, the Explicit Scope Boundary's IRAP/Essential-8 exclusion) already existed — this just states the distinction directly instead of leaving it to be inferred.

---

### R.15 [MEDIUM] — Cross-reference integrity (Group F — 12 tests have no VG)

File: `specs/11-test-plan.md`, `specs/12-verification.md`

Issue: The Group F subagent identified 12 TEST-### entries with no corresponding VG-### in `12-verification.md`, including TEST-008 (PDP circuit breaker, NFR-016 — a safety property with no release gate), TEST-028 (rate limiting, NFR-017), TEST-033 (ingest throughput, NFR-006), and TEST-041 (per-rail latency, NFR-022). The Security Verification section uses a bulk checkbox ("TEST-027 through TEST-031 all pass") that provides weak coverage but doesn't give individual tests their own pass criteria. The TASK→TEST link is also informal throughout — most TASK Verification Evidence fields say "test output" or "test suite" without naming a specific TEST-###, making automated traceability impossible.

**Status**: ✅ Fixed 2026-07-16 — DEC-147 (expanded to include this finding alongside R.3-R.6). Of the review's named orphaned tests, `TEST-041`/`TEST-042` were already closed by R.3's fix; 8 more (`TEST-004`, `TEST-008`, `TEST-018`, `TEST-019`, `TEST-028`, `TEST-030`, `TEST-033`, `TEST-034`) had no gate mechanism at all — new `VG-039`..`VG-046` close them. The remaining 3 (`TEST-015`, `TEST-016`, `TEST-017`) were already release-blocking via the separate Release Gates table (`DEC-092`/`DEC-109`'s rows) — not a coverage gap, just a missing cross-reference by test id, added directly in that table. The bulk-checkbox and informal-TASK-link observations are noted but not separately actioned — no suggested fix was given for those two sub-points beyond the id-level gaps this fix closes.

---

### R.16 [LOW] — Stale pattern recurrence (Group E → process)

File: `specs/92-stage5-review-memos.md` Round 5, `specs/14-spec-audit-report.md` re-audit notes

Issue: The "fix doesn't propagate to every touched document" pattern — named explicitly in Round 5 (DEC-096, DEC-098, DEC-108) — has recurred in DEC-139's re-audit (two pre-existing `00-index.md` citation gaps found in passing) and DEC-144/145's re-audit (stale `06-api-contracts.md` Group-B description fixed while touching the row). The `update-specs` skill's Step 1 (grep both ID and entity name) exists but hasn't eliminated the pattern — the skill is used at implementation time but its propagation claim isn't re-verified at review time.

**Status**: Acknowledged, no spec edit. This is a process-recurrence observation, not `specs/` content — logged in `.scratch/session-feedback.md` instead, per `CLAUDE.md`'s own distinction between the two. Worth noting the pattern recurred a further two times within this same session, reinforcing the observation: DEC-146 itself existed only to fix DEC-142's incomplete propagation, and TASK-040 needed its own phase-placement fix before this session's cross-model-review work even started.

---

### R.17 [LOW] — Cross-reference (Group C → undefined CLI surface)

File: `specs/08-observability-logs.md` lines ~139-141

Issue: References `cli eval promote --from-traces <timerange>` as the MVP trace-to-regression promotion command. The `cli eval` family is defined in `23-evals-guardrails.md` §2.3 (`run`, `report`) but `promote` is not listed there. The command name exists only in this offhand reference.

**Status**: ✅ Fixed 2026-07-16 — DEC-148. `cli eval promote --from-traces <timerange>` added to `23-evals-guardrails.md` §2.3's `cli eval` command family alongside `run`/`report`. No behavior change — the command was already used and specified in `08-observability-logs.md`, just never listed in its own defining section.

---

### R.18 [LOW] — Domain plausibility (Group A → Group C)

File: `specs/08-observability-logs.md` §Metrics, `specs/02-requirements.md` NFR-024

Issue: The `cost_per_turn` formula uses `gpu_hourly_rate` defaulting to RunPod 4090-spot ($0.45/h) — a cloud-rental proxy. The formula correctly notes that on-prem customers should override the rate, but NFR-024's alert ceiling (¥0.10/turn) was calibrated against the cloud proxy. A customer on owned hardware with different amortized cost gets meaningless alerts. This is a known limitation (the formula is clearly documented), but worth naming since the on-prem cost story is central to the product's positioning.

**Status**: Acknowledged, no spec edit. The review's own text already calls this "a known limitation... clearly documented" — no further spec change identified.

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 3 |
| HIGH     | 5 |
| MEDIUM   | 7 |
| LOW      | 3 |

This is the second cross-model review of this spec set. The 2026-07-13 review found 30 issues (15 CRITICAL/HIGH); this review finds 18 (8 CRITICAL/HIGH) — a measurable improvement. The prior review's fixes worked: no stale model names, no broken DEC cross-references, no un-resolved review-memo findings were found this round.

The remaining issues cluster in three categories:

1. **Incomplete propagation of the most recent DECs** (R.1, R.2, R.3, R.8). DEC-142 (sparse embedding split, 2026-07-15) and DEC-145 (admin-scope gap + TASK-040, 2026-07-16) are the two most recent decisions. Both have incomplete propagation: DEC-142 missed 4 deployment-surface files; TASK-040 was added without TEST/VG registration. The `update-specs` skill's propagation step works for older DECs but the most recent ones — added in the same session or immediately before this review — consistently have gaps. The fix is procedural: run a propagation-completeness check immediately before any cross-model review, not just at DEC-authoring time.

2. **NFR→TASK coverage gaps in the build plan** (R.5, R.6). The functional-requirement chain (REQ→TASK) is solid (30/30). The non-functional chain is not: 8 MVP NFRs lack implementing TASKs. The prior DEC-129 NFR sweep deliberately scoped itself to "zero coverage of any kind," leaving NFRs with TEST-but-no-TASK unaddressed. A dedicated NFR→TASK sweep (matching the existing REQ→TASK sweep) would close this.

3. **Factual claims from the Stage 2-4 authoring window that were never live-verified** (R.7, R.10). DEC-012's TGI claim and the competitive-positioning assertions in §2.1 date from the original authoring window (2026-06-25/27), before the cross-model review and live-verification disciplines existed. Neither is load-bearing for the architecture, but both erode the spec set's credibility.

Compared to the prior review's 30 findings spanning architecture errors, stale model names, and pervasive propagation failures, this review's 18 findings are narrower and more procedural. The spec set's technical content has substantially improved. The three CRITICAL findings are all fixable in a single pass — each is a propagation-registration gap, not a design error.

Verdict: **BLOCK** — R.1 (DEC-142 deployment-surface propagation), R.2 (NFR-001 unverifiable with unsized VRAM), and R.3 (TASK-040 missing TEST/VG) must be resolved.

## Triage Disposition (2026-07-16, same day)

All 18 findings were independently re-verified against actual spec content before any fix was applied, per this project's standing practice of not trusting an external review's severity labels at face value — see each finding's own **Status** line above for the specific evidence and disposition. Unlike the prior (2026-07-13) review, verification here surfaced one finding (R.7) whose own technical premise was wrong, not just a spec gap to close.

**Final disposition, all 18 findings**:
- **14 fixed** (R.1–R.6, R.8–R.12, R.14, R.15, R.17) — including R.11 folded into R.1's fix (same root cause, same DEC-146) and R.15 folded into R.3–R.6's DEC-147 batch (same traceability-registration character)
- **1 declined — finding disproven** (R.7) — DEC-012's original "TGI in maintenance mode since Dec 2025" claim was independently re-verified correct via live `gh api` checks against the actual `huggingface/text-generation-inference` repository (no releases after 2025-12-19, a "Maintenance mode" PR merged 2025-12-11, a live `[!CAUTION]` banner recommending vLLM/SGLang); the review's own rebuttal did not hold up. `DEC-012` left unchanged. This finding's second half (a missing hedge on `01-product-brief.md`'s competitor-claims table) was real and is fixed under R.9.
- **3 acknowledged, no spec edit** (R.13, R.16, R.18) — each for a stated reason on its own Status line: R.13 is a standing self-audit-overconfidence pattern the audit file's own growing body of evidence-cited Re-audit Notes already addresses in practice, not something a single edit fixes; R.16 is a process-recurrence observation that belongs in `.scratch/session-feedback.md`, not `specs/` content; R.18 the review's own text already calls the limitation adequately documented.

**Three new decisions minted during triage**: **DEC-146** (R.1/R.2/R.11 — completes DEC-142's deployment-surface propagation, makes NFR-001 honest about the unmeasured VRAM gap), **DEC-147** (R.3/R.4/R.5/R.6/R.15 — closes the build-plan traceability gaps: orphaned TASK-040/TEST-041, wrong VG-018 citation, an 8-NFR ownership sweep, REQ-005's ungated NLI half, 8 further orphaned tests), **DEC-148** (R.8/R.9/R.10/R.12/R.14/R.17 — documentation-clarity fixes plus one acceptance-criterion correction, NDCG → RAGAS context precision).

**Post-triage severity count**: 3 CRITICAL (all fixed), 5 HIGH (4 fixed — R.4/R.5/R.6/R.8 — plus R.7 independently disproven rather than fixed), 7 MEDIUM (6 fixed, 1 acknowledged), 3 LOW (1 fixed, 2 acknowledged). **Nothing remains outstanding in the CRITICAL or HIGH tier.** The BLOCK verdict above reflects the spec set's state at review time, before this triage pass; it is not a live status. Current spec-audit verdict: **READY** (`14-spec-audit-report.md`, re-audited across three dated Re-audit Notes covering this triage's fixes).
