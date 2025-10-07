# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS runtime

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

ENV PYTHONPATH=/app/src \
    PATH=/app/.venv/bin:$PATH \
    PORT=8000

EXPOSE 8000

CMD ["/app/.venv/bin/python3", "-m", "uvicorn", "--app-dir", "src", "main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
