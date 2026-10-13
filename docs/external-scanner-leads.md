# Import findings from another scanner

Open a web or API run's **SAST Leads** tab, choose **Import SAST leads**, then
**Import from file**. Select a report, choose **Preview report**, review its
counts and warnings, then choose **Import**. Importing does not start a scan.
Use the existing **SAST Validate** mode when you want DAST to focus on these leads.

The preview does not save anything. Imports add open, unverified leads only to
the selected run. Scanner verdicts never become confirmed AESPA findings on
import. AESPA preserves the source scanner, rule ID, filename, file locations,
reported snippets, and SARIF code flows for investigation. Reimporting the same
findings into the same run skips duplicates, even if the report was renamed.
Other runs can import and investigate their own independent copies.

Reports must be UTF-8, at most 5 MiB, and contain at most 5,000 findings/results.
The preview shows at most 100 findings; its counts cover the complete report.
Report paths and links are stored as evidence; AESPA does not open them while
importing. File imports require the updated backend: wait for active scans to
finish before restarting an older AESPA server.

## SARIF

Upload a `.sarif` or `.json` file using
[SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html).
AESPA reads results across all runs, including rules defined in tool extensions,
message templates, artifact indexes, and physical or logical locations. Results
marked absent, results with accepted or unspecified suppressions, and results that are neither failures nor
review items are skipped and counted in the preview.

Severity uses explicit severity metadata when present, then a numeric
`security-severity` score (critical ≥9, high ≥7, medium ≥4, low >0, info =0).
Otherwise SARIF error/warning/note/none levels map to high/medium/low/info.
No confidence score is inferred when the scanner does not provide one.

## Markdown

Choose **Download Markdown template** in the dialog. Use one level-two heading
per finding and metadata bullets followed by Description and Evidence sections:

````markdown
# External scanner findings

## Missing ownership check

- Scanner: My scanner
- Rule ID: auth-001
- Severity: high
- Category: A01
- Location: src/api/orders.py:42
- Suggested endpoint: GET /orders/{id}

### Description

The order lookup accepts an ID without checking the caller's ownership.
Verify the behavior against the live target.

### Evidence

```python
return db.get(Order, request.path_params["id"])
```
````

The title is required. Severity defaults to medium; supported values are
critical, high, medium, low, and info. Scanner, rule ID, category, location,
suggested endpoint, description, and evidence are optional. Confidence, when
provided, must be a number between 0 and 1 or a percentage such as `80%`.
Missing locations and confidence scores are called out in the preview.

AESPA's **Export leads** Markdown files are also supported, including their
embedded structured data. Import resets investigation and validation status.
Arbitrary prose and Markdown tables are not automatically converted into leads;
convert those reports to the template or export SARIF from the source scanner.
