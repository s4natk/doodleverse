FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    TF_CPP_MIN_LOG_LEVEL=2

WORKDIR /app

# Dependencies get their own layer, so a code change does not reinstall TensorFlow.
# The serve extra leaves out MLflow, matplotlib, and scikit-learn.
COPY pyproject.toml requirements.lock README.md NOTICE ./
RUN mkdir -p ml services/inference \
    && pip install --constraint requirements.lock ".[serve]"

COPY ml/doodleverse ./ml/doodleverse
COPY services/inference/doodleverse_api ./services/inference/doodleverse_api
RUN pip install --no-deps --force-reinstall . \
    && useradd --create-home --uid 10001 app

USER app
ENV DOODLEVERSE_MODEL_DIR=/models/doodleverse
EXPOSE 8000

CMD ["uvicorn", "doodleverse_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
