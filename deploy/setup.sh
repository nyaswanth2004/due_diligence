#!/usr/bin/env bash
# One-shot provisioning for the VeritasIQ backend + Ollama on a fresh Ubuntu VPS.
#
# Usage:
#   sudo bash setup.sh [app_dir] [git_url] [frontend_origin]
#
#   app_dir         install location, default /opt/veritasiq
#   git_url         repo to clone, default https://github.com/nyaswanth2004/due_diligence.git
#   frontend_origin Vercel URL the browser will call from, e.g. https://your-app.vercel.app
set -euo pipefail

APP_DIR="${1:-/opt/veritasiq}"
GIT_URL="${2:-https://github.com/nyaswanth2004/due_diligence.git}"
FRONTEND_ORIGIN="${3:-https://your-app.vercel.app}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run with sudo (or as root)." >&2
  exit 1
fi

echo ">> apt packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl python3 python3-venv python3-pip git

echo ">> Ollama (local LLM server)"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
systemctl enable ollama --now || true
# Pull the model used by the app (backend .env sets LLM_MODEL=qwen2.5:3b)
ollama pull qwen2.5:3b

echo ">> app service user"
id -u veritasiq >/dev/null 2>&1 || useradd --create-home --shell /bin/bash veritasiq

echo ">> clone / update app"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$GIT_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi
chown -R veritasiq:veritasiq "$APP_DIR"

echo ">> python venv"
su veritasiq -s /bin/bash -c "python3 -m venv '$APP_DIR/backend/venv'"
su veritasiq -s /bin/bash -c "'$APP_DIR/backend/venv/bin/pip' install --upgrade pip wheel setuptools"
su veritasiq -s /bin/bash -c "'$APP_DIR/backend/venv/bin/pip' install -r '$APP_DIR/backend/requirements.txt'"

echo ">> .env (skipped if backend/.env already exists)"
if [ ! -f "$APP_DIR/backend/.env" ]; then
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  cat > "$APP_DIR/backend/.env" <<EOF
DEBUG=false
SECRET_KEY=$SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=60

DATABASE_URL=sqlite:///./veritasiq.db
REDIS_URL=redis://localhost:6379/0

STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=storage/documents
VECTOR_INDEX_PATH=storage/vectors

OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:3b
LLM_BACKEND=ollama
OLLAMA_KEEP_ALIVE=10m

EMBEDDING_BACKEND=sentence_transformers
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

VECTOR_STORE_BACKEND=local
VECTOR_DIM=384

RETRIEVAL_TOP_K=6
RETRIEVAL_FUSION_K=60
KEYWORD_ENABLED=true
RERANKER_ENABLED=true

CORS_ORIGINS=["$FRONTEND_ORIGIN","http://localhost:5173","http://localhost:3000"]
EOF
  chown veritasiq:veritasiq "$APP_DIR/backend/.env"
fi

mkdir -p "$APP_DIR/backend/storage/documents" "$APP_DIR/backend/storage/vectors"
chown -R veritasiq:veritasiq "$APP_DIR/backend/storage"

echo ">> systemd service"
cp "$APP_DIR/deploy/veritasiq.service" /etc/systemd/system/veritasiq.service
systemctl daemon-reload
systemctl enable veritasiq --now

echo ">> smoke check"
sleep 2
if command -v curl >/dev/null 2>&1; then
  curl -fsS "http://127.0.0.1:8000/api/v1/health" && echo " [ok]" || echo "WARN: health check failed (see: journalctl -u veritasiq -n 50)"
fi

echo
echo "DONE."
echo "  1. Set CORS_ORIGINS to your real Vercel URL if different from $FRONTEND_ORIGIN"
echo "     (edit $APP_DIR/backend/.env then: systemctl restart veritasiq)"
echo "  2. If you want to keep existing ingested docs, stop the service, copy veritasiq.db + storage/"
echo "     from the dev machine into $APP_DIR/backend/, then start it again."
echo "  3. Optional: front your API with nginx + a domain so Vercel calls https (mixed-content rule)."
