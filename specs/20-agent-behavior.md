# 20 — Agent Behavior

> Stage 4 deliverable (companion to `04-architecture.md` §10).
> MVP = single-step (no agent loop). V2 = ReAct fallback. V3 = TruLens drift monitoring.
> Detailed prompt templates: `24-prompt-registry.md`. Eval & guardrails: `23-evals-guardrails.md`.

## 1. Plain-English summary

> **Round 2 supersede (DEC-075 + DEC-077, 2026-06-29)**: The MVP pipeline is now expressed as a **LangGraph 1.2.x typed-state graph** (version corrected 2026-07-08, DEC-131) with explicit safety-rail nodes. The MVP graph runs **one-shot** (no cyclic feedback edges enabled) and so remains "not a multi-step agent" by behavior; V2 enables the feedback edge from `verify/` back to `generate/` (REQ-020) and the ReAct branch. The single-turn anti-hallucination guarantee is preserved.

In the MVP, GroundedDocs is **not a multi-step agent**. It is a single graph traversal: input-rail check → one retrieval → ACL trim → rerank → one generation → output-rail check → one verification → one audit. Refusal is a typed product response, not an error. This deliberate narrowness is the anti-hallucination foundation — every assertion ships through `verify/`, and the model never decides on its own to take a second action.

In V2, GroundedDocs gains a **bounded ReAct fallback** and a **mid-flight rewriting feedback edge** (REQ-020): when single-step retrieval fails a recall test, the system may decompose the query into sub-questions; when verify finds ungrounded claims, the failed-claim list can be sent back to `generate/` for a targeted re-prompt. Each sub-step still flows through the same `verify/` gate, and a hard iteration cap prevents drift.

## 2. MVP agent shape (DEC-039 + DEC-075 + DEC-077 + DEC-082)

### 2.1 Turn pipeline (LangGraph nodes per DEC-075 / DEC-082)

> **Round 3 supersede (DEC-082, 2026-06-29)**: `safety_input/` and `retrieve/` run as **parallel fan-out edges** from `api/`, joined at `acl/`. The `acl/` join discards retrieval output when `safety_input` flagged. `verify/` is explicitly bifurcated into `mechanical_fast_path` (≤1 ms, early-exit) and `nli_slow_path` (≤600 ms, runs only after mechanical pass). Saves ~150 ms on the warm-cache hot path. Pipeline diagram updated accordingly.

```
user query
   │
   ▼
api/                       (constructs LangGraph state from HTTP request)
   │ state.invoke()
   │
   ├─────────────────┬──────────────────  ← parallel fan-out per DEC-082
   │                 │
   ▼                 ▼
safety_input/    retrieve/
(Llama Prompt    (hybrid: dense + sparse;
 Guard 2 —        Layer-1 ACL filter
 DEC-077)         pushdown per §7B.3 +
                  DEC-046)
   │                 │
   └────────┬────────┘  ← join at acl/
            ▼
acl/                       (Layer-2 JIT live PDP trim via ECMAdapter; circuit
   │                        breaker DEC-063; if safety_input flagged → discard
   │                        retrieval, route policy_blocked. If retrieval-rail
   │                        Llama Prompt Guard 2 flags too many chunks →
   │                        verification_unavailable refusal)
   ▼
rerank/                    (TEI bge-reranker-v2-m3; ONNX Runtime backend,
   │                        MVP default per DEC-093 / NFR-027 — produces
   │                        reranked_set, the authorized set passed to generate/)
   ▼
generate/                  (prompt assembled from reranked_set (authorized) chunks
   │                        + per-customer template; vLLM call with chunked-prefill
   │                        per DEC-083; cache lookups via Redis — DEC-076)
   ▼
safety_output/             (Llama Guard 3 8B int4 AWQ — DEC-077 + DEC-082;
   │                        classify draft answer for harmful categories;
   │                        on flag → policy_blocked terminal state)
   ▼
verify/.mechanical_fast_path                       ← DEC-082 explicit split
   │ (≤1 ms; regex/dict; checks citations against reranked_set,
   │  NOT the raw retrieval_set — DEC-088; early-exit on fail →
   │  low_grounding refusal without entering NLI)
   ▼
verify/.nli_slow_path
   │ (≤600 ms warm; DeBERTa NLI; only runs if
   │  mechanical passed; MVP terminal — V2 may
   │  emit `regenerate` back-edge to generate/
   │  with failed-claim list)
   ▼
audit/                     (context fingerprint persisted incl. safety-rail adapter/
   │                        version + policy ruleset version (DEC-089) + safety-rail
   │                        verdicts + verify path taken (mechanical_fast / nli_slow)
   │                        + revision_count; citations stored as verbatim snapshot,
   │                        not chunk_id pointers (DEC-087))
   ▼
api/ → user                (terminal state surfaced to caller)
```

