# SpendSense

SpendSense is a personal finance workspace for tracking income and expenses, planning budgets, and understanding spending patterns. The repository contains a Next.js app and a FastAPI service with SQLAlchemy persistence, JWT authentication, category rules, an explainable anomaly baseline, a local natural-language parser, and a conservative spending forecast.

## Run locally

Requirements: Python 3.11+, Node.js 20+, and (for the Compose setup) Docker Desktop.

### Quick start with Docker

1. Copy `.env.example` to `.env` and set a long random `SECRET_KEY`.
2. Run `docker compose up --build` from the repository root.
3. Open [http://localhost:3000](http://localhost:3000); the API docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

### Run services separately

For the API, use SQLite by default or point `DATABASE_URL` to PostgreSQL. From `backend/`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

For the web app, from `frontend/`:

```bash
pnpm install
pnpm dev
```

Set `NEXT_PUBLIC_API_URL` if the API is not at `http://localhost:8000`. The browser persists the JWT in local storage; logout clears it. For deployment, use HTTPS, a strong secret, secure cookie based auth, restrictive CORS, and managed database backups.

## Database and migrations

`DATABASE_URL` is read by SQLAlchemy. The API creates tables on startup for a frictionless SQLite start. For a managed database, run `cd backend && alembic upgrade head`. The initial migration creates users, transactions, budgets, and insight records with user scoped indexes and constraints.

Optional demo data: from `backend/`, run `python -m app.seed`, then sign in with `demo@spendsense.local` and `demo-password`. Use this only for local development; change or remove the demo account before deployment.

## Features

- Account creation, sign in, sign out, bcrypt password hashing, and authenticated user scoped data access.
- Transaction creation, editing, deletion, search, category/type/date filters, sorting, and CSV export.
- PDF bank statement import with a transaction preview, estimated categories, duplicate detection, and explicit confirmation before saving. Supports Google Pay transaction statement exports and FamX statements; other text-based statements are imported when their rows clearly identify dates and debit/credit direction. PDFs up to 12 MB / 100 pages are supported; scanned PDFs that require OCR are not supported yet. Uploaded PDFs are parsed in memory and not retained.
- Monthly budgets by category or for all categories, calculated from expense records and colored warnings at 75%, 90%, and 100%.
- Backend sourced overview totals, daily spending, category breakdown, recent transactions, and monthly analytics.
- Local deterministic natural language entry. The result remains editable and requires user confirmation before it is saved.
- Explainable category keyword classification with a low confidence `Other` fallback.
- Data based category insights and an outlier check; outlier means unusual compared with recorded expenses, not fraudulent.
- Three month moving average forecast with historical variability, hidden until there are at least three months of data.

## API

Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.

Transactions: `GET/POST /transactions`, `GET/PUT/DELETE /transactions/{id}`.

Statement import: `POST /transactions/import-pdf/preview` (multipart PDF upload), then `POST /transactions/import-pdf/commit` (reviewed transaction JSON).

Budgets: `GET/POST /budgets`, `PUT/DELETE /budgets/{id}`.

Analytics: `GET /analytics/summary`, `/analytics/categories`, `/analytics/monthly-trends`.

AI baselines: `POST /ai/parse-transaction`, `GET /ai/insights`, `/ai/anomalies`, `/ai/forecast`.

## AI limits

The app does not require an external AI provider. Natural language extraction uses a deterministic parser, categorization uses editable rules, insights use recorded amounts, anomaly detection uses an IQR and Z-score baseline, and forecasts use a three month moving average. LLM provider settings are reserved in `.env.example`; no provider is wired in this initial local release. These heuristics can miss context and are not financial advice.

An optional scikit-learn dependency set is available in `backend/requirements-ml.txt` for future classifier experiments; the current core service does not depend on it.

## Tests

From `backend/`, install requirements and run `pytest`. Tests cover classification confidence, parser confirmation data, analytics, insight evidence, authentication, CRUD creation, and cross user isolation.
