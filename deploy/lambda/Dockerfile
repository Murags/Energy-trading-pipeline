# Container image for the scheduled day-ahead forecast Lambda.
#
# A container is required rather than a zip: xgboost, pandas and pyarrow exceed
# Lambda's 250 MB unzipped layer limit. The image holds code and configuration
# only; data, models and forecasts live in S3, and credentials come from the
# function's IAM role at runtime.
FROM ghcr.io/astral-sh/uv:0.11.11 AS uv

# Amazon Linux 2023 (glibc 2.34): manylinux_2_28 wheels exist for xgboost and
# pyarrow here, so nothing is compiled from source during the build.
FROM public.ecr.aws/lambda/python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    MPLBACKEND=Agg

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR ${LAMBDA_TASK_ROOT}

# Install into the task root, never into /var/lang: the base image's runtime
# interface client lives there and must stay importable. Requirements are
# exported from the committed lockfile rather than maintained separately.
COPY pyproject.toml uv.lock README.md ./
RUN uv export --locked --no-dev --no-emit-project --extra aws \
        --format requirements-txt -o /tmp/requirements.txt \
    && uv pip install --target ${LAMBDA_TASK_ROOT} -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY src/energy_trading_pipeline/ ./energy_trading_pipeline/
COPY configs/ ./configs/

# The forecast reads and writes the single S3 prefix supplied at deploy time.
ENV ETP_CONFIG=configs/experiment_day_ahead_pvwind.yaml \
    ETP_MODEL_PARAMS=configs/model_params.yaml

CMD ["energy_trading_pipeline.forecasting.lambda_handler.handler"]
