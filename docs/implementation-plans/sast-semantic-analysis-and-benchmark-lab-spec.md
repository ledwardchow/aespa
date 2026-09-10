# SAST Semantic Analysis and Benchmark Lab — Implementation Specification

**Status:** Proposed for review  
**Date:** 2026-09-10  
**Scope:** Improve AESPA SAST recall, precision, coverage assurance, and efficiency through a source-backed repository model, threat analysis, semantic work planning, complementary discovery, candidate reconciliation, and semantic closure. Add an optional Benchmark Lab that evaluates ordinary completed SAST runs against externally stored ground truth without creating a second scan engine.

## 1. Executive summary

AESPA's SAST engine currently builds a deterministic regex-derived atlas, creates input- and sink-oriented work items, dispatches bounded discovery workers, validates each candidate independently, and records attack paths. This gives the system auditable execution and strong sink coverage, but makes initial pattern recognition an overly powerful gate. Security questions that do not begin at a recognized input or sink can receive no meaningful review, and completing every generated work item can overstate semantic coverage.

This specification changes the pipeline to:

```text
source snapshot
  -> repository model
  -> source-backed threat model
  -> semantic coverage obligations
  -> independent baseline + focused discovery + deterministic passes
  -> candidate reconciliation and deduplication
  -> independent validation
  -> semantic gap closure
  -> attack paths and report
```

The design is framework-neutral. Language- and framework-specific parsers populate a shared semantic representation; vulnerability reasoning operates on that representation rather than on framework-specific route regexes.

Benchmarking is kept out of the scan path. A benchmark evaluation attaches external ground truth to an already completed normal `SastRun`, compares expected vulnerabilities with reportable and non-reportable candidates, and stores the evaluation separately. The Benchmark Lab is a testing feature, hidden by default, and enabled through System Settings in the same style as Reporting Lab.

## 2. Product decisions

1. **Normal SAST runs remain the sole execution mechanism.** Benchmark Lab does not fork, wrap, or replace `start_sast_scan()`.
2. **Ground truth is never supplied to a scanner phase.** It becomes accessible only to the post-run evaluator after a run is terminal.
3. **Threat analysis is operational scan state.** It must produce source-backed scenarios and coverage obligations, not only prose.
4. **Regexes remain useful signals, not completeness gates.** They supplement parser and LLM-assisted repository mapping.
5. **Coverage is semantic.** File reads and closed pattern matches remain telemetry, but do not establish that a security objective was assessed.
6. **Discovery strategies remain complementary.** Preserve AESPA's sink-first review while adding independent and threat-directed review.
7. **Validation remains adversarial.** Candidate validators do not silently turn adjacent observations into confirmed findings; adjacent concerns return to a discovery or closure queue.
8. **Benchmark Lab is hidden by default.** A persisted `panel_enabled = false` setting controls the sidebar entry under `Testing Features`.

## 3. Goals

- Improve discovery of authorization, business-logic, missing-control, sensitive-output, deployment, and dependency issues.
- Retain or improve injection and client-side sink recall.
- Make scanner coverage explainable in terms of assets, boundaries, invariants, and operations.
- Reduce repeated source reads, low-value LLM calls, and duplicate candidate validation.
- Support unknown languages and custom frameworks through graceful reconciliation rather than silent undercoverage.
- Make scanner changes measurable with blind, repeatable post-run evaluation.
- Preserve pause, resume, source-path jailing, evidence receipts, exports, and dynamic lead handoff.

## 4. Non-goals

- Building a whole-program compiler or exact interprocedural taint engine for every language.
- Treating generated threat scenarios as confirmed vulnerabilities.
- Requiring runtime reproduction before a SAST lead can be reportable.
- Automatically importing benchmark findings into web or API runs.
- Making benchmark evaluation part of ordinary customer scan completion.
- Optimizing specifically for one fixture, language, framework, or ground-truth document format.

## 5. Current architecture and limitations

Relevant implementation points:

- `services/sast_workprogram.py` inventories files and creates regex-derived `SastSurfaceItem`, `SastPartition`, `SastWorker`, and `SastWorkItem` rows.
- `services/sast_scanner.py` runs scope, discovery, validation, attack-path, and report phases.
- `services/prompts/sast.py` directs discovery workers to resolve assigned items and directs validators to review exactly one candidate.
- `services/component_facts.py` already extracts compact routes, calls, auth boundaries, queues, datastores, and framework facts, but currently runs after the SAST report.
- `SastWorkItem` supports `work_type` values centered on input and sink obligations and stores one scalar `lead_id`.

