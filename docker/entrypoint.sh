#!/usr/bin/env sh
set -eu

case "${1:-api}" in
  api)
    exec uvicorn mpips.asgi:app \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers "${MPIPS_API_WORKERS:-1}"
    ;;
  worker)
    set -- celery -A mpips.worker worker \
      --loglevel="${MPIPS_WORKER_LOG_LEVEL:-info}" \
      --concurrency="${MPIPS_WORKER_CONCURRENCY:-1}" \
      --max-tasks-per-child="${MPIPS_WORKER_MAX_TASKS_PER_CHILD:-100}"

    if [ -n "${MPIPS_WORKER_QUEUES:-}" ]; then
      set -- "$@" --queues="${MPIPS_WORKER_QUEUES}"
    fi

    exec "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
