#!/usr/bin/env sh
set -e

# Persisted app data (SQLite DB, uploaded documents, vector index, HF model
# cache) lives on the app-data volume mounted at /app/data.
mkdir -p /app/data

# Seed the initial admin user when requested. Idempotent: if the user already
# exists the script exits 1 and we continue normally.
if [ "$ADMIN_BOOTSTRAP" = "true" ]; then
  if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "[entrypoint] bootstrapping admin user '$ADMIN_USERNAME'"
    python scripts/create_user.py \
      --username "$ADMIN_USERNAME" \
      --email "${ADMIN_EMAIL:-admin@example.com}" \
      --role "${ADMIN_ROLE:-admin}" \
      --password "$ADMIN_PASSWORD" \
      || echo "[entrypoint] admin user already exists (skipping)"
  else
    echo "[entrypoint] ADMIN_BOOTSTRAP=true but ADMIN_USERNAME/ADMIN_PASSWORD are empty; skipping"
  fi
fi

exec "$@"
