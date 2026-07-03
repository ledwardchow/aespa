# Playwright base image ships chromium + all system deps already.
FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# Attribution for the bundled MIT/BSD/Apache/MPL deps (runtime set only).
RUN uv run --no-dev python scripts/generate_third_party_licenses.py THIRD_PARTY_LICENSES.txt

# DB + uploads live under /data so they're writable and can be mounted to persist.
RUN mkdir -p /data && chmod 777 /data
ENV AESPA_HOST=0.0.0.0 AESPA_PORT=8000 \
    AESPA_DATABASE_URL=sqlite:////data/aespa.db \
    AESPA_DATA_DIR=/data/aespa_data
VOLUME /data
EXPOSE 8000
CMD ["uv", "run", "aespa"]
