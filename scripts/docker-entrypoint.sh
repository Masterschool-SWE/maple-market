#!/bin/sh
set -e

role="${1:-api}"

case "$role" in
  api)
    mkdir -p /data/chroma
    marker=/data/chroma/.ingested
    if [ ! -f "$marker" ]; then
      echo "Ingesting policies into Chroma (first boot)..."
      python -m app.agent.rag.ingest
      touch "$marker"
    fi
    exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 1
    ;;
  streamlit)
    exec streamlit run frontend/streamlit_app.py \
      --server.address 0.0.0.0 \
      --server.port 8501 \
      --server.headless true \
      --browser.gatherUsageStats false
    ;;
  *)
    exec "$@"
    ;;
esac
