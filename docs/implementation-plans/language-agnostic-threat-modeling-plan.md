# Language-Agnostic Threat Modeling Plan

## Goal

Generate useful, source-backed threat models for web applications and APIs written in any language. Common frameworks should benefit from cheap parser hints, but unsupported languages must still receive an agent-led source review.

The first release target is at least 80% recall for known important assets, actors, trust boundaries, entry points, and sensitive operations in each benchmark ecosystem. A scan must not report full semantic coverage when expected application structures were not mapped.

## Current problem

The repository model is currently built mainly from Python, JavaScript, manifest, and compact pattern adapters. The threat model then derives its assets from repository nodes classified as `store`.

This makes the initial detector an overly strong filter. Bank of Ed demonstrates the failure:

- SQL files are present in the source archive but excluded from the compact source-file suffix list.
- PHP PDO connections are not recognized by the datastore patterns.
- No `store` nodes are created.
- The threat model copies `store` nodes into `assets`, so the result contains no assets.
- The model-assisted threat pass cannot add assets directly and has no source-reading tools.

Assets and storage also need to be separate concepts. A MySQL database is a store. Customer identities, account balances, card data, authentication secrets, and transaction integrity are assets.

## Proposed workflow

```text
Source archive
    -> language-neutral file inventory
    -> deterministic parser and pattern hints
    -> agent-led architecture and threat review with file tools
    -> structured merge and evidence validation
    -> completeness checks and focused retry
    -> threat scenarios and required security checks
```

Deterministic analysis remains useful for fast inventory, stable fingerprints, source ranking, common-framework hints, and output validation. It must not decide whether an asset, actor, boundary, or sensitive operation is allowed to exist in the threat model.

## Canonical data

Keep the existing repository and threat-model records. No database migration is required for the first implementation because `SastSurfaceItem.kind` and the threat-model JSON fields can store the expanded data.

Add normalized repository items for:

- `asset`: data, identity, privilege, or integrity guarantee that matters
- `store`: database, file store, cache, queue, object store, or other persistence mechanism
- `actor`: user, role, service, administrator, or external system
- `identity`: session, account, service identity, tenant, or machine credential
- `boundary`: transfer of data or authority between trust zones
- existing operations, controls, inputs, outputs, sinks, dependencies, and deployment facts

Each generated item must include:

- a stable semantic ID and fingerprint
- name, type, and short description
- provenance such as parser, pattern, agent review, or user context
- confidence
- one or more `path:line` evidence references for source-derived facts
- related component or store IDs where available

Threat scenarios must refer to asset IDs rather than treating stores as assets.

## Implementation slices

### 1. Language-neutral inventory and source ranking

Update `sast_scanner.py`, `component_facts.py`, and `sast_parsers.py` so the semantic phases receive an inventory of all readable files, not only a fixed list of source suffixes.

- Detect text by content with file-size and binary limits.
- Classify known extensions, including SQL, XML, YAML, properties, configuration, deployment, and common schema or migration formats.
- Keep unknown readable files in the inventory as `Other`.
- Exclude or strongly deprioritize vendored dependencies, generated bundles, build output, and test fixtures while recording that they exist.
- Rank likely architecture files first: manifests, entry points, routes, controllers, middleware, auth, models, schemas, migrations, database helpers, configuration, deployment files, and external-client code.
- Add cheap hints for common database and persistence technologies across .NET, Java, JavaScript, Python, PHP, Go, Ruby, and SQL.

These hints improve navigation. They are not the final asset list.

### 2. Agent-led architecture and threat analysis

Replace the current plain completion used for threat enrichment with a checkpointed agentic phase using the existing path-jailed `list_files`, `glob`, `grep`, and `read_file` tools.

Add a small threat-model tool set in `services/prompts/sast.py`:

- the four read-only source tools
- `record_model_fact` to add a source-backed asset, store, actor, identity, boundary, control, operation, or deployment fact
- `record_threat_scenario` to add a bounded scenario linked to recorded facts
- `finalize_threat_model` to submit the summary, attacker capabilities, security objectives, assumptions, and open questions

The tool executor must:

- reject evidence paths outside the extracted archive
- require the cited file and line to exist
- require source files to have been opened before their evidence can support an agent fact
- deduplicate facts by semantic fingerprint
- cap facts, scenarios, tool calls, file reads, and returned text
- prevent literal secret values from being stored
- checkpoint after every completed tool exchange so pause and resume continue safely

The agent should start with the source inventory and deterministic hints, then inspect representative files. It should follow inputs through entry points, controls, stores, and sensitive operations and work backward from important consumers. Unknown frameworks use the same file tools rather than a separate fallback prompt.

### 3. Merge and completeness validation

Add a language-neutral merge and validation step in `sast_semantic.py`.

- Preserve deterministic facts and add accepted agent facts with their own provenance.
- Keep physical stores separate from protected assets.
- Verify every source-derived evidence reference against the archive and evidence receipts.
- Reject unsupported relationships and references to missing semantic IDs.
- Prefer higher-confidence source-backed facts while preserving distinct evidence.

Run completeness checks before planning:

- database client, ORM, SQL schema, migration, or persistent write found with no stores or assets
- authentication or session code found with no actors, identities, or auth boundary
- server or API framework found with no entry points
- routes found with no untrusted inputs
- file, network, process, query, deserialization, or state-mutation consumers found with no sensitive operations
- meaningful production source left outside both parser coverage and direct agent reads
- file, fact, tool, token, or scenario cap reached
- model provider unavailable or model phase interrupted