The principal limitations are:

- Failure to recognize a framework construct can remove an entire class of investigation anchors.
- Line-oriented pattern matches do not express components, identities, assets, call edges, state transitions, or data-release boundaries adequately.
- Workers are rewarded for closing assigned items rather than resolving the repository's material security questions.
- Missing controls often have no syntactic sink and therefore no owner.
- One work item can reveal multiple vulnerabilities but can retain only one lead relationship.
- Per-candidate validation happens before global root-cause consolidation.
- No post-validation phase can create candidates for material gaps.

## 6. Target SAST phase model

Persist these phases in `SastRun.phase_state_json`, adding new keys without breaking older run rendering:

| Phase | Purpose | May create candidates? |
|---|---|---:|
| `scope` | Extract, classify, hash, and inventory the immutable source snapshot | No |
| `repository_model` | Build normalized architecture and security-relevant facts | No |
| `threat_model` | Identify assets, actors, boundaries, objectives, assumptions, and threat scenarios | No |
| `planning` | Convert facts and scenarios into semantic coverage obligations and worker packets | No |
| `discovery` | Run baseline, focused, deterministic, and sink-first discovery | Yes |
| `reconciliation` | Merge duplicates, split conflated issues, and prioritize unique hypotheses | No new security claims; may split or merge |
| `validation` | Adversarially confirm, dismiss, or defer unique candidates | No; may raise adjacent concerns |
| `closure` | Reconcile uncovered scenarios, surfaces, sibling operations, and adjacent concerns | Yes |
| `attack_path` | Establish external reachability, capability gain, impact, and dynamic objective | No |
| `report` | Persist final leads, coverage assurance, telemetry, and report projection | No |

Older runs lacking the new phases remain readable. Resume must restart only an incomplete phase and reuse immutable completed phase artifacts.

## 7. Repository model

### 7.1 Normalized representation

Create a framework-neutral graph containing:

- **Components:** applications, services, modules, workers, clients, libraries, build or deployment units.
- **Operations:** routes, RPC methods, queue consumers, jobs, CLI commands, file importers, callbacks, UI actions, and exported library methods.
- **Actors and identities:** anonymous users, authenticated identities, roles, tenants, services, operators, and external systems.
- **Assets:** credentials, secrets, PII, financial records, authorization state, files, source code, audit records, and integrity-critical state.
- **Inputs and outputs:** request fields, messages, files, environment or configuration values, serialized responses, logs, exports, and rendered content.
- **Sensitive operations:** queries, interpreters, process execution, network access, filesystem access, deserialization, cryptography, authentication decisions, authorization decisions, and state mutation.
- **Controls:** authentication, authorization, ownership, validation, encoding, sanitization, transaction boundaries, throttling, approval, audit, and isolation controls.
- **Edges:** calls, reads, writes, emits, receives, authenticates, authorizes, renders, redirects, imports, exports, and transforms.
- **Dependencies and deployment facts:** package versions, externally loaded assets, runtime modes, container or process privileges, listener exposure, and configuration precedence.

Every fact must carry:

- a stable fingerprint;
- a provenance value such as `parser`, `manifest`, `pattern`, `llm_reconciliation`, or `user_context`;
- confidence;
- one or more `path:line` evidence anchors when source-established;
- an optional unresolved or contradictory status.

### 7.2 Extraction layers

Run these layers in order:

1. **Inventory and manifests:** languages, dependency manifests, lockfiles, frameworks, runtime and deployment files.
2. **Parser adapters:** AST or tree-sitter extractors for supported language families.
3. **Compact deterministic facts:** refactor and reuse `component_facts.py` before discovery.
4. **Pattern fallback:** retain high-signal generic patterns for constructs not yet parsed.
5. **LLM reconciliation:** inspect representative files and resolve missing entrypoints, component roles, controls, and ambiguous call relationships.

Parser adapters must emit the normalized representation. They must not contain benchmark-specific vulnerability rules.

### 7.3 Completeness heuristics

Create repository-model warnings when facts disagree with the source inventory, including:

- server or server framework with no externally reachable operations;
- client framework with no user actions, output surfaces, or outbound calls;
- datastore dependency with no reads or mutations;
- authentication dependency with no identity or session boundaries;
- queue dependency with no producers or consumers;
- production source count materially larger than mapped component coverage;
- model caps or truncation reached;
- unresolved framework or generated-code ownership.