The `policy/` orchestration rail (NeMo Guardrails) composes with this graph by intercepting node-to-node state transitions — it can escalate refusal class, force an audit trigger, or block a transition based on declarative policy rules (DEC-077).

### 2.2 What the model is allowed to do

- Read the query and the retrieved chunks
- Produce an answer with citations
- Nothing else

### 2.3 What the model is not allowed to do

- Tool calls (no tools exposed)
- Web access (no outbound calls — REQ-012)
- Memory writes (no persistent memory in MVP)
- Decide to do more retrievals (`generate/` does not call `retrieve/`)
- Skip citations (the prompt requires citations on every assertion; `verify/` enforces)

### 2.4 Conversation memory

- Server-side only: `conversation_id` references the last N turns (N = 5 in MVP, configurable)
- `conversation_id` is a non-null column on `audit_events` (REQ-007 acceptance per RC-T3-02); server reads the last N turns from `audit_events` indexed by `conversation_id`
- Client-supplied conversation history is **ignored** (trend research §1.3 best practice: server reconstructs history)
- Rationale: prevents prompt-injection via fabricated prior turns

## 3. V2 — ReAct fallback (REQ-015)

### 3.1 Trigger

ReAct does not run by default. It triggers when:

- Retrieval top-1 score < `recall_trigger_threshold`, **and**
- Retrieved set diversity (cosine spread of top-K) < `diversity_trigger_threshold`

Both must hold. Either alone does not trigger.

### 3.2 Loop shape

```
think      → produce a sub-query (or "no more useful sub-queries")
   │
   ▼
sub_retrieve  → hybrid retrieve on the sub-query
   │
   ▼
verify/    → mechanical + NLI on sub-evidence (early failure shortcuts)
   │
   ▼ (if useful)
think      → next sub-query OR final answer
   │
   ▼ (final answer)
verify/    → full mechanical + NLI on assembled answer
   │
   ▼
audit/
```

### 3.3 Hard caps

| Knob | MVP-time decision | V2 ReAct decision (DEC-075 graph) | Reason |
|---|---|---|---|
| Iteration cap (ReAct sub-queries) | N/A (MVP no loop) | 3 sub-queries per turn (hard); 5 only with admin override | Empirical: more usually degrades grounding |
| **Mid-flight rewriting feedback (verify → generate) iteration cap (RC-R2-T8-04)** | **N=1 (single pass)** | **N≤2 mid-flight rewrites per turn (hard)** | **Bounded re-prompt loop; superlimit → refuse** |
| Per-turn token budget | 4000 in / 1000 out | 8000 in / 2000 out at peak (includes sub-query + rewrite context) | Caps cost; latency budget |
| **Cost ceiling per turn (RC-R2-T8-04)** | **Open-weights cost only (no commercial-API cost in MVP)** | **≤ ¥0.10 per turn at customer-chosen open-weights configuration; configurable** | **Cost-discipline NFR per benchmark §Topic 9** |
| Recall trigger threshold | calibrated against golden set | Same | Will not enable until V2 eval validates |
| Final verify must pass | yes | yes | No "partial credit" delivery |
| **V2 mid-flight rewrite prompt template (REQ-022 V2 extension, S6.2 Round 3)** | N/A (MVP no feedback edge) | **`rewrite_repair` template activated on `revision_count > 0`**; signature `(failed_claims, previous_answer, reranked_set) -> Prompt` (parameter corrected from `retrieval_set` to `reranked_set` per DEC-088 — the rewrite prompt must only offer the model the Layer-2-authorized chunk set, never the raw pre-authorization candidate pool). Body instructs the model to repair ONLY the listed failed claims, keeping the rest unchanged | Prevents wholesale rewrites that lose correct content; bounded by N≤2 iteration cap above |
| **V2 admin-configurable intent classifier (REQ-051, DEC-084, S3.1 Round 3)** | N/A | `intent_classifier/` node before parallel fan-out; per-intent policy may downgrade `nli_slow_path` to advisory (audit always records `nli_performed: bool` + intent class; per-customer SLA waiver required) | Latency saving for low-risk traffic without losing audit trail; mechanical fast-path + audit are non-negotiable |

