#!/bin/sh
set -e

case "$1" in
  web)
    # Applique les migrations de base de données avant de démarrer.
    alembic upgrade head
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers "${WEB_WORKERS:-2}" \
      --bind 0.0.0.0:8000 \
      --forwarded-allow-ips="*" \
      --access-logfile - \
      --timeout 60
    ;;
  worker)
    exec python -m app.jobs
    ;;
  *)
    exec "$@"
    ;;
esac
