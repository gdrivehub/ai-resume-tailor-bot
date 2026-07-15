# =====================================================================
# AI Resume Tailor Bot — Production Dockerfile
# Multi-stage build for a small, fast, optimized image.
# =====================================================================

# ---------- Stage 1: Build dependencies ----------
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps needed to build some Python wheels (PyMuPDF, reportlab, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------- Stage 2: Runtime image ----------
FROM python:3.12-slim

WORKDIR /app

# Only the runtime shared libs needed by PyMuPDF/Pillow/reportlab (no compilers),
# plus gosu for safely dropping root privileges after fixing volume ownership.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r botuser && useradd -r -g botuser -m -d /home/botuser botuser

# Bring in the pre-built Python packages from the builder stage
COPY --from=builder /root/.local /home/botuser/.local

ENV PATH=/home/botuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY . .
COPY entrypoint.sh /entrypoint.sh

RUN mkdir -p /app/temp /app/logs \
    && chown -R botuser:botuser /app /home/botuser \
    && chmod +x /entrypoint.sh

# NOTE: we intentionally stay as root here. entrypoint.sh fixes ownership
# of any bind-mounted volumes (which Docker creates as root on the host)
# at container start, then execs the app as the unprivileged botuser via
# gosu. Do NOT add `USER botuser` here or bind-mounted ./logs will break.

# Health check hits the built-in aiohttp server (see app/health_server.py)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('HEALTH_SERVER_PORT','8080') + '/health', timeout=3)" || exit 1

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py"]
