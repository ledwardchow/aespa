# Workflow index

The coverage response returns two collections. `workflows` contains all identified workflows, including those that have not been reached. `items` contains security checks for reached workflows only. Existing scan enforcement continues to consume `items`.

A workflow row has a run-scoped `workflow_key`, name, goal, crawl status, reached page reference, and optional root/latest note references. A security check retains its own status and evidence. Note-derived identity is `note:<root-note-id>`. Main-crawl state identity is `page:<page-id>`. A page represented by a workflow note does not get a duplicate automatic row. Separate states at one URL remain distinct.

`list_workflow_tests(run_id)` derives inventory from existing pages and notes, so archived crawls rebuild identity after IDs are remapped. `seed_workflow_tests(run_id)` creates checks only where reached-state evidence exists. The coverage model uses a unique run/workflow-key/check-kind constraint, with nullable note IDs for main-crawl workflows.

Identification reviews reached functions as well as missed candidates. An explicit observed page ID establishes the reached state. Reached proposals are recorded without replaying the workflow or asking the user. Unreached proposals use the existing browser exploration and input requests. Reaching a form does not establish transaction completion or a passing security test.

Notifications continue to use unresolved user-input requests from unsuccessful attempts. A successful workflow never notifies, even if stale input flags exist. Security checks never create crawl notifications.

Two designs were considered. A normalized inventory table adds another persistence and archive mapping path. The derived inventory uses sources already saved and preserves existing retry and archive behavior. The independent design judge preferred the derived design. The normalized design's separation of crawl and security state was retained in the response contract.

Final review tightened inference deduplication to name, start URL, and goal. The visible-goal instruction clarifies that further actions mean the workflow is unreached. Legacy partial-schema migration tests required reflecting the coverage table without recursively loading referenced tables. All 115 backend checks passed after these changes. The built UI showed four workflow rows after reload and exactly one input notification, with no browser errors. Frontend lint, type checking, 370 unit tests, build, and formatting checks for changed frontend files passed. The full frontend formatting command has unrelated existing failures in four untouched files.