Warnings create reconciliation obligations. A high-risk unresolved warning prevents `completion_status = full`.

### 7.4 Proposed storage

Evolve `SastSurfaceItem` into the canonical fact node where practical:

- extend `kind` to support `component`, `operation`, `actor`, `identity`, `asset`, `input`, `output`, `sink`, `control`, `store`, `dependency`, `deployment`, and `unknown`;
- add `confidence`, `review_status`, and optional `component_key` fields;
- retain `details_json` for type-specific bounded properties.

Add `SastSurfaceEdge`:

```text
id
sast_run_id
source_surface_id
target_surface_id
edge_kind
confidence
provenance
evidence_json
fingerprint
created_at
```

Do not overload campaign-level `ComponentConnection` for all repository graph edges. Campaign connections and per-run semantic edges have different lifecycles and cardinality.

## 8. Threat analysis

### 8.1 Purpose

Threat analysis determines what security properties matter for the actual repository. It does not assert vulnerabilities. Its output guides prioritization and creates auditable questions for discovery and closure.

### 8.2 Canonical threat model

Persist one versioned `SastThreatModel` per source snapshot and scan configuration with these fields:

```text
summary
assets[]
trust_boundaries[]
attacker_capabilities[]
security_objectives[]
assumptions[]
open_questions[]
model_version
source_snapshot_digest
prompt_version
created_at
```

Each asset, boundary, objective, and assumption carries evidence references or an explicit origin such as user-provided context. Secret values must never be copied; record only the secret's role, storage reference, recipients, and enforcing control.

### 8.3 Threat scenarios

Persist `SastThreatScenario` rows with:

```text
id
sast_run_id
scenario_key
title
actor
controlled_input_or_state
entry_surface_ids[]
boundary_surface_ids[]
asset_surface_ids[]
expected_control_surface_ids[]
sensitive_operation_surface_ids[]
security_objective
capability_gain
impact
prerequisites[]
evidence_json
priority
confidence
status
created_at / updated_at
```

Scenario status is `planned`, `in_review`, `resolved`, `deferred`, `not_applicable`, or `unreviewed`. Scenario priority uses reachability, plausible capability gain, asset importance, and evidence confidence.

### 8.4 Threat-model worker contract

The worker receives the normalized repository model, representative evidence, applicable policy, and optional user context. It must:

- identify realistic actors without granting them capabilities they do not have;
- identify assets and enforceable invariants;
- describe boundary crossings and expected controls;
- separate source-established facts, deployment assumptions, and open questions;
- emit structured scenarios through tools rather than only prose;
- avoid producing vulnerability findings.

Threat scenarios must remain bounded. Prefer material architecture boundaries over generating every possible STRIDE or OWASP combination.

### 8.5 Independent baseline isolation

The independent baseline discovery worker sees the repository model and applicable security policy but not the generated threat scenarios. This reduces anchoring and provides an independent source of recall. Focused workers receive selected scenarios.

## 9. Semantic coverage obligations

### 9.1 Obligation model

Expand `SastWorkItem` into a general obligation, or introduce `SastCoverageObligation` if preserving the existing table simplifies migration.

Required fields:

```text
obligation_key
obligation_type
title
security_question
priority
source_scenario_id nullable
primary_surface_ids[]
related_surface_ids[]
required_evidence[]
assigned_worker_id nullable
status
disposition
reasoning
evidence_json
controls_json
open_questions_json
created_at / updated_at
```

Statuses are `pending`, `in_progress`, `finding`, `safe`, `not_applicable`, `deferred`, `blocked`, and `superseded`.

### 9.2 Obligation families

- identity and authentication invariants;
- authorization, ownership, role, and tenant isolation;
- source-to-sink interpretation flows;
- sink-to-source backward tracing;
- sensitive output, export, logging, and browser persistence;
- business and state-transition invariants;
- sibling-operation consistency;
- missing controls and abuse resistance;
- parser, deserialization, file, network, and process boundaries;
- cryptographic and secret lifecycle;
- configuration and deployment safety;
- dependency and third-party asset exposure;
- monitoring and auditability, classified according to scan policy.

### 9.3 Worker packets

Partition obligations by coherent component, operation family, trust boundary, or security domain. Do not split a single call path merely to meet a fixed item count.

Worker instructions change from “review only the assigned items” to:

