# LLM Usage Statistics

Open **Usage** in the sidebar to review LLM consumption. AESPA records each
completed provider call independently of the scan that produced it, so deleting a
run does not remove its usage history.

The page shows lifetime and monthly totals for:

- Calls
- Input and output tokens
- Prompt-cache reads and writes
- Provider-native credits when reported
- Estimated cost when price data is available

The provider and model table keeps the exact model name and endpoint family used
for each row. Use the month selector to review earlier periods.

**Refresh prices** downloads the current LiteLLM price map. Individual rows can
use manually entered prices when the downloaded data is missing or unsuitable.
Cost is an estimate and depends on the selected price source.

**Reset statistics** permanently deletes all stored usage rows for every month.
Downloaded prices and manual price overrides are kept.