### 3.4 Tool set (V2)

Exactly one tool: `sub_query_retrieve(query: str) -> chunks[]`.

No file system, no web, no SQL. The principle is from trend research §3.1: every tool widens prompt-injection blast radius, so tools are added only when their absence demonstrably hurts the customer task.

## 4. V2 — Review queue (REQ-016)

### 4.1 Routing rules

Admin defines per-category routing rules (e.g., regex over query, intent tag, document tag). Matching queries:

- Generate answer + verify normally
- Instead of returning to user immediately, hold the answer in a review queue with state `pending_review`
- Reviewer opens the queue, sees query + retrieved chunks + draft answer + NLI scores
- Reviewer takes one of three actions: **approve** (deliver as-is), **edit** (modify and deliver), **reject** (deliver a refusal)

### 4.2 Feedback into eval

Each reviewer verdict becomes a row in the customer-specific golden set (REQ-023) candidate list. Admin promotes selected verdicts into the regression set.

## 5. V3 — Production observability (REQ-027)

TruLens integrates as a tracing layer over the same pipeline. Drift detection triggers an LCC Tier 2 advisory recommendation (trend research §3.3 + DEC-028 Tier 2).

## 6. Behavior under failure (MVP, aligned with 5-class refusal taxonomy per DEC-042 / DEC-058, **layered-rail rows added per DEC-077**)

