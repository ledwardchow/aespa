# Playwright base image ships chromium + all system deps already.
FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Refresh the base image packages, remove browser multimedia plugins AESPA does
# not use, and omit system Python packaging tools that are unnecessary at
# runtime. Keep the apt index out of the final layer.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get purge -y gstreamer1.0-plugins-bad libgstreamer-plugins-bad1.0-0 \
    && apt-get autoremove -y \
    && uv pip uninstall --system pip setuptools msgpack \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# Attribution for the bundled MIT/BSD/Apache/MPL deps (runtime set only).
RUN uv run --no-dev python scripts/generate_third_party_licenses.py THIRD_PARTY_LICENSES.txt \
    && rm -rf /root/.cache

# DB + uploads live under /data so they're writable and can be mounted to persist.
RUN mkdir -p /data && chmod 777 /data
ENV AESPA_HOST=0.0.0.0 AESPA_PORT=8000 \
    AESPA_DATABASE_URL=sqlite:////data/aespa.db \
    AESPA_DATA_DIR=/data/aespa_data
VOLUME /data
EXPOSE 8000
CMD ["uv", "run", "aespa"]
