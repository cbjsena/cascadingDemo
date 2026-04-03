#!/bin/bash
# 에러 발생 시 스크립트 중단
set -e

echo "[Entrypoint] Starting local development tasks..."

# DB/Redis 준비 대기 (podman-compose depends_on은 시작 순서만 보장)
python - <<'PY'
import os
import socket
import time


def wait_for(host, port, name, timeout=60):
	deadline = time.time() + timeout
	while time.time() < deadline:
		try:
			with socket.create_connection((host, port), timeout=2):
				print(f"[Entrypoint] {name} is ready: {host}:{port}")
				return
		except OSError:
			time.sleep(1)
	raise SystemExit(f"[Entrypoint] Timeout waiting for {name}: {host}:{port}")


wait_for(os.getenv("DB_HOST", "db"), int(os.getenv("DB_PORT", "5432")), "PostgreSQL")
wait_for(os.getenv("REDIS_HOST", "redis"), int(os.getenv("REDIS_PORT", "6379")), "Redis")
PY

# 기본값은 0(개발 속도 우선). 필요 시 RUN_MIGRATIONS_ON_START=1로 실행.
if [ "${RUN_MIGRATIONS_ON_START:-0}" = "1" ]; then
  echo "[Entrypoint] Applying database migrations..."
  python manage.py migrate --noinput
else
  echo "[Entrypoint] Skipping migrations (RUN_MIGRATIONS_ON_START=${RUN_MIGRATIONS_ON_START:-0})"
fi

# 2. Execute the development server
# Podman 환경에서 autoreload 부모 프로세스 종료로 컨테이너가 내려가는 현상을 피합니다.
exec python manage.py runserver 0.0.0.0:8000 --noreload
