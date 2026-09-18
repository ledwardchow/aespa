# Systems and Campaigns

Systems group code components and live targets that belong to one product.
Use them when a system is split across repositories, services, or frontends and
you want AESPA to connect source findings to the correct live target.

The feature is optional. Enable **Systems** under **System Settings > Feature
Visibility** if it is not shown in the sidebar.

## Prepare an system

Create a System, then add:

- **Code Components**: Named repositories or services. Upload an immutable source
  ZIP snapshot for each component you want to test.
- **Live Targets**: Existing Sites and API Collections that make up the product.
  A target can be linked to a component when ownership is known.

## Start a campaign

A campaign needs at least one component snapshot and one live target. Choose the
snapshots and targets, an LLM profile, SAST concurrency, and any optional mapping
limits. Review the frozen selection before starting it.

The campaign then:

1. Runs SAST against the selected component snapshots.
2. Extracts source-backed interface facts and matches calls between components.
3. Proposes which live target should receive each reportable lead.
4. Waits for a person to approve or reject the proposed paths.
5. Resolves approved paths against real API endpoints or crawled browser actions.
6. Starts focused SAST Validate child runs for ready paths.

The **Runs**, **Components**, **Connections**, **Review Leads**, **Findings**, and
**Activity** tabs show the campaign's progress. Findings stay owned by the child
web or API run and are collected in the campaign view.

Stopping a campaign waits for its active child work to stop safely. Resume reuses
completed scans and saved mapping work. Individual child runs can also be resumed
from their normal SAST, web, or API pages.
