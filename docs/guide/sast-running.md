# Running SAST Scans

Standalone SAST scans analyse a source ZIP and produce source-backed leads. A
lead is a hypothesis until it is validated. Reportable leads can be copied into
a web or API run for live testing.

## Start a scan

Open **SAST**, select **New SAST scan**, and choose:

- A source ZIP of up to 250 MB.
- An optional run name.
- **Light** for the lower-cost source inventory, discovery, validation, and
  attack-path workflow.
- **Deep** to add repository modelling, threat scenarios, security coverage
  planning, candidate reconciliation, and semantic closure.
- An optional LLM profile. The active global profile is used when none is set.

The scan starts when the run is created.

## Review progress and results

The run moves through scope, model, threat, planning, discovery, reconciliation,
validation, closure, attack-path, and report phases as required by its analysis
mode. Its views show:

- **Coverage**: Files, source items, and security obligations reviewed by workers.
- **Model** and **Threats**: Repository facts, assets, actors, boundaries, and
  threat scenarios generated for Deep analysis.
- **Security checks**: Planned security obligations and their dispositions.
- **Candidates**: Confirmed, dismissed, and inconclusive candidates with source,
  control, sink, counterevidence, proof gaps, and attack-path information.
- **Activity**: Worker and validator progress.
- **Execution Summary**: Phase budgets and efficiency information when available.

Pause waits for a safe agent-step boundary. Resume restores saved phase
checkpoints. A stopped or interrupted scan can continue without discarding
completed worker and validator results.

## Send leads to live testing

Only reportable leads can be handed off. Use a completed SAST run's handoff action,
or import the run from the **SAST Leads** tab of an existing web or API run. AESPA
creates a copy owned by the receiving run, so resolving it does not modify the
standalone SAST result.

Use **SAST Validate** on the receiving run when you want to test only the imported
leads. Quick scans also require imported open leads to be resolved before they
finish. Full scans include them in the wider coverage workflow.

SAST runs can be exported as a complete JSON bundle, including the source ZIP,
saved phase state, results, activity, and component facts. Leads can also be
exported as Markdown.
