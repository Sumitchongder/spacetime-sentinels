# Reproducible environment: docker build -t sentinels . && docker run --rm -it sentinels make reproduce
FROM python:3.12-slim
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends make && rm -rf /var/lib/apt/lists/*
COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
RUN pip install -r requirements.txt && pip install -e ".[dev]"
COPY . .
CMD ["make", "test"]
