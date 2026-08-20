# syntax=docker/dockerfile:1.7

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}" \
    PORT=8000

COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libglib2.0-0 \
        libgl1 \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra service --no-install-project

COPY mpips ./mpips
COPY docker/entrypoint.sh /usr/local/bin/mpips-entrypoint

RUN chmod +x /usr/local/bin/mpips-entrypoint \
    && groupadd --system --gid 10001 mpips \
    && useradd --system --uid 10001 --gid mpips --home-dir /app mpips \
    && chown -R mpips:mpips /app

USER mpips

EXPOSE 8000

ENTRYPOINT ["tini", "--", "mpips-entrypoint"]
CMD ["api"]
