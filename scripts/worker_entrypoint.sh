#!/bin/bash
set -e

echo "[Worker Entrypoint] Waiting for dependencies..."

python - <<'PY'
import os
import socket
import time


def wait_for(host, port, name, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"[Worker Entrypoint] {name} is ready: {host}:{port}")
                return
        except OSError:
            time.sleep(1)
    raise SystemExit(f"[Worker Entrypoint] Timeout waiting for {name}: {host}:{port}")


wait_for(os.getenv("DB_HOST", "db"), int(os.getenv("DB_PORT", "5432")), "PostgreSQL")
wait_for(os.getenv("REDIS_HOST", "redis"), int(os.getenv("REDIS_PORT", "6379")), "Redis")
PY

echo "[Worker Entrypoint] Starting Celery worker..."
exec celery -A config worker -l info --concurrency=${CELERY_WORKER_CONCURRENCY:-2}

