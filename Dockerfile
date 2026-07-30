FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:$PATH"

COPY backend/pyproject.toml backend/uv.lock /app/backend/
RUN uv sync --project /app/backend --frozen --no-dev

COPY backend/ /app/backend/
COPY sql/ /app/sql/
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
RUN mkdir -p /app/工作总结 /app/output

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/v1/health')"

CMD ["uvicorn", "--app-dir", "/app/backend", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
