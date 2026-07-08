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

CMD ["gunicorn", "wsgi:app", "--timeout", "300", "--bind", "0.0.0.0:10000"]