- resolve every assigned obligation;
- inspect callers, callees, siblings, shared controls, and materially related operations;
- create all distinct candidates found on the reviewed trace;
- create a secondary candidate when evidence establishes a separate root cause;
- create an adjacent concern when evidence is insufficient but merits closure review;
- record newly discovered repository facts and relationships;
- do not stop after finding the first issue.

Use token and time budgets to bound work, not artificial semantic isolation.

## 10. Discovery ensemble

Run these sources of discovery:

1. **Independent baseline auditor:** an open-ended repository security review, independent of generated scenarios.
2. **Threat-directed workers:** investigate prioritized scenarios and invariants.
3. **Deterministic analyzers:** high-confidence checks for dependency versions, credentials, insecure defaults, dangerous APIs, and configuration.
4. **Sink-first workers:** retain backward tracing from sensitive operations and browser output sinks.
5. **Coverage reconciliation workers:** investigate repository-model warnings and unresolved semantic facts.

All discovery paths write to one candidate ledger using a stable candidate schema. Candidate provenance records which strategy or obligation produced it.

## 11. Candidate relationships and reconciliation

### 11.1 Many-to-many linkage

Replace the effective one-work-item-to-one-lead relationship with `SastObligationLead`:

```text
obligation_id
lead_id
relationship  # primary | supporting | adjacent | duplicate
created_at
```

Keep `SastWorkItem.lead_id` readable during migration, then remove or deprecate it after old exports and APIs no longer depend on it.

### 11.2 Pre-validation reconciliation

Before creating validator tasks:

- normalize category and affected operation;
- cluster by root control failure, source-to-sink path, asset, remediation, and affected authority;
- merge duplicate instances while retaining every location and evidence item;
- split candidates that contain independently remediable root causes;
- retain provenance from all contributing workers;
- assign stable candidate IDs only after reconciliation.

Do not merge merely because titles or CWEs match.

### 11.3 Validation behavior

Validate each reconciled candidate once. The validator retains the disprove-it mandate and returns `confirmed`, `dismissed`, or `inconclusive` with counterevidence and proof gaps.

Add `record_adjacent_concern` to the validator tool set. It may create a bounded closure-queue item but may not confirm another finding. This preserves independence while preventing material observations from being discarded.

### 11.4 Post-validation reconciliation

Run a small deterministic and, when necessary, LLM-assisted pass to:

- merge duplicates surviving validation;
- ensure distinct root causes were not conflated;
- reconcile severity with actual capability gain and prerequisites;
- preserve dismissed and inconclusive evidence for coverage reporting.

## 12. Semantic closure

Closure receives:

- final repository model and warnings;
- threat scenarios;
- obligations and dispositions;
- confirmed, dismissed, and inconclusive candidates;
- adjacent concerns;
- file and evidence receipts.

It must account for every high-priority scenario and material boundary with one of:

- a reportable lead;
- a source-backed safe disposition;
- a source-backed not-applicable disposition;
- a deferred disposition with a specific proof gap;
- an explicit unreviewed status that makes coverage partial.

Closure can create new candidates. New candidates must pass the same reconciliation and independent validation contracts before becoming reportable.

Completion is `full` only when:

- all required workers completed;
- no high-priority obligation is pending, blocked, or unreviewed;
- all repository-model completeness warnings are resolved or explicitly accepted as low-risk unknowns;
- every reportable candidate was validated and received attack-path analysis;
- deterministic analyzer failures and caps are disclosed;
- the source atlas and semantic model were not silently truncated.

## 13. Deterministic dependency analysis

Add a separate software-composition pass that:

- extracts direct and resolved versions from manifests and lockfiles;
- recognizes versions embedded in vendored filenames, headers, source maps, and remote asset URLs;
- distinguishes runtime, development, optional, and bundled dependencies;
- matches versions against an offline advisory database with its update timestamp recorded;
- emits deterministic evidence and confidence;
- avoids treating an unverified product-name match as a vulnerable dependency.

The general SAST model consumes dependency facts and can reason about reachability and deployment prerequisites, but version-to-advisory matching should not rely primarily on an LLM.

## 14. Scan policy changes

Move hardcoded exclusions into policy fields. At minimum provide policy control for:

- rate limiting and brute-force resistance;
- race conditions and concurrency invariants;
- audit logging and detection controls;
- defense-in-depth browser and deployment findings;
- vulnerable dependency reporting;
- minimum severity and confidence;
- maximum baseline, threat, closure, and validator budgets.

