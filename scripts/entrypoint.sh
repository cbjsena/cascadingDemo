#!/bin/bash

# 에러 발생 시 스크립트 중단
set -e

echo "🚀 [Entrypoint] Starting deployment tasks..."

# 1. DB Migration (선택 사항: 배포 시마다 자동 적용)
echo "📦 Applying database migrations..."
python manage.py migrate --noinput

# 2. Collect Static Files
# Django가 정적 파일을 /app/staticfiles로 모아주면, Nginx가 이를 서빙합니다.
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

# 3. Start Gunicorn
echo "🔥 Starting Gunicorn..."
# workers: (CPU 코어 수 * 2) + 1 권장
# bind: 0.0.0.0:8000 (컨테이너 내부 포트)
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --log-level=info