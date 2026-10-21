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
The preview shows at most 100 findings. Counts for SARIF and structured Markdown
cover the complete report.
Other JSON, unstructured Markdown, and plain text reports can be reviewed with
the model selected for the destination run. These reports must be 128 KiB or
smaller and can produce at most 100 leads. Split larger reports into separate
files before importing them. AESPA sends the report text to the selected model
only when you preview it. Each proposed lead must include an exact quote from
the uploaded file. Review the preview before importing. Import uses the same
reviewed leads and does not call the model again. A changed file needs a new
preview. Model-generated previews contain proposed leads. Compare them with the
source report for missing findings before importing. Missing confidence scores
appear as **Unknown**. A model or provider
error leaves the run without imported leads.
Report paths and links are stored as evidence; AESPA does not open them while
importing. File imports require the updated backend: wait for active scans to
finish before restarting an older AESPA server.

## SARIF

Upload a `.sarif` file or SARIF `.json` file using
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
Unstructured Markdown and plain text reports use model review during preview.
Malformed SARIF files return an error instead of being sent to the model.
