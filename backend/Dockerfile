# Container image for the Pharma Signal Full DSP API (full_dsp_server.py).
# Builds from the backend/ directory:  docker build -t pharma-signal-api ./backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8090 \
    FULL_DSP_DB=/data/pharma_signal_dsp.db

WORKDIR /app

# Install only the lean Full DSP runtime dependencies for faster, smaller builds.
COPY requirements-full-dsp.txt .
RUN pip install --no-cache-dir -r requirements-full-dsp.txt

# Persisted SQLite location (mount a volume/disk here in production).
RUN mkdir -p /data

COPY full_dsp_server.py storage.py .

EXPOSE 8090

# Honor the host-provided $PORT (Render/Railway/Fly set this); default 8090 locally.
CMD ["sh", "-c", "uvicorn full_dsp_server:app --host 0.0.0.0 --port ${PORT:-8090}"]
