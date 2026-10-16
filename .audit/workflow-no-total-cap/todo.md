- [x] Reproduce the four-workflow admission cap in the owning source.
- [x] Add a regression showing later ordinary workflows were skipped.
- [x] Remove total admission cap while retaining concurrency and payment/deletion restrictions.
- [x] Run workflow tests and a real local crawl with six ordinary workflows and two restricted workflows.
- [x] Independently review, clean up, and hand back.

Bug-fix playbook. Reproduce, identify cause, plan fix, verify same surface, preserve failing-before-passing evidence. No commit or PR requested. No signature or design change needed. Existing approved generated-data behavior remains the design.

Verified. Regression failed under the four-proposal cap and passed after removal. 70 workflow and coverage tests passed. The actual local browser crawl submitted six ordinary workflows with generated values, while payment needed input and deletion stayed blocked. Independent source review passed. Version 0.7.20261016.10.
