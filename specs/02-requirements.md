# 02 — Requirements (seeded outline)

> Stage 2 seed: REQ-### identifiers, one-line statement, one-line acceptance criterion each.
> Stage 7 (`spec-writer`) deepens each into full acceptance criteria and links to architecture, test plan, build plan.
> Each REQ traces to a value-prop differentiator (§4 of `01-product-brief.md`) or a non-functional constraint.

Status legend: **MVP** = ship in MVP; **V2+** = roadmap; **NFR** = non-functional, applies to MVP.

## Functional requirements

| ID | Status | Statement | Acceptance seed | Traces to |
|---|---|---|---|---|
| **REQ-001** | MVP | The system shall accept document uploads via API in supported formats (PDF text-extractable, Word .docx, Markdown, plain text) | Upload returns a document ID and a parseable processing status within 1 second; rejected formats return 415 with the supported list | Diff 1 (on-prem ingest) |
| **REQ-002** | MVP | The system shall parse, chunk, embed, and index uploaded documents into a vector store | A 100-page born-digital PDF reaches "indexed" status in ≤ 60 s on reference hardware; failure modes emit structured errors with retry guidance | Diff 1 |
| **REQ-003** | MVP | The system shall perform hybrid retrieval (dense + sparse + rerank) over the indexed corpus, with multilingual baseline | Mixed Chinese/English query returns top-K reranked chunks; reranking measurably improves NDCG over dense-only on the golden set | DEC-014 |
| **REQ-004** | MVP | The system shall generate natural-language answers with inline citations linking to source chunks | Every assertion-bearing sentence in the answer carries at least one citation token; citation tokens resolve to specific chunk IDs in this turn's retrieval set | Diff 3 |
| **REQ-005** | MVP | The system shall perform runtime citation verification before delivering an answer | Every emitted citation is verified to (a) reference a chunk in this turn's retrieval set (mechanical), and (b) pass an NLI entailment check against that chunk; verification failures cause refusal or stripped citation per policy | Diff 3 |
| **REQ-006** | MVP | The system shall refuse to answer when grounding confidence is below configured threshold | Below-threshold queries receive an explicit refusal response (no fabricated answer); refusal threshold is admin-configurable; refusal events are logged | Diff 4 |
| **REQ-007** | MVP | The system shall persist an append-only audit record for every query | Each record contains: query, timestamp, user/session ID, retrieved chunk IDs, answer text, citations, verification results, refusal flag, latency. Records are immutable after write | Diff 5 |
| **REQ-008** | MVP | The system shall expose a stable HTTP API for vendor integrators | OpenAPI 3.x spec published; semantic versioning; integration test suite exercises every documented endpoint | Diff 2 |
| **REQ-009** | MVP | The system shall ship an embeddable chat widget (iframe) deployable into a host vendor UI | Widget loads from system origin via iframe tag; host can pass theme tokens (color, font) via URL params; widget never reads cross-origin host state | Diff 2, §8 trend research |
| **REQ-010** | MVP | The system shall provide admin APIs for document lifecycle: upload, list, delete, per-document ACL | Delete is soft (configurable retention); ACL is a flat tag set in MVP (V2: group-based); list supports pagination | Diff 5 |
| **REQ-011** | MVP | The system shall ship as a single-host installable artifact (docker-compose) | `docker compose up` plus a documented config file brings the system from cold to a working `/ready` endpoint in ≤ 30 minutes on reference hardware | DEC-008 (demo) |
| **REQ-012** | MVP | The system shall be runnable in air-gapped mode | With egress blocked at the OS network namespace, MVP eval suite passes 100%; no required outbound calls; optional cloud-LLM adapters disabled by default | DEC-003 |
| **REQ-013** | MVP | The system shall ship an offline eval harness using RAGAS metrics | `cli eval run --suite golden` produces a report with faithfulness, answer relevancy, context precision, context recall; pass/fail per §9.1 thresholds | DEC-017 |
| **REQ-014** | MVP | The system shall ship with a sample CCM-style corpus and golden Q&A set | A 50-question hand-curated golden set is included; first-run `eval` produces a baseline report; documented as "the smoke test for new installs" | RISK-009 |
| REQ-015 | V2 | The system shall support multi-step ReAct-style agent reasoning over the same retrieval primitives | Agent decomposes a multi-part question into sub-queries; final answer carries citations from each sub-query; degrades to single-step when single-step recall is sufficient | (V2-α) |
| REQ-016 | V2 | The system shall surface a review queue for routed categories | Admin defines category routing rules; matching answers pause for reviewer action (approve / edit / reject); reviewer verdict captured | (V2-α) |
| REQ-017 | V2 | The system shall support pluggable document connectors (SharePoint, file share, generic REST) | Connector framework documented; at least one reference connector ships | (V2-γ) |
| REQ-018 | V2 | The system shall provide a JS widget (non-iframe) for deeper vendor theming | Widget renders in host DOM; host CSS cascades; sandbox isolation preserved at API layer | (V2-β) |
| **REQ-019** | **V2** | The system shall render each citation as a highlighted span inside its source chunk and a clipped page snapshot for PDF sources | Click a citation → modal opens the source chunk with the cited span highlighted; for PDF sources, a page-region image is shown | DEC-022, brief §7 V2-citation-deep |
| **REQ-020** | **V2** | The system shall decompose an answer into atomic claims and verify each claim independently | Each claim carries its own NLI check + citation; failed-claim spans are visually downgraded (greyed) while passing claims render normally | DEC-022, brief §7 V2-citation-deep |
| **REQ-021** | **V2** | The system shall support document lifecycle states (`authoritative` / `draft` / `deprecated`) and surface potential contradictions | Admin can flip state via API or admin console; `authoritative` boosts retrieval ranking; the system flags document pairs whose contents conflict on the same query | DEC-022, brief §7 V2-governance-deep |
| **REQ-022** | **V2** | The system shall ship a per-customer prompt template registry with versioning | Customer admin saves system prompt, refusal phrasing, citation format; templates are immutable on version pin; rollback supported | DEC-022, brief §7 V2-governance-deep |
| **REQ-023** | **V2** | The system shall allow admins to curate a customer-specific golden Q/A set and run RAGAS against it | Admin UI for adding/editing/deleting Q/A pairs; CLI runs the customer set as a regression gate; deltas vs prior run reported | DEC-022, brief §7 V2-tuning-deep |
| **REQ-024** | **V2** | The system shall support A/B traffic split across prompts or model adapters | Admin defines a split (e.g., 50/50); per-arm RAGAS metrics over a sampling window are reported; admin promotes the winner | DEC-022, brief §7 V2-tuning-deep |
| **REQ-033** | **V2** | The system shall implement a model adapter abstraction so swapping generation model (Qwen3 → Qwen4 / DeepSeek / commercial API) requires only a config change with no service restart | Switching adapter via admin API takes effect for new turns within ≤ 10 seconds; pre- and post-switch RAGAS reports run against the same golden set produce comparable structured deltas | DEC-028 LCC enabler |
| **REQ-034** | **V2** | The system shall version embedding model identity and support single-host blue/green corpus re-embedding | Each chunk persists `embedding_model@version`; bumping the embedding model spawns a re-embedding job into a shadow collection; admin triggers cutover; queries during re-embedding go to the old collection; rollback returns to old collection within ≤ 60 seconds | DEC-028 LCC Tier 3 enabler |
| **REQ-035** | **V2** | Every audit record (REQ-007) shall carry a "context fingerprint": model adapter + model version + embedding model version + reranker version + prompt template version active at answer time | An auditor selecting any historical answer can reconstruct exactly which stack components produced it; fingerprint fields are mandatory and non-null | DEC-028 LCC forensics |
| REQ-025 | V3 | The system shall ship as React / Vue component SDKs for embedding | Vendor adds `<GroundedDocsChat />` to a React app; CSS isolation guaranteed; identical API surface to widget | (V3) |
| REQ-026 | V3 | The system shall support multi-host deployment via Helm chart with blue/green reindex | Helm install on a Kubernetes cluster; reindex pipeline runs against shadow collection with cutover trigger | (V3) |
| REQ-027 | V3 | The system shall integrate TruLens for production observability + drift monitoring | Live trace per query; drift detection on RAGAS metrics over a configurable window | DEC-016 V3 step |
| REQ-028 | V3 | The system shall support OCR + complex table extraction during ingest | Scanned-PDF page becomes searchable text; tables in contracts emit cell-structured chunks | (V3) |
| REQ-029 | V3 | The system shall ship a compliance audit prep package for the first regulated buyer's standard (SOC2 / HIPAA / MLPS L3) | Audit-mode export of audit log; documentation matrix mapping controls to system features | Triggered by first regulated buyer |
| **REQ-030** | **V3** | The system shall support customer-corpus LoRA fine-tuning of **both reranker and generator** (two independent adapters, trained separately) | Each training job runs on customer hardware in ≤ 24 h on reference rig; emits adapter weights; per-customer adapter swap at serving time (REQ-033 abstraction) | DEC-023, DEC-030 |
| **REQ-031** | **V3** | The system shall expose a corpus-health dashboard for admin | Dashboard shows: stale-document candidates, contradicting-pair candidates, low-citation-coverage documents, top high-refusal query clusters | DEC-022 (sticky support deliverable) |
| **REQ-032** | **V3** | The system shall ship a tuning playbook as a versioned product artifact | Playbook is markdown + executable scripts; "5 steps after first install" covers golden-set seeding, threshold calibration, prompt-template seed, A/B baseline, first weekly review | DEC-022 |

