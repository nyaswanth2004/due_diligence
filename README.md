# VeritasIQ Due Diligence Copilot

An AI-powered financial due diligence copilot. Ingests financial documents (PDFs, scanned
PDFs, spreadsheets), retrieves relevant information with semantic search, and answers
questions with **grounded, evidence-cited** responses from the uploaded source documents.

## Architecture

```
Frontend (React/Next.js)  →  FastAPI backend  →  Multi-agent orchestration (LangGraph)
                                              →  Document ingestion (PDF/OCR/spreadsheet)
                                              →  Hybrid retrieval (embeddings + BM25)
                                              →  Local LLM reasoning (Ollama/vLLM)
                                              →  Postgres + pgvector, Redis, MinIO
```

## Project layout

```
backend/
  app/
    api/routes/       # HTTP endpoints (documents, search, health, auth, audit, reports)
    core/             # config, logging, security (PBKDF2 + JWT)
    db/               # SQLAlchemy engine/session
    models/           # ORM models (documents, chunks, users, audit logs, reports)
    ingestion/        # classifiers, extractors (PDF/OCR/spreadsheet), chunker, pipeline
    retrieval/        # embeddings, vector index (local/pgvector), BM25, RRF fusion, reranking
    analysis/         # financial extractor, ratios, multi-agent DD workflow
    evaluation/       # RAG evaluation dataset, metrics, harness
    schemas/          # Pydantic API schemas
    services/         # storage backends, task queue, audit, reporting
  scripts/            # create_user, evaluate CLI
  tests/
docker-compose.yml    # postgres+pgvector, redis, minio, ollama
frontend/             # React + Vite + TypeScript UI
```

## Retrieval pipeline

```
chunks ──► embed (bge-small / ollama / hash)
          ├─► vector index (LocalVectorIndex | pgvector)
          └─► BM25 keyword index
query ──► hybrid RRF fusion ──► cross-encoder rerank ──► provenance hits
```

Documents are indexed automatically after ingestion and de-indexed on delete.

## Quick start (local, no Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements-dev.txt
uvicorn app.main:app --reload     # http://127.0.0.1:8000
```

Health check: `GET /api/v1/health`
Run tests: `pytest`

### Auth, RBAC and audit

Roles: `admin` (everything + audit log), `analyst` (upload/delete documents,
generate reports), `viewer` (read-only search, Q&A, reports).

Create a user (run from `backend/`):

```bash
.venv\Scripts\python -m scripts.create_user --username admin --email admin@example.com --role admin --password "change-me"
```

All write endpoints log an audit trail (uploads, deletes, searches, questions,
report generation, logins) visible to admins at `/api/v1/audit`. Set a strong
`SECRET_KEY` in `.env` before any real deployment.

### RAG evaluation

```bash
.venv\Scripts\python -m scripts.evaluate --dataset golden.json --top-k 8
```

The golden dataset schema lives in `app/evaluation/dataset.py`. Metrics:
retrieval recall/precision@k, MRR, answer groundedness, citation accuracy, and
answer hit rate. See `tests/test_evaluation_e2e.py` for an end-to-end example.

### Frontend (dev)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to :8001)
npm run build      # typecheck + production bundle
```

The UI is a dark, premium enterprise dashboard (Tailwind + shadcn-style components,
Framer Motion, Recharts) with: Dashboard overview + charts, Projects (frontend
grouping of documents), Document Upload with drag & drop, AI Chat with verified
citations, Risk Analysis, Reports, Users (admin), Audit Logs (admin) and Settings.

Run the backend (above) first, then open the UI. If port 8000 is taken, start the
backend on 8001 and make sure `frontend/vite.config.ts` proxies `/api` to
`http://127.0.0.1:8001`.

## API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Authenticate (username + password) → JWT + user |
| GET | `/api/v1/auth/me` | Current user (role: admin / analyst / viewer) |
| POST | `/api/v1/documents` | Upload a document (PDF / scanned PDF / XLSX / CSV / image) — analyst/admin |
| GET | `/api/v1/documents` | List documents (status filter, pagination) |
| GET | `/api/v1/documents/{id}` | Document status + chunk count |
| GET | `/api/v1/documents/{id}/chunks` | Chunks with page/section provenance |
| DELETE | `/api/v1/documents/{id}` | Delete document, chunks, stored file, index — analyst/admin |
| GET | `/api/v1/search?q=...&top_k=&document_id=` | Hybrid semantic+keyword search with provenance |
| GET | `/api/v1/search/stats` | Index statistics (documents, chunks, backends) |
| POST | `/api/v1/qa` | Grounded Q&A with verified citations |
| POST | `/api/v1/reports/generate` | Run multi-agent due diligence workflow over documents — analyst/admin |
| GET | `/api/v1/reports` | List generated reports |
| GET | `/api/v1/reports/{id}` | Fetch a generated report |
| GET | `/api/v1/audit` | Audit log (admin only) |
| GET | `/api/v1/users` | List users (admin only, search filter) |
| POST | `/api/v1/users` | Create user (admin only) |
| PATCH | `/api/v1/users/{id}` | Update role / active status (admin only) |
| DELETE | `/api/v1/users/{id}` | Remove user (admin only, self-delete blocked) |

## Grounded Q&A pipeline

```
question ──► hybrid retrieval ──► evidence chunks
     ──► grounded prompt (answer ONLY from evidence) ──► local LLM (Ollama)
     ──► structured JSON ──► citation verification (drop hallucinated ids)
     ──► answer + citations + context + dropped-citation report
```

Every citation is checked against the provided context; hallucinated or stale
chunk ids are dropped and reported in `dropped_citations`.

## Due diligence report pipeline

```
documents ──► deterministic figure extraction (with chunk/page provenance)
     ──► ratio calculation (liquidity, solvency, profitability + risk levels)
     ──► multi-agent analysis: Analyzer, Risk, Compliance
     ──► Report agent (structured sections + optional LLM executive summary)
     ──► persisted report (JSON) retrievable via /reports/{id}
```

The extractor and ratio calculator are fully deterministic and provenance-tracked —
every figure and ratio points back to the exact source chunk. The LLM is used only
for the executive summary narrative and never to invent numbers.

## Production services (Docker)

```bash
docker compose up -d
```

Then set `DATABASE_URL`, `STORAGE_BACKEND=s3`, and `VECTOR_STORE_BACKEND=pgvector`
in `.env` (copy from `.env.example`).

## Roadmap

- [x] Phase 0 — Scaffold + config + DB foundation
- [x] Phase 1 — Ingestion pipeline (PDF text, OCR, spreadsheets) + chunking with provenance
- [x] Phase 2 — Embeddings + hybrid retrieval (vector + BM25 + RRF + cross-encoder rerank)
- [x] Phase 3 — Local LLM grounded Q&A with verified citations
- [x] Phase 4 — Multi-agent due diligence report generation (deterministic, provenance-tracked)
- [x] Phase 4b — React frontend (upload, docs, search, QA chat, report dashboard)
- [x] Phase 5 — Auth/RBAC (JWT), audit logging, RAG evaluation harness
- [ ] Phase 6 — CI, deployment hardening, multi-tenant data isolation