| Failure | Behavior | Refusal class |
|---|---|---|
| **`safety_input/` (Llama Prompt Guard 2) flags inbound query as prompt-injection / jailbreak (DEC-077)** | **Return refusal; rail verdict captured in audit; no generation attempt** | **`policy_blocked`** |
| **`acl/`'s retrieval-rail scan (Llama Prompt Guard 2, batched, runs after PDP trim per §8.1) flags too many retrieved chunks as poisoned content (DEC-077, corrected attribution DEC-096)** | **Flagged chunks dropped before `rerank/`; if drop rate exceeds threshold, return refusal; rail verdicts captured in audit** | **`verification_unavailable`** |
| Retrieval returns empty (or top-1 score below floor) | Return refusal; no generation attempt; offer up to 3 neighboring docs from post-Layer-2 set (REQ-006a) | `no_recall` |
| Layer 2 trim removed the last grounded chunk (user lacks ECM permission) | Return refusal; user-facing text depends on `acl_denial_mode` (transparent shows as-is; opaque masks as `no_recall`); audit always records actual | `access_denied` |
| **`safety_output/` (Llama Guard 3 8B) flags draft answer as harmful (DEC-077)** | **Return refusal; rail verdict captured in audit; answer not emitted; under V2 may trigger `regenerate` feedback edge once before refusing** | **`policy_blocked`** |
| **NeMo Guardrails policy escalates a normal answer into a refusal (DEC-077)** | **Return refusal of the policy-declared class; audit records the escalation rule** | (escalation can target any of the 5 classes) |
| Generation timeout | Return 504 with audit row written; client may retry with same conversation_id | (HTTP error — not a refusal class) |
| NLI service unreachable OR ECM PDP circuit breaker tripped (DEC-063) | Return refusal; system does not silently skip verification | `verification_unavailable` |
| vLLM unhealthy | Return 503; health check governs widget loading | (HTTP error — not a refusal class) |
| **TEI dense-embedding service (`tei-embed`, bge-m3) unreachable — sparse (`tei-embed-sparse`) still healthy (split 2026-07-16, DEC-146, from a single undifferentiated row added 2026-07-05)** — `retrieve/`'s hybrid search cannot produce a dense score at all | Return 503; health check governs widget loading, same as vLLM row | (HTTP error — not a refusal class) |
| **TEI sparse-embedding service (`tei-embed-sparse`, DEC-142's dedicated SPLADE model) unreachable — dense (`tei-embed`) still healthy (added 2026-07-16, DEC-146)** — `retrieve/` could technically still produce a dense-only score, but REQ-003's acceptance criterion requires both a dense-vector score and a sparse-vector score independently contributing to the fused ranking; **no degraded dense-only mode exists** — deliberately fail-closed, consistent with every other model-serving dependency's row in this table rather than a special-cased partial-availability path | Return 503; health check governs widget loading, same as the dense-down and both-down cases | (HTTP error — not a refusal class) |
| **Both TEI embedding services unreachable (added 2026-07-05 review finding, split 2026-07-16 to sit alongside the two single-service rows above, DEC-146)** — `retrieve/`'s hybrid search cannot embed the query at all | Return 503; health check governs widget loading, same as vLLM row | (HTTP error — not a refusal class) |
| **TEI reranker service unreachable (added 2026-07-05 review finding)** — `rerank/` cannot score the authorized chunk set | Return 503; health check governs widget loading, same as vLLM row | (HTTP error — not a refusal class) |
| Citation contains a chunk_id not in `reranked_set` (`mechanical_fast_path` fails, DEC-082 + DEC-088 — checked against the Layer-2-authorized, reranked set, not the raw pre-authorization retrieval pool) | **Early-exit short-circuit**: skip `nli_slow_path` entirely (saves ~600 ms); strip citations + return refusal without NLI cost | `low_grounding` |
| All mechanical checks pass but NLI fail rate exceeds threshold (`nli_slow_path`) | Grey out non-entailed sentences OR return refusal if grounding too weak; V2 may route via feedback edge to `generate/` (REQ-020, REQ-052 streaming) | `low_grounding` |
| **Mid-flight rewriting feedback iteration cap exceeded (V2, DEC-075 + RC-R2-T8-04)** | **Return refusal after N=2 rewrite attempts; audit records iteration count + failed-claim list** | **`low_grounding`** |
| Future: policy-routed category | Hold the answer; in MVP this trigger is dormant; V2 routes to review queue (REQ-016) | `policy_blocked` |

**Verification can never be silently skipped.** This is RISK-002 mitigation in code.

All refusal classes are returned as **HTTP 200 with typed `refusal_reason` field** (DEC-042). The audit log records both `refusal_reason_actual` and `refusal_reason_shown` so transparent/opaque mode flips do not lose forensics.

## 7. What is intentionally not specified here (MVP)

- Prompt template content → `24-prompt-registry.md`
- Eval methodology + golden set format → `23-evals-guardrails.md`
- Memory / context window mgmt details → `22-memory-context.md`
- Tool specifications → `21-tools-and-mcp.md` (sparse in MVP — only `sub_query_retrieve` in V2)

## 8. Open questions for Stage 5 review (architecture-reviewer)

| Q | Topic |
|---|---|
| Is the no-agent-loop MVP defensible against a vendor who asks "but can it reason?" | T1 Product-System Fit, T8 AI Agent Production Readiness |
| Is the 3-iteration ReAct cap evidenced? | T8 |
| Is the conversation-history-server-reconstructed rule sufficient under prompt injection? | T4 Security |
| Does refusal-as-typed-200 give vendors the integration shape they expect? | T1 |

These will be answered in Stage 5 memos.
