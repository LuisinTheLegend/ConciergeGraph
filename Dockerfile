# Grafo Concierge — Production Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir --no-deps .

# Final runtime image (non-root)
FROM python:3.12-slim

WORKDIR /app

RUN groupadd --gid 10001 --system concierge && \
    useradd --uid 10001 --gid 10001 --system --create-home --home-dir /home/concierge --shell /usr/sbin/nologin concierge && \
    mkdir -p /app/data /home/concierge/.cache && \
    chown -R 10001:10001 /app /home/concierge

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    HOME=/home/concierge \
    GRAFO_HOST=0.0.0.0 \
    GRAFO_PORT=8000 \
    GRAFO_TRANSPORT=sse \
    GRAFO_DB_PATH=/app/data/concierge.db \
    GRAFO_CHROMA_PATH=/app/data/chroma \
    PYTHONUNBUFFERED=1

USER concierge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; port = os.environ.get('GRAFO_PORT', '8000'); resp = urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=5); raise SystemExit(0 if resp.status == 200 else 1)"]

CMD ["concierge-mcp"]
