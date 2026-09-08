FROM python:3.14-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
CMD ["/app/.venv/bin/attendance-mcp"]
