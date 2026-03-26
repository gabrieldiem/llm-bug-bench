################################
# Stage 1: Builder
################################
FROM python:3.13-slim-trixie AS builder

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false

RUN (poetry check --lock || poetry lock) && poetry install --no-root --no-ansi

################################
# Stage 2: Runtime
################################
FROM python:3.13-slim-trixie AS runner

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY bizwatcher/ bizwatcher/
COPY tests/ tests/

RUN mkdir -p /app/results
VOLUME /app/results

ENTRYPOINT ["python", "-m", "bizwatcher"]
CMD ["--help"]