## Non-functional requirements (NFR-### — MVP)

| ID | Statement | Acceptance seed |
|---|---|---|
| **NFR-001** | The system shall run end-to-end on a single workstation with one consumer/workstation-class GPU (≥ 24 GB VRAM) | Reference hardware spec documented; eval suite passes within latency budget on that spec |
| **NFR-002** | Make no required outbound network calls at runtime | Air-gap test (REQ-012) passes |
| **NFR-003** | Support Chinese and English baseline; design must not block additional languages | Mixed-language golden set passes MVP thresholds for both languages |
| **NFR-004** | Citation-hit-rate (every emitted citation lands in current retrieval set) shall be 100% | Hard gate; verified by REQ-005 mechanical check |
| **NFR-005** | Query latency p95 ≤ 8 s on reference hardware | Measured in eval harness latency suite |
| **NFR-006** | Ingest throughput ≥ 100 pages/min on reference hardware | Measured in eval harness ingest suite |
| **NFR-007** | All durable state survives container restart | Persist DB + vector store on host volume; documented backup procedure |
| **NFR-008** | The system shall not log query content or document content at INFO level by default | Sensitive payload at DEBUG only; INFO logs contain IDs, status, latency, sizes |
| **NFR-009** | The HTTP API surface shall declare auth on every endpoint | Default: bearer token; integrations document AuthN/AuthZ hand-off |
| **NFR-010** | The system shall expose a configurable refusal threshold (REQ-006) via admin config | Threshold change takes effect without restart |
| **NFR-011** | The MVP shall ship a `dev profile` documenting cloud-GPU rental settings (RunPod / Vast.ai recommended images, ports, volumes, model cache layout) | A new contributor following only the dev profile reaches a working eval run in ≤ 2 hours; profile validated by user (DEC-021) |

## Traceability Quick Map (will deepen at Stage 7)

| Value-prop differentiator (§4 of brief) | Requirements |
|---|---|
| On-prem deployment | REQ-011, REQ-012, NFR-001, NFR-002, NFR-007 |
| Vendor-embeddable | REQ-008, REQ-009 |
| Verified citation | REQ-004, REQ-005, NFR-004 |
| Refusal as a product feature | REQ-006, NFR-010 |
| Audit-ready | REQ-007, REQ-010, NFR-008 |
| Eval / RAGAS thresholds | REQ-013, REQ-014, NFR-005, NFR-006 |
| Multilingual baseline | REQ-003, NFR-003 |

## Out of MVP (named, traced to Non-Goals §6 of brief)

- ReAct agent → REQ-015 (V2)
- Review queue → REQ-016 (V2)
- Connectors → REQ-017 (V2)
- JS widget → REQ-018 (V2)
- SDK, Helm, HA, blue/green, OCR, certs, IM channels — see §6 / §7 of brief
