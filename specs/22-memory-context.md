# 22 — Memory and Context

> Stage 7 (`spec-writer`) deliverable. Documents GroundedDocs's conversation memory model. Cross-references `20-agent-behavior.md` §2.4 (the authoritative behavior spec) and `05-data-model.md` (the `audit_events`-derived storage) rather than re-deriving them — this file's job is to state the memory-specific policy (what may/must never be stored, retention, retrieval, compaction, user visibility) in one place, per the `21-tools-and-mcp.md`-adjacent AI-agent slot convention.

## Plain-English Summary

GroundedDocs has exactly one kind of memory: the last few turns of a conversation, reconstructed server-side from the audit trail every time. There is no long-term user profile, no cross-conversation memory, no client-trusted history. This narrowness is deliberate — it closes an entire class of prompt-injection attack (a client claiming a fabricated prior turn happened) and keeps the citation-verification guarantee scoped to what the system actually retrieved this turn, not some blended memory of prior turns.

## Memory Types

GroundedDocs implements exactly one memory type in MVP:

| Memory type | Present in MVP? | Description |
|---|---|---|
| **Short-term conversation memory** | Yes | Last N=5 turns of the current `conversation_id`, reconstructed server-side from `audit_events` on every turn (`20-agent-behavior.md` §2.4) |
| Long-term user memory / profile | No | Not implemented; no per-user preference store, no cross-conversation summarization |
| Semantic/episodic memory beyond the document corpus | No | The document corpus itself (via `retrieve/`) is the system's only long-term "knowledge," and it is not memory in the agent sense — it's the product's retrieval index |
| Tool-call memory | No | MVP has no tool surface (DEC-039); N/A |
| Cross-conversation memory | No | Each `conversation_id` is independent; no session links across conversations |

**V2 scope note**: none of the roadmap items (ReAct sub-query state, REQ-020 claim-decomposition feedback loop) introduce a new memory *type* — they extend the existing turn-scoped `QueryGraphState` (`04-architecture.md` §5.1.1) within a single turn, which is graph execution state, not persisted cross-turn memory. `failed_claims` and `revision_count` are explicitly cleared at the entry of a new turn (§5.1.1's reducer semantics) — they do not leak into conversation memory.

## What May Be Stored

- `conversation_id` (opaque identifier, not content) — safe at `INFO` log level (NFR-008)
- The last N=5 turns' `audit_events` rows for a given `conversation_id`, read back to reconstruct context for the current turn — this includes prior queries, prior answers, and prior citations, all already governed by `audit_events`'s own privacy classification and retention rule (`05-data-model.md`)
- Nothing beyond what `audit_events` already stores — conversation memory is a **read pattern** against the audit table, not a separate storage mechanism with its own retention or privacy rules to define

## What Must Never Be Stored (as Memory)

- **Client-supplied conversation history is never stored, never read, never trusted** — the `POST /v1/query` request schema (`06-api-contracts.md`) has no field for prior messages; only `query` and `conversation_id` are accepted. A client attempting to pass a fabricated `history` array is silently ignored, not merely distrusted (verified by the contract test in `06-api-contracts.md`: "Client-history rejection")
- No cross-user memory — one user's conversation never influences another user's turn, even within the same document corpus
- No memory of ACL decisions beyond the existing ACL cache TTL discipline (`04-architecture.md` §7B.5) — a user's *access* is re-evaluated per query (Layer 2 JIT), never cached as a standing "memory" of what they were once allowed to see

## Retention Policy

Conversation memory has **no retention policy independent of `audit_events`'s** (DEC-070: append-only, immutable, multi-year per customer compliance policy) — because it is not separately stored. The practical "how far back does memory reach" question is answered by the **N=5 turn window** (a query-time limit, not a storage-time limit): even though `audit_events` retains every turn forever, only the last 5 are read back into the current turn's context.

- **N=5 is admin-configurable** (`20-agent-behavior.md` §2.4)
- Increasing N does not require a schema change — it changes the `LIMIT` on the same `audit_events` query (`07-database.md`'s `(conversation_id, timestamp DESC)` index already supports any N)

## Retrieval Policy

Server-side reconstruction, every turn, no exception:

1. On `POST /v1/query` with a given `conversation_id`, `api/` queries `audit_events` for the last N=5 rows matching that `conversation_id`, ordered by `timestamp DESC`
2. These rows are assembled into the graph's prompt-construction context (the exact prompt-assembly mechanics are `20-agent-behavior.md`'s and `24-prompt-registry.md`'s concern, not this file's)
3. If no `conversation_id` is supplied, or the supplied ID has no matching rows, the turn proceeds with empty prior context — treated as the start of a new conversation, not an error

**No semantic retrieval over conversation history** — this is a recency-window read, not a similarity search. GroundedDocs's one retrieval mechanism (`retrieve/`, hybrid dense+sparse over the document corpus) is not applied to conversation history; the two are architecturally and conceptually distinct systems that happen to both be called "retrieval" in different contexts. This file exists partly to make that distinction explicit and prevent future confusion between "retrieving documents" and "retrieving conversation turns."

## Compaction Policy

**None in MVP.** The last-N-turns window is itself the compaction strategy — rather than summarizing or compressing older turns, the system simply stops reading them once N is exceeded. This is a deliberate simplicity choice: a summarization step would be a new LLM call on the hot path (latency cost against NFR-005) and a new potential hallucination surface (a bad summary of turn 1 could corrupt turn 6's context) — neither is justified at N=5's small window size.

**V2/V3 consideration** (not committed, named for completeness): if N is ever raised substantially (e.g. for a long-running compliance-review conversation), a compaction strategy would need designing at that point — this is explicitly out of scope for MVP and not addressed further here, consistent with `01-product-brief.md`'s non-goals discipline (name deferred scope, don't half-design it).

## User Visibility and Deletion Controls

- **Visibility**: an end user can see their own conversation's prior turns implicitly, via the widget's own conversation UI state (client-side rendering of what was already returned to them) — GroundedDocs does not need a separate "view my conversation history" API, since the widget already holds what it rendered
- **Admin visibility**: `GET /v1/admin/audit` (`06-api-contracts.md`), filtered by `conversation_id` or `user_id`, surfaces the full turn history to an admin — this is the same audit-pull mechanism as any other compliance query, not a memory-specific endpoint
- **Deletion**: conversation memory has no independent deletion control — deleting "memory" would mean deleting `audit_events` rows, which is forbidden by DEC-070's append-only posture (GDPR erasure against `audit_events` is explicitly deferred to the first regulated AU/EU buyer engagement, per DEC-070 and `05-data-model.md`'s retention rules). There is no lighter-weight "forget this conversation but keep the audit trail" middle ground in MVP — the two are the same data

