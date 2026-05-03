# AESPA — AI-Enabled Security Pentesting Agent

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup

Install uv: https://docs.astral.sh/uv/getting-started/installation/

```bash
# Install dependencies
uv sync

# Install Playwright's Chromium browser (one-time)
uv run playwright install chromium
```

## Running

```bash
uv run aespa
```

The UI is available at `http://127.0.0.1:8000` by default.

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `AESPA_DATABASE_URL` | `sqlite:///./aespa.db` | SQLAlchemy database URL |
| `AESPA_HOST` | `127.0.0.1` | Bind address |
| `AESPA_PORT` | `8000` | Bind port |

## LLM Configuration

Open the app, go to **LLM Settings**, and configure one of:

- **Anthropic** — requires an Anthropic API key
- **OpenAI** — requires an OpenAI API key
- **Google** - requires a Google API key
- **OpenAI-compatible** — for local models via LM Studio (`http://localhost:1234/v1`) or Ollama (`http://localhost:11434/v1`); no API key required

## Use
Landing page:
![Screenshot](docs/images/sites.png)

Site setup:
![Screenshot](docs/images/sitesetup.png)

Crawler:
![Screenshot](docs/images/crawler.png)

Scan in progress:
![Screenshot](docs/images/scanprogress.png)

Traffic log:
![Screenshot](docs/images/trafficlog.png)

Findings:
![Screenshot](docs/images/finding.png)

## Dev comments:

**Crawler/Site Map** - "mostly works"
* The crawler works by submitting the contents of the page to an LLM and asking it where to visit next. 
* Multi-user crawling works by having multiple headless Chromium browsers via Playwright crawl at once, and matching page URLs. (this is going to be an issue for SPA apps which don't update the URL)

**Scan** 
* This works by grabbing auth tokens from each user via Playwright then the structure of pages from the site map, plus the information collected (i.e. uses authentication, has object references, takes user input etc) are sent to the LLM to determine what should be tested. The LLM generates HTTP probes in JSON format, which are then interpreted back to HTTP requests and sent by HTTPX. The responses are sent back to the LLM to determine whether there's a finding here.
* I've been testing this with qwen3-coder-30b which is the only model that runs acceptably fast locally and the results aren't very good, it's mostly false positives. Need to adjust prompts + test with a better model
* Testing raw prompts directly against qwen3-coder, I've observed that it doesn't give very good security testing advice in general, hah.
