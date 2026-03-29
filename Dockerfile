################################
# Stage 1: Builder
################################
FROM python:3.13-slim-trixie AS builder

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false

RUN (poetry check --lock || poetry lock) && poetry install --without dev --no-root --no-ansi

################################
# Stage 2: Runtime
################################
FROM python:3.13-slim-trixie AS runner

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN mkdir -p /app/results

COPY src/ src/
COPY benchmarks/ benchmarks/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "-m", "src", "--port", "8080"]
