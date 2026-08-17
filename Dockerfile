# syntax=docker/dockerfile:1

# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python backend + built SPA ----------
FROM python:3.11-slim AS backend
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime/system libraries:
#   build-essential  -> compiles any pip wheel that ships no binary wheel
#   libgomp1         -> OpenMP runtime used by onnxruntime
#   libgl1           -> libGL.so.1 used by OpenCV (OCR/rapidocr)
#   libglib2.0-0     -> GLib runtime used by OpenCV
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
# Built SPA is served by FastAPI from /app/static (single-port deployment).
COPY --from=frontend /build/dist /app/static
COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && mkdir -p /app/data

EXPOSE 8000

# Run a single uvicorn worker: the app keeps its task queue and keyword index
# in-process, so multiple workers would not share state.
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