## Privacy Classification

Conversation memory inherits `audit_events`'s classification: **Confidential / Compliance-critical** (`05-data-model.md`). It carries no separate or lesser classification just because it's being read as "memory" rather than "audit history" — the same rows, the same sensitivity, two different read patterns.

## Conversation History Provenance

This is the section the AI-agent spec template requires explicitly, and it is the single most security-relevant fact in this file:

**History is server-reconstructed by default. Client-supplied history is unconditionally ignored — not "distrusted," not "validated then possibly rejected," ignored at the schema level.** There is no cryptographic-signature exception, no "explicitly justified" override path documented for MVP: the request schema simply has no field to carry client-supplied history in the first place (`06-api-contracts.md`). This is stronger than the AI-agent template's baseline expectation ("ignored unless cryptographically signed or explicitly justified") — GroundedDocs's rationale for not even offering a signed-history exception is that the value of such an exception (letting a trusted vendor-integrator client carry its own longer or differently-scoped history) does not outweigh the attack surface it would reopen (a compromised or misconfigured vendor integration becoming a fabricated-history injection vector) at MVP's risk tolerance. If a genuine V2 need for this emerges (e.g. a vendor wanting to seed a conversation with prior context from their own system, not GroundedDocs's), it would need a fresh product-scope decision — not one this file makes unilaterally.

## Evaluation Cases for Memory Correctness

| Test | What it verifies |
|---|---|
| N-turn window respected | Seed a conversation with N+2 turns; verify the (N+1)th and (N+2)th turns' context excludes the earliest 2 turns |
| Client-history rejection (cross-reference `06-api-contracts.md`'s existing contract test) | A request with a fabricated `history` field has zero influence on the reconstructed context — verified by checking the actual prompt sent to `generate/`, not just the response |
| Cross-conversation isolation | Two different `conversation_id`s with overlapping turn timestamps never leak context into each other |
| Cross-user isolation | Two different `user_id`s, even if (hypothetically) sharing a `conversation_id` through a client bug, must not have their turns blended — `conversation_id` alone is not treated as sufficient authorization; the underlying ACL/session validation on every turn still applies independently |
| Empty/unknown `conversation_id` handling | A never-before-seen `conversation_id` produces empty prior context, not an error |
| Legal-hold interaction (cross-reference `04-architecture.md` §7B.6, DEC-091) | A conversation whose reconstructed context references a document that is later placed under legal hold has its KV-cache invalidated on the next relevant event — this is not a memory-correctness bug per se, but a memory *provenance* concern this file should name: the reconstructed context can go stale mid-conversation in exactly this one documented way, and the system's remediation (cache invalidation, not memory deletion) is intentional |

## Dependencies

- `20-agent-behavior.md` §2.4 (authoritative conversation-memory behavior spec — this file does not restate its mechanics, only its policy framing)
- `04-architecture.md` §5.1.1 (`QueryGraphState` — the in-turn execution state, distinct from cross-turn memory), §7B.6 (legal-hold KV-cache interaction)
- `05-data-model.md` (`audit_events` entity — the actual storage conversation memory reads from)
- `06-api-contracts.md` (`POST /v1/query` request schema — the enforcement point for "client history is never accepted")
- `24-prompt-registry.md` (this phase — how reconstructed history is assembled into the actual prompt)

## Decision References

DEC-039, DEC-042, DEC-045, DEC-070, DEC-091