Reports distinguish:

- exploitable vulnerability;
- conditional vulnerability;
- defense-in-depth weakness;
- compliance or hardening gap.

## 15. Benchmark Lab product design

### 15.1 Feature visibility

Benchmark Lab is a testing feature and is hidden by default.

Add a singleton `BenchmarkLabConfig` modeled after `ReportingDebugConfig`:

```text
id = 1
panel_enabled = false
default_match_mode = "assisted"
default_repetitions = 1
updated_at
```

System Settings -> Feature Visibility gains a card immediately after Reporting Lab:

```text
Benchmark Lab

Evaluate completed SAST scans against separately stored ground truth. Ground
truth is never exposed to scanner agents.

[ ] Show Benchmark Lab in the sidebar
```

The toggle uses a backend-persisted setting and the same immediate-save interaction as Reporting Lab. Do not use browser-local storage for this feature.

When enabled, the existing `Testing Features` sidebar section displays:

```text
Testing Features
  Reporting Lab   # only when its own toggle is enabled
  Benchmark Lab   # only when benchmark panel_enabled is true
```

The section label appears when either feature is enabled, not only when Reporting Lab is enabled. The collapsed sidebar shows enabled icons without the section label.

The hidden state affects discoverability, not API authorization. AESPA remains localhost-only by design; nevertheless, evaluator endpoints must validate all state transitions and must never expose ground truth through ordinary SAST analysis APIs.

### 15.2 Ordinary scans remain unchanged

Benchmark Lab never creates a special scanner run type. Users run SAST normally and evaluate only terminal runs.

Initial UI flow:

1. Open Benchmark Lab.
2. Click `New Evaluation`.
3. Select one completed SAST run.
4. Upload or select a ground-truth dataset.
5. Review blindness and provenance checks.
6. Configure matching policy.
7. Run evaluation.

Later, a benchmark comparison can group several evaluated normal runs. It stores references to `SastRun` rows and does not execute them.

### 15.3 Routes and pages

Add routes:

```text
#/benchmark-lab
#/benchmark-lab/evaluations/new
#/benchmark-lab/evaluations/:id
#/benchmark-lab/comparisons/:id       # later slice
```

Frontend feature folder:

```text
frontend/src/features/benchmark-lab/
  BenchmarkLabPage.jsx
  BenchmarkEvaluationForm.jsx
  BenchmarkEvaluationDetail.jsx
  BenchmarkSummary.jsx
  GroundTruthMatrix.jsx
  MatchReviewPanel.jsx
  BenchmarkAuditPanel.jsx
  benchmarkLab.css
```

Add a small `Evaluated` badge and link to a completed SAST run only when an evaluation exists. Do not add ground-truth contents to `SastRunDetail` API payloads.

### 15.4 Evaluation setup

The form includes:

- completed SAST run selector;
- ground-truth dataset upload or saved dataset selector;
- dataset schema validation preview;
- match mode: deterministic only, assisted, or human-reviewed;
- severity tolerance;
- location tolerance;
- inclusion rules for conditional and hardening items;
- evaluation name and optional notes.

The form displays immutable run provenance before submission:

- source archive digest;
- scanner version and source revision when available;
- model profile snapshot and role models;
- reasoning settings;
- workflow or prompt versions;
- start/completion timestamps;
- token and request usage;
- completion assurance and partial-coverage reasons.

### 15.5 Ground-truth schema

Support a canonical JSON format first, with Markdown import as a parser feeding the same schema:

```json
{
  "schema_version": 1,
  "name": "Example corpus case",
  "source_digest": "sha256:...",
  "items": [
    {
      "external_id": "GT-001",
      "title": "Object ownership is not enforced",
      "description": "...",
      "category": "CWE-639",
      "severity": "high",
      "locations": [{"path": "src/example.py", "line": 42}],
      "root_cause": "...",
      "affected_operation": "...",
      "expected_evidence": ["..."],
      "classification": "exploitable"
    }
  ]
}
```

Do not require exact titles or CWEs. Root cause, affected operation, data or authority flow, and locations are stronger match features.

### 15.6 Blindness and contamination checks

Evaluation must distinguish `valid`, `warning`, and `contaminated` runs.

Checks include:

- ground truth was created or uploaded only after the selected scan completed, or was stored in evaluator-only storage throughout;
- the source archive digest matches the dataset's expected digest;
- no ground-truth file was present in the source archive;
- no source file closely matches the ground-truth item corpus or known answer-key filenames;
- no SAST evidence receipt accessed an evaluator-owned path;
- the run was not resumed with modified source;
- evaluator data was absent from all phase checkpoints and candidate prompts.