Send unresolved high-value gaps through one focused agent retry. If material gaps remain, continue only with partial semantic coverage and retain specific open questions. Never turn an empty section into an implicit `none found` result.

### 4. Threat scenarios and scan planning

Update `build_threat_model` and `plan_semantic_obligations` so scenarios come from the merged threat model.

- Use assets, actors, entry points, boundaries, controls, and sensitive operations selected by the threat analyst.
- Keep deterministic scenario generation only as a reduced-coverage fallback.
- Generate required security checks for each important scenario and unresolved material gap.
- Carry asset and boundary references into discovery worker packets.
- Prevent `completion_status = full` when threat-model completeness has a material warning.

If the configured model is temporarily unavailable, use the existing retry and pause behavior. If a user deliberately runs without a usable model, allow the deterministic fallback but label the result as reduced coverage.

### 5. UI and reporting

Update the SAST Model, Threats, Coverage, and Efficiency views.

- Show assets separately from stores.
- Show evidence, type, confidence, and provenance for assets and boundaries.
- Display threat-model quality as full, partial, or reduced coverage with plain reasons.
- Show how many files were directly reviewed during architecture and threat analysis.
- Show caps and focused retries.
- Treat zero assets as a warning when persistence, authentication, or sensitive operations were detected.
- Preserve the same fields in SAST JSON export and restore.

Do not edit `src/aespa/web` directly. Rebuild it from `frontend/` after the UI work.

### 6. Evaluation and the 80% target

Add a threat-model benchmark suite separate from vulnerability-finding ground truth. Start with small, reviewable fixtures for:

- PHP and MySQL, using a reduced Bank of Ed fixture
- ASP.NET Core and Entity Framework
- Spring Boot and JPA
- Node.js with Express and an ORM
- Python with FastAPI or Django
- Go with an HTTP router and SQL client
- one unsupported or uncommon language fixture to exercise the generic path

Each fixture should define expected semantic items by class and stable meaning, not exact generated prose. Score:

- asset recall
- actor and identity recall
- entry-point recall
- trust-boundary recall
- sensitive-operation recall
- evidence validity
- unsupported extra facts for precision monitoring

Release gates:

- at least 80% recall in every semantic class for every primary ecosystem fixture
- at least 80% macro-average recall across fixtures
- 100% valid evidence references for accepted source-derived facts
- no empty asset model when the fixture contains clear persistent or sensitive state
- no full-coverage result when a material completeness check remains unresolved
- stable results across repeated model runs, reported as median and range

Use deterministic fixture tests for inventory, merge, evidence checks, and completeness rules. Use stubbed model transcripts for normal CI. Run repeated real-model evaluations as a release check because nondeterministic recall cannot be established by mocked tests.

## Main code areas

- `src/aespa/services/sast_scanner.py`: phase orchestration, checkpointed threat agent, pause and retry behavior
- `src/aespa/services/prompts/sast.py`: threat-analysis prompt and tool schemas
- `src/aespa/services/sast_semantic.py`: normalized merge, evidence validation, completeness checks, scenarios, and planning
- `src/aespa/services/component_facts.py`: language-neutral source hints and broader persistence markers
- `src/aespa/services/sast_parsers.py`: optional parser adapters and parser coverage warnings
- `src/aespa/services/sast_workprogram.py`: completion decision and coverage summary
- `frontend/src/features/sast-runs/SemanticAnalysisView.jsx`: assets, stores, evidence, and quality state
- `tests/sast/`: unit, phase, resume, and regression coverage
- `tests/fixtures/`: cross-language threat-model fixtures and expected semantic items

## Delivery order

1. Add the benchmark fixtures and scoring helper first so changes have a measurable target.
2. Add language-neutral inventory, SQL support, PHP PDO hints, and completeness warnings. Confirm the Bank of Ed regression fixture fails before the fix and passes afterward.
3. Add the checkpointed threat-model agent and structured recording tools.
4. Add merge validation, evidence checks, and the focused retry.
5. Connect the merged model to scenarios, security checks, and the completion decision.
6. Update the UI, exports, architecture documentation, changelog, and packaged frontend assets.
7. Run unit tests, SAST service tests, frontend lint and tests, the frontend build, and repeated real-model benchmark evaluations.

## Compatibility and rollout

- Existing SAST runs remain readable. Their stored threat models are not rewritten.
- New fields inside JSON structures must have tolerant readers and defaults.
- Keep the old deterministic threat builder for restored older checkpoints and explicit reduced-coverage runs.
- Add a prompt and semantic-model version so resumed scans do not mix incompatible contracts.
- A run paused before threat analysis can resume with the new phase. A run with a completed old threat-model checkpoint should keep its existing result unless the user restarts the scan.
- Preserve the current uncommitted SAST cleanup and UI-state work when implementation begins.

## Out of scope for the first release

- Building complete compilers or call graphs for every language
- Guaranteeing 80% recall for arbitrary unknown applications with no readable source
- Runtime confirmation of every threat-model fact
- Automatically changing user-supplied threat models or deployment assumptions
- Treating threat scenarios as confirmed vulnerabilities
