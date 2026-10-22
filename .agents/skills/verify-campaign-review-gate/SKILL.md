---
name: verify-campaign-review-gate
description: "Formally check the campaign review gate: live testing starts only after review, and a rejected path is not queued. Use when editing submit_review, continue_to_live_testing, apply_review_decisions, or compile_runnable_cases."
---

# Verify the campaign review gate

A test samples a few review orders. This check runs the real gate functions across the review orders they allow, plus the transaction gap between the status read and the decision write.

Run it from the repository root after any change to the covered functions. The command needs `uv` and the project environment. It does not start a crawl, a scanner, or an LLM.

```bash
uv run python scripts/check_campaign_review_gate.py
```

Exit 1 is the baseline at the sync commit: every hold passes, and the two findings below reproduce. Exit 0 means those findings no longer reproduce and every hold still passes. A `FAIL` hold, or a finding other than the two named here, means the change broke a promise the sync commit keeps. Stop and treat that as a bug in the change.

## What is verified

Live testing of a campaign path is the dynamic scan that runs after a person reviews SAST proposals. The harm of a bad gate is that AESPA attacks a live site or API on a path the reviewer did not approve, or skips a path the reviewer did approve, after Start was already accepted.

Two promises are checked in `scripts/check_campaign_review_gate.py`:

- Live testing starts only from `awaiting_review`, and only after `review_submitted_at` is set. A partial review does not set that stamp. An empty review is refused while any proposal is still `proposed`, and a decision for another campaign changes nothing.
- Once `continue_to_live_testing` has committed `dast_running`, a review that starts after that commit does not change a mapping. Separately, `compile_runnable_cases` is the step that copies a lead into the child run.

The checker calls `campaigns.submit_review`, `campaigns.continue_to_live_testing`, `correlation.apply_review_decisions`, and `campaign_validation_cases.compile_runnable_cases` on an in-memory SQLite database. The live-testing task is replaced with a no-op after the status commit, so the status write is real and no scan starts. The race parks inside `apply_review_decisions`, which is the next database transaction after `submit_review` closes its status-check session (`src/aespa/services/campaigns.py`, the session that ends just before `apply_review_decisions`). That boundary is one indivisible step in the code: the status check commits, then the decision write opens its own session.

This is an explicit-state check of those functions, not a TLA+ model. A separate model would stay green if someone deleted a guard in the Python. The repo has no installed verifier that runs on the Python itself. No extra tool is installed; the command uses the project's Python and `uv.lock`.

## Known findings at the sync commit

Do not weaken the check, and do not change product code, to make a finding disappear. Report a finding in the words below. Change the product only when the user asks.

**Review decision commits after live testing starts.** `submit_review` reads `awaiting_review` and returns from that session. Before `apply_review_decisions` commits, `continue_to_live_testing` can commit `dast_running`. The decision still changes the mapping. At the sync commit the checker rejects an approved mapping in that gap: the campaign is `dast_running` and the mapping is `rejected`. A scan that resolves approved mappings after that write will test a different set from the set Start authorized.

**Compile queues a resolved case after its mapping was rejected.** `compile_runnable_cases` selects `CampaignValidationCase` rows with `readiness_status == resolved` and does not read `LeadTargetMapping.status`. The checker resolves a case, sets that mapping to `rejected`, and calls compile. The rejected mapping's lead is copied into the child run. `apply_review_decisions` does not clear readiness, so a rejection that lands after resolve leaves a case this copy will queue.

## Coverage record

Sync commit: `06d48d23d159cd0cc7843cb07671cb5d6243705c`

Confirmed at that commit on 22 Oct 2026. The checker prints `HEAD`. When `HEAD` is not this commit, re-read the covered functions before trusting the result. Move this sync commit forward only after you confirm the check still describes the code at the new commit. If a known finding no longer reproduces, confirm the function now enforces it, then delete that finding from this skill. If the code change is intentional, update the hold or the finding text so it matches the new behavior, and say what changed.

Covered code:

- `src/aespa/services/campaigns.py` — `submit_review` (status check, empty-review refusal, stamp when nothing is still `proposed`), `continue_to_live_testing` (status and stamp checks, commit of `dast_running`)
- `src/aespa/services/correlation.py` — `count_pending_mappings`, `apply_review_decisions` (unknown mapping refuses the whole batch; a decision writes `approved` or `rejected`)
- `src/aespa/services/campaign_validation_cases.py` — `compile_runnable_cases` (copies resolved cases; the copy query does not filter on mapping status)

## What a failure means

- `FAIL` on a hold: the real function no longer keeps that promise. Example: deleting the `review_submitted_at is None` raise in `continue_to_live_testing` makes "live testing refuses to start before the review is stamped" fail, and the detail shows `status=dast_running stamped=False`. That was run once against a scratch edit and then the edit was removed. The baseline after that removal is the two findings only.
- `the review gap can be exercised` fails: the checker did not reach `apply_review_decisions`. That is a harness problem. Do not "fix" the product to satisfy it.
- `FINDING` text: product behavior. A counterexample is the sentence under the finding. Read it as campaign status, mapping status, and which function wrote them.
- A pass does not prove the scanner, the crawl, or a second process. It proves the checked orders of these functions on one in-memory database.

## Left out

- Crawl, scanner startup, and whether a copied lead is sent to a host
- Supplemental validation, which passes an explicit approved `mapping_ids` set into compile
- Restart reconciliation, stop, and resume of a child run
- More than one mapping inside the race
- A rejection that arrives after the lead was already copied and the scanner is reading it
- Any order that cannot be expressed as these function calls and the one transaction gap

## Tell a modeling error from a bug

The holds call the public functions and read the committed rows. A hold fails only when those rows disagree with the promise. The race is not a guessed interleaving: it blocks the real `apply_review_decisions` after `submit_review` has already passed the status check. The compile finding calls the real `compile_runnable_cases` after the mapping row is `rejected`. If a result depends on the no-op live-testing task rather than the status column, say so and fix the checker. Do not explain a `FAIL` hold away by calling the in-memory database unrealistic: these functions use the same session and status values against any database.