Filename and content-similarity checks are warnings unless a direct match is established. Direct access to ground truth or a full expected-results document marks the evaluation contaminated. Contaminated results remain inspectable but are excluded from aggregate scorecards by default.

Ground-truth storage must be outside the SAST extraction root and inaccessible through `_jail`, `list_files`, `glob`, `read_file`, and `grep`.

### 15.7 Matching pipeline

1. Normalize ground truth and scanner candidates.
2. Generate deterministic possible matches using path, operation, CWE/category, source/sink, and normalized root-cause tokens.
3. For assisted mode, give an evaluator LLM only the completed scanner output and ground truth—not source tools or scanner transcripts unless explicitly requested for adjudication.
4. Require one disposition per ground-truth item: `full`, `partial`, or `missed`.
5. Require one disposition per unmatched reportable finding: `additional_valid`, `false_positive`, `duplicate`, or `unreviewed`.
6. Store rationale, contributing lead IDs, confidence, and whether a human changed the decision.
7. Never rewrite the original `ScanLead` or `SastRun` rows.

Assisted matching is an evaluation convenience, not unquestioned truth. Low-confidence and many-to-many matches enter human review.

### 15.8 Evaluation metrics

Show:

- full recall;
- inclusive recall counting partial detections;
- precision over adjudicated reportable findings;
- duplicate rate;
- unique validated root causes;
- recall by vulnerability family and classification;
- partial and unresolved match counts;
- run completion assurance;
- runtime, requests, input/output/cache tokens, and estimated cost;
- cost and requests per unique true positive;
- contamination status.

For comparisons with repeated runs, show median, range, and per-item detection frequency. Do not imply statistical confidence from one run.

### 15.9 Evaluation detail UI

Tabs:

- `Summary`: scorecards, caveats, and configuration provenance.
- `Ground Truth`: expected item by matched scanner lead, with found/partial/missed status.
- `Additional Findings`: unmatched scanner findings and their adjudication.
- `Coverage`: threat scenarios, semantic obligations, and partial coverage reasons.
- `Efficiency`: runtime, token, request, and validator telemetry.
- `Audit`: dataset digest, source digest, matching version, edits, and contamination checks.

The Ground Truth table must allow expanding a row to show:

- expected root cause and locations;
- matched lead evidence and locations;
- evaluator rationale;
- confidence;
- manual override controls with an audit reason.

### 15.10 Benchmark persistence

Add:

`BenchmarkDataset`

```text
id
name
schema_version
source_digest nullable
ground_truth_json
ground_truth_digest
created_at / updated_at
```

`BenchmarkEvaluation`

```text
id
name
sast_run_id
dataset_id
status
match_mode
matching_version
policy_json
run_provenance_json
blindness_status
blindness_checks_json
metrics_json
error_message
started_at / completed_at
created_at / updated_at
```

`BenchmarkMatch`

```text
id
evaluation_id
ground_truth_external_id nullable
scan_lead_id nullable
disposition
confidence
rationale
human_reviewed
review_note
created_at / updated_at
```

The nullable sides allow missed ground-truth rows and additional scanner findings. Add uniqueness constraints that prevent duplicate relationships within an evaluation.

Future `BenchmarkComparison` can reference multiple evaluations without changing scan execution.

### 15.11 Benchmark APIs

Settings:

```text
GET /api/settings/benchmark-lab
PUT /api/settings/benchmark-lab
```

Datasets:

```text
GET    /api/benchmark-lab/datasets
POST   /api/benchmark-lab/datasets
GET    /api/benchmark-lab/datasets/{id}
PUT    /api/benchmark-lab/datasets/{id}
DELETE /api/benchmark-lab/datasets/{id}
```

Evaluations:

```text
GET  /api/benchmark-lab/evaluations
POST /api/benchmark-lab/evaluations
GET  /api/benchmark-lab/evaluations/{id}
POST /api/benchmark-lab/evaluations/{id}/run
POST /api/benchmark-lab/evaluations/{id}/matches/{match_id}/review
GET  /api/benchmark-lab/evaluations/{id}/export
```

Creation rejects a non-terminal SAST run. Running an evaluation never calls SAST lifecycle methods and never changes candidate validation status.

## 16. Reporting and exports

