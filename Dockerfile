FROM ghcr.io/astral-sh/uv:0.11.11 AS uv
FROM python:3.11-slim-trixie@sha256:6f31d6e9ba2b0a787a3f81c37b004155b87b9efa1b771182bd550c1615745be5

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    MPLBACKEND=Agg \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app

ARG UV_EXTRA=test
COPY pyproject.toml uv.lock README.md docker-compose.yml ./
RUN uv sync --locked --extra test --extra "$UV_EXTRA" --no-dev --no-install-project

COPY src/ ./src/
COPY configs/ ./configs/
COPY tests/ ./tests/
COPY notebooks/ ./notebooks/
COPY .github/workflows/ci.yml ./.github/workflows/ci.yml
RUN uv sync --locked --extra test --extra "$UV_EXTRA" --no-dev \
    && uv pip uninstall --python /usr/local/bin/python pip setuptools wheel

CMD ["python", "-m", "energy_trading_pipeline.cli", "--config", "configs/experiment.yaml"]