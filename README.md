# AESPA — AI-Enabled Security Pentesting Agent

![Ask DeepWiki](https://deepwiki.com/badge.svg) ![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)

## What is this?

An **exploration** into whether a fully LLM-driven, automated web application/API "penetration tests" could work.

## What should I use it for?

Testing :) It's got a cool UI and stuff.

**This is not a replacement for human testers; it can help you scale.** If you run an offensive security team and have a lot of websites/APIs you need to work through, running this first can help you prioritise what to put testers on.

## Features

Multi-agent (test lead + specialists, adversarial validator and reporting) web app and API testing.

You will need to provide:

- For web app testing - URL and (optionally) credentials
- For API testing - documentation so that the scanner can understand the structure of the APIs in scope (OpenAPI YAML, text dumps of Confluence pages, markdown, free text files containing API credentials; just upload whatever you have and the scanner will figure it out!)
- (Optionally) ZIP of the source code for the API. It will perform a "SAST-lite" agentic examination of the code to identify leads to investigate during the DAST API testing
- An API key for an OpenAI or an Anthropic-format LLM provider

## Performance

Here's are [two](docs/results/juice-shop-results.md) [comparisons](docs/results/results-comparison.md) of this scanner, run against the [Bank of Ed](https://github.com/ledwardchow/BankOfEd/tree/vulnerable-version):

- AESPA + Sonnet 4.6 
- Claude Code + Sonnet 4.6
- Codex + GPT 5.5 
- Claude Code + Qwen3.6-35b-A3b

And a [comparison](docs/results/vuln-scanner-comparison.md) of a single (specialist agents turned off) vs multi-agent scan. As of 27th May 2026, a multi-agent scan on the Bank of Ed costs about $7.50 USD on Sonnet 4.6 token prices and about $1.50 on Deepseek v4 Flash prices (against the first-party API).

Also, scan results for [VAmPI](docs/results/vampi/vampi.md).

## Documentation

The [Architecture](docs/architecture.md).

The [changelog](CHANGELOG.md).

The [User Guide](docs/guide/index.md)!

## Requirements

- Python 3.12+
- uv: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
- Burp Suite Professional, if you want to use the active scan integration
- Anthropic/OpenAI/Google/AWS Bedrock API key **OR**
- A local model - some suggestions at the bottom

Note, this was developed/tested mostly on Bedrock/Sonnet 4.6. Your results may vary on a different setup.

If your API key has TPM/RPM quota caps this is configurable in the LLM Settings UI. If left unconfigured i've seen this consume up to ~10m TPM bursts (inclusive of cached tokens).

## Setup

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

Crawls work well on any model, including local models, so you can save a bit of money by using something cheap. Dynamic scans don't work well on local models, I've had the best results on Sonnet 4.6.

If your site is authenticated and you don't have credentials, you can start a dynamic scan directly without a site map. The agents will just have less context about what it is testing upfront.

This app is intended for use on a computer you're sitting in front of. Note to those who want to host this on anything other than localhost, this app has **NO SECURITY**, the API is **unauthenticated** and passwords/API keys you save in this app can be stolen straight off the page; you should use an authenticating reverse proxy such as Cloudflare/Tailscale for a headless instance.

## Running with Docker

The image bundles Chromium, so no separate Playwright install is needed.

### From Docker Hub

The image is published at [ledwardchow/aespa](https://hub.docker.com/r/ledwardchow/aespa). To run it without cloning this repo:

```bash
docker run -p 8000:8000 ledwardchow/aespa
```

Then open `http://localhost:8000`.

### From a clone

```bash
docker compose up -d        # pull the image, publish port 8000, persist data
```

Then open `http://localhost:8000`. The DB and uploads persist in the `aespa-data` volume across restarts. `docker compose down` to stop.

To build and run locally instead of pulling the published image:

```bash
docker compose up -d --build
```

If you run with `docker run` directly, you **must** publish the port and mount the volume yourself — there is no image-level default for these:

```bash
docker run -p 8000:8000 -v aespa-data:/data ledwardchow/aespa
```

In Docker Desktop, hitting the play button on the **Images** tab starts a container with no published port (you'd get "could not connect"). Either fill in Host port `8000` and a `/data` volume under the Run dialog's "Optional settings", or run `docker compose up -d` once and drive it from the **Containers** tab afterward — those controls reuse the port and volume.

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable             | Default                | Description             |
| -------------------- | ---------------------- | ----------------------- |
| `AESPA_DATABASE_URL` | `sqlite:///./aespa.db` | SQLAlchemy database URL |
| `AESPA_HOST`         | `127.0.0.1`            | Bind address            |
| `AESPA_PORT`         | `8000`                 | Bind port               |

If you don't do this, it will use the values above as the default.

## LLM Configuration

Open the app, go to **LLM Settings**, and configure:

- **Providers** — reusable connection settings with a name, API format, optional base URL, API key, and one or more model names. Built-in formats include Anthropic, OpenAI, OpenAI-compatible, OpenRouter, Google Gemini, Amazon Bedrock Runtime, Azure OpenAI, and Azure AI Foundry. Use OpenAI-compatible for local models such as LM Studio (`http://localhost:1234/v1`) or Ollama (`http://localhost:11434/v1`). For Bedrock, leave the API key blank to use boto3 credentials from AWS_PROFILE, environment variables, SSO, or the instance/task role.
- **Profiles** — named runtime choices that select a provider and one model from that provider's configured model list. Runs can use the system default profile or a specific profile.

## Use

Landing page:  
![Screenshot](docs/images/sites.png)

Site test runs:  
![Screenshot](docs/images/testruns.png)

Site setup:  
![Screenshot](docs/images/sitesetup.png)

Site Map:  
![Screenshot](docs/images/sitemap.png)

Intelligence Log (populated by crawler and scanners):  
![Screenshot](docs/images/intelligence.png)

A.L.I.C.E chat:  
![Screenshot](docs/images/alice.png)

Dynamic scan in progress:  
![Screenshot](docs/images/agentstatus.png)

Task Graph used by the dynamic scan:  
![Screenshot](docs/images/taskgraph.png)

Attack Surface  
![Screenshot](docs/images/attacksurface.png)

Traffic log:  
![Screenshot](docs/images/trafficlog.png)

Findings  
![Screenshot](docs/images/findings.png)

API Setup  
![Screenshot](docs/images/apisetup.png)

Parsed API documentation  
![Screenshot](docs/images/apispecparsed.png)

SAST Scan-based Lead Detection  
![Screenshot](docs/images/sastleads.png)

OWASP Coverage for API Scanning  
![Screenshot](docs/images/apiworkprogram.png)

API Scan Findings  
![Screenshot](docs/images/apifindings.png)

## Recommended models

- Claude Sonnet 4.6 - Output token cap 70000. Doesn't seem to trigger refusals even without CVP.
- Minimax M3 - Output token cap 70000, turn off force tool call
- GLM 5.2 - Output token cap 70000, turn off force tool call
- GPT 5.4/5.5 work well too, but you need an account with Trusted Access or the scanner will terminate early/frequent refusals.
