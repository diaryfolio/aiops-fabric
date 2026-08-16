FROM python:3.12.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN groupadd --gid 10001 viewsense \
    && useradd --uid 10001 --gid viewsense --no-create-home --shell /usr/sbin/nologin viewsense

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --requirement /app/requirements.txt

COPY src /app/src

USER 10001:10001

ENTRYPOINT ["python", "-m", "viewsense_common.serve"]

FROM runtime AS test
USER root
COPY requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir --requirement /app/requirements-dev.txt
COPY tests /app/tests
COPY config /app/config
COPY fabric /app/fabric
COPY contracts /app/contracts
COPY deploy /app/deploy
COPY docs/design/high-level /app/docs/design/high-level
COPY pyproject.toml /app/pyproject.toml
USER 10001:10001
ENTRYPOINT []
CMD ["pytest", "-q", "-p", "no:cacheprovider"]
