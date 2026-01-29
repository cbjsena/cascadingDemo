# 1. Base Image (Python 3.11 사용)
FROM python:3.11-slim

# 2. 환경 변수 설정 (버퍼링 비활성화, .pyc 파일 생성 방지)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 시스템 의존성 패키지 설치 (PostgreSQL 연동 등을 위해 필요)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Python 패키지 설치
# 캐싱을 위해 requirements.txt만 먼저 복사하여 설치
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 6. 프로젝트 코드 복사
COPY . /app/