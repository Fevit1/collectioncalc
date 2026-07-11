FROM python:3.11-slim

# Unbuffered stdout/stderr — without this, print()/logging output sits in the
# container's pipe buffer until process exit, so Render's log viewer shows
# NOTHING while the service runs (L-2026-020; proven 2026-07-08 when a dying
# container flushed 10 days-old [Billing] lines with one timestamp).
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y libzbar0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 2 workers x 8 threads (gthread): the workload is I/O-bound (Anthropic API,
# Postgres), so threads keep /health, login, and collection loads answering
# while a 10-30s grading call runs — the old single sync worker serialized
# everything behind it. Sized to the Starter instance (512MB): measured RSS
# ~173MB/worker -> 2 workers ~= 350-380MB with headroom; memory fallback is
# 1 worker x 12 threads. DB ceiling: pool is per-process (db.py), so
# 2 workers x DB_POOL_MAX(8) = 16 pooled + overflow, vs ~100 usable.
CMD ["gunicorn", "wsgi:app", "--workers", "2", "--threads", "8", "--worker-class", "gthread", "--timeout", "300", "--bind", "0.0.0.0:10000"]
