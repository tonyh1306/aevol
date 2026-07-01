FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY sdk/ ./sdk/
RUN uv pip install --system -e ./sdk

COPY worker/pyproject.toml .
RUN uv pip install --system -e .

COPY worker/app/ ./app/

CMD ["python", "-m", "app.main"]
