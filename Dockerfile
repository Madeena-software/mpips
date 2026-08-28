# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv@sha256:95f2aa1fe59274951cfe9b0cbc7972e879ff1004bc8945d130a32eb0dbd85945 AS uv

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}" \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libglib2.0-0 \
        libgl1 \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=mpips-api-uv,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev --extra service --no-install-project

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