SAST report additions:

- compact repository-model summary;
- threat-model summary and assumptions;
- semantic coverage totals and unresolved high-priority obligations;
- discovery strategy provenance;
- unique candidate count before and after reconciliation;
- partial-coverage reasons;
- dependency advisory database timestamp.

Complete SAST run export must version and include the new repository model, threat model, scenarios, obligations, edges, candidate relationships, and phase checkpoints. It must not include separately stored benchmark datasets or evaluations.

Benchmark evaluation exports support JSON, CSV match tables, and Markdown summaries. Exports identify contaminated or partially adjudicated evaluations prominently.

## 17. Observability and efficiency

Track by phase and strategy:

- elapsed time;
- LLM calls and retries;
- input, output, cache-read, and cache-write tokens;
- files and unique source spans read;
- repository facts created and reconciled;
- obligations created and resolved;
- candidates emitted, merged, split, confirmed, dismissed, and deferred;
- adjacent concerns raised and resolved;
- duplicate validation calls avoided;
- caps and truncations reached.

Use these metrics to budget work dynamically. High-priority unresolved threat scenarios receive budget before repeated review of low-confidence generic sinks.

## 18. Migration and compatibility

- Use Alembic for all schema additions and changes.
- New tables use cascading foreign keys to `sast_run` or evaluation parents where ownership is unambiguous.
- Preserve old SAST runs and exports; missing new phase data renders as `Not available for this run`.
- Import recognizes prior export schema versions and does not fabricate threat or semantic coverage data.
- Keep `SastWorkItem.lead_id` during a compatibility window while new relationships are populated.
- Existing SAST API response fields remain stable; add new fields or endpoints rather than changing meanings silently.
- Benchmark feature defaults to disabled for both fresh and upgraded databases.

## 19. Security and privacy requirements

- Treat source, repository documentation, ground truth, and evaluator notes as untrusted data.
- Never execute source or ground-truth content.
- Preserve ZIP traversal and extraction-root protections.
- Never copy secret literal values into repository or threat models.
- Keep benchmark ground truth out of scanner prompts, checkpoints, evidence receipts, exports, and dynamic lead handoffs.
- Redact provider credentials and sensitive runtime configuration from provenance snapshots.
- Validate dataset size and schema before persistence.
- Limit evaluator prompt size and sanitize exported filenames.
- Deleting a SAST run must either reject while evaluations reference it or retain an immutable evaluation snapshot; choose and document one behavior before implementation. The recommended behavior is to reject deletion until evaluations are deleted or explicitly detached.

## 20. Testing strategy

### 20.1 Repository model tests

- parser adapters produce the same normalized fact shapes across languages;
- component, operation, actor, asset, control, and edge fingerprints are stable;
- fallback reconciliation activates when completeness heuristics fail;
- caps and truncation create partial-coverage reasons;
- unsupported frameworks degrade explicitly rather than producing false full coverage.

### 20.2 Threat analysis tests

- structured threat-model tool output validates against schema;
- evidence anchors resolve to inventoried files;
- assumptions remain distinct from source-established facts;
- threat scenarios do not become findings without discovery and validation;
- independent baseline prompts exclude generated threat scenarios.

### 20.3 Work-program tests

- each high-priority threat scenario creates at least one obligation;
- an obligation can link to multiple leads and a lead to multiple obligations;
- worker completion requires all assigned obligations to reach a terminal status;
- secondary candidates and adjacent concerns persist correctly;
- unresolved high-priority obligations force partial completion.

### 20.4 Reconciliation and validation tests

- duplicate instances consolidate without losing locations or evidence;
- independently remediable root causes remain separate;
- only reconciled candidates launch validators;
- validators cannot directly confirm adjacent concerns;
- closure-created candidates receive reconciliation and validation.

### 20.5 Benchmark tests

- `BenchmarkLabConfig.panel_enabled` defaults to false;
- the sidebar section appears when either Reporting Lab or Benchmark Lab is enabled;
- disabling Benchmark Lab hides navigation without deleting data;
- only terminal SAST runs can be evaluated;
- ground truth is absent from SAST prompts, checkpoints, receipts, analysis APIs, and run exports;
- digest mismatch and direct answer-key access produce the correct blindness status;
- deterministic matching is stable;
- assisted matching is stubbed in tests and cannot mutate scan results;
- manual overrides retain audit history;
- metrics distinguish full, partial, missed, duplicate, false-positive, additional-valid, and unreviewed states;
- contaminated evaluations are excluded from aggregate comparisons by default;
- route parsing, lazy route registration, settings APIs, and feature toggle interactions are covered.

