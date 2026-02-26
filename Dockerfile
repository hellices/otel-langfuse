FROM python:3.12-slim

WORKDIR /app

# uv 설치 (빠른 패키지 설치)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 먼저 복사 (캐시 활용)
COPY pyproject.toml .

# 의존성 설치
RUN uv pip install --system --no-cache .

# 소스 복사
COPY config.py .
COPY run_server.py .
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