### 20.6 End-to-end evaluation corpus

Maintain a private or separately packaged blind corpus spanning:

- multiple server and client languages;
- conventional and custom frameworks;
- monoliths, services, workers, CLIs, and libraries;
- injection, authorization, authentication, sensitive output, business logic, missing controls, configuration, dependencies, and browser sinks;
- safe controls and near-miss patterns for precision.

Ground truth must not be stored inside the source archives supplied to SAST. Run important configurations at least three times and report per-item detection frequency.

## 21. Rollout plan

### Slice 0 — Evaluation foundation

- Add Benchmark Lab toggle under System Settings -> Feature Visibility.
- Add hidden-by-default sidebar route under `Testing Features`.
- Add datasets, evaluations, matches, deterministic matching, audit status, and basic result matrix.
- Evaluate only completed ordinary SAST runs.

This slice establishes reliable measurement before scanner behavior changes.

### Slice 1 — Repository model

- Move/refactor compact component-fact extraction before discovery.
- Add normalized nodes and edges, evidence, confidence, and completeness warnings.
- Add parser adapter interface and initial supported adapters.
- Add LLM reconciliation fallback.

### Slice 2 — Threat analysis and planning

- Add persisted threat model and scenarios.
- Add semantic obligation model and generator.
- Add threat-model and planning phases to lifecycle, resume, API, UI, and export.

### Slice 3 — Discovery redesign

- Add isolated independent baseline auditor.
- Create threat-directed worker packets.
- Retain and retune sink-first discovery.
- Move dependency analysis into a deterministic pass.
- Allow secondary candidates and adjacent concerns.

### Slice 4 — Candidate reconciliation

- Add many-to-many obligation/lead relationships.
- Add pre-validation merge/split pass.
- Validate unique candidates only.
- Add post-validation severity and root-cause reconciliation.

### Slice 5 — Semantic closure

- Add closure queue and worker.
- Permit closure-created candidates.
- Replace structural completion with semantic completion rules.
- Surface unresolved scenarios and proof gaps in Coverage UI.

### Slice 6 — Policy, efficiency, and comparison

- Add configurable finding classes and phase budgets.
- Add phase/strategy efficiency telemetry.
- Add multi-evaluation comparisons, repetitions, trend views, and regression thresholds to Benchmark Lab.

Each slice must ship with migrations, backend tests, frontend tests, architecture documentation updates, user-facing changelog updates, and rebuilt frontend assets when UI changes are implemented.

## 22. Acceptance criteria

The program is complete when:

1. SAST produces a source-backed repository and threat model before discovery.
2. Material threat scenarios become persisted, auditable semantic obligations.
3. Unsupported or incompletely mapped architecture cannot silently receive full coverage.
4. Independent baseline, threat-directed, deterministic, and sink-first strategies all contribute to one candidate ledger.
5. A reviewed trace can produce multiple distinct candidates.
6. Duplicate candidates are consolidated before independent validation.
7. Closure accounts for every high-priority scenario and can recover missed candidates.
8. Dependency versions receive a deterministic analysis path.
9. Existing pause, resume, evidence, export, and handoff behavior remains functional.
10. Benchmark Lab evaluates completed normal SAST runs without exposing ground truth to scanner phases.
11. Benchmark Lab is hidden by default and appears under `Testing Features` only after its System Settings toggle is enabled.
12. Blind evaluation results include recall, precision, duplicates, coverage assurance, efficiency, provenance, and contamination status.
13. Cross-language blind-corpus evaluation demonstrates improved recall without an unacceptable precision, duplicate-rate, or cost regression.

## 23. Review decisions still required

1. Whether the first parser adapter release should support a small set of major language families or ship only the adapter interface plus LLM reconciliation.
2. Whether benchmark ground truth should be stored in the main AESPA database or a separate evaluator database. A separate database provides a clearer isolation boundary and mirrors Reporting Lab storage, but requires explicit backup/export behavior.
3. Whether Benchmark Lab should expose deterministic matching only in the first slice or include assisted matching immediately.
4. Whether deleting a referenced SAST run should be blocked or detach evaluations onto immutable snapshots.
5. Which finding classifications and negative-control families are enabled by default in ordinary SAST policy.
6. Initial phase budgets and the conditions under which closure may request additional budget.

