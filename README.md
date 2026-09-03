# TripSplit Ledger

[![CI](https://github.com/GGGUJINGGG/tripsplit-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/GGGUJINGGG/tripsplit-ledger/actions/workflows/ci.yml)

**Live demo:** [tripsplit-ledger.vercel.app](https://tripsplit-ledger.vercel.app) — register your own account to try it (see [Deployment](#deployment) for how the frontend/backend are hosted).

After a group trip, I used Splitwise to settle expenses with friends and ran into a few frustrations: the free tier limits how many expenses you can log per day, and it doesn't show a full spending breakdown for the trip — only who owes whom. I wanted to see total spending by category, by day, and per person, not just the final settlement numbers.

That gap was the starting point. As I logged our actual trip expenses into an early version of this app, I kept noticing other things I wanted — filtering, expense types, CSV export, a per-person spending summary — and added them one by one. TripSplit Ledger is the result: a personal expense tracker built around how I actually think about group travel spending.

The current implementation uses a React/Vite frontend, a FastAPI backend, and PostgreSQL persistence through SQLAlchemy 2.0. Database schema changes are managed with Alembic, and backend integration tests run against a separate PostgreSQL test database.

## Screenshots

![Trip Detail](screenshots/trip-detail.png)

![Expense Ledger](screenshots/expense-ledger.png)

## Features

**Trip management**
- Create trips with date ranges
- Per-trip dashboard showing total spending, shared spending, and personal spending at a glance
- Invite another registered user to a trip by email (owner-only)
- Trip renaming and deletion, owner-only and enforced by the API

**Expenses**
- Add, edit, and delete expenses with title, amount, category, date, payer, currency, and an optional note
- Shared vs. personal expense types — personal expenses count toward your own spending but are excluded from settlement calculations
- Flexible split: choose which participants share each expense
- Expense shares calculated in integer cents to avoid floating-point rounding errors

**Filtering and search**
- Filter the expense ledger by category, payer, type (shared/personal), and date range
- Free-text search by title or note
- Sort by newest, oldest, or amount

**Spending summary**
- Per-participant breakdown: total paid, shared responsibility, personal spending, and net balance
- Category summary table showing shared vs. personal totals across all 7 categories
- Daily spending timeline

**Settlements**
- Simplified payment plan that minimizes the number of transactions
- Settlement amounts consistent with per-participant net balances

**Export**
- CSV export of the full expense ledger with all filters applied

## Known Limitations

- **No multi-currency settlement** — expenses can be tagged with a currency, but settlement calculations are hidden when a trip mixes currencies. Exchange-rate conversion is not yet implemented. The backend's `/dashboard` totals (spending by category/day, paid/owed per person) are also not currency-segmented — they sum raw amounts across currencies, so those numbers aren't meaningful for a mixed-currency trip. The frontend works around this by computing its own per-currency breakdowns instead of relying on those backend fields.
- **No frontend UI for inviting members beyond the invite-by-email form** — the API also enforces owner-only rules here, but there's no bulk invite or member-management screen beyond that one form.
- **Expense Ledger pagination is client-side** — `GET /trips/{id}/expenses` supports real `limit`/`offset` query params, but the frontend still loads a trip's full expense list in one request (it's embedded in `GET /trips/{id}`, which the dashboard and CSV export also depend on) and paginates 25 rows at a time in the browser. That keeps the table usable at moderate scale but doesn't reduce what's transferred over the network — a trip with tens of thousands of expenses would need the frontend to fetch pages from the paginated endpoint directly instead.
- **Password reset emails aren't actually emailed** — no transactional email provider (SES, Resend, SendGrid, ...) is configured, so `POST /auth/forgot-password` logs the reset link server-side instead of sending it. The rest of the flow (single-use, hashed, time-limited tokens; forced logout of other sessions on reset) is real and tested; only the delivery mechanism is a stand-in.
- **Rate limiting is in-memory and single-instance** — `/auth/login`, `/auth/register`, and `/auth/forgot-password` are rate-limited per IP, but the counters live in the API process's memory. Fine for this app's one Railway container; a multi-instance deployment would need a shared store (Redis, etc.) instead.
- **Error monitoring (Sentry) is wired up but not turned on** — the backend logs structured JSON for every request (method, path, status, duration) by default, but exception tracking via Sentry only activates if `SENTRY_DSN` is set (see `backend/.env.example`); no Sentry project is configured for this deployment.

## Planned

- Exchange-rate conversion to enable settlements across mixed-currency trips
- Budget tracking per trip or per category

## Architecture

```mermaid
flowchart LR
    subgraph Client["Browser"]
        FE["React 19 + Vite SPA<br/>access + refresh JWT in localStorage"]
    end

    subgraph Server["FastAPI backend"]
        Auth["/api/auth<br/>register · login · refresh · logout ·<br/>forgot/reset-password · me"]
        Trips["/api/trips<br/>trips · participants · expenses"]
        Dash["/api/trips/{id}/dashboard"]
        Settle["/api/trips/{id}/settlements"]
    end

    DB[("PostgreSQL<br/>SQLAlchemy 2.0 + Alembic")]

    FE -- "HTTPS, Bearer JWT" --> Auth
    FE -- "HTTPS, Bearer JWT" --> Trips
    FE -- "HTTPS, Bearer JWT" --> Dash
    FE -- "HTTPS, Bearer JWT" --> Settle
    Auth --> DB
    Trips --> DB
    Dash --> DB
    Settle --> DB
```

Every route except `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/forgot-password`, and `/api/auth/reset-password` requires a valid JWT and checks that the requesting user is a member of the trip being accessed; only the trip owner can rename/delete a trip or invite new members. `/dashboard` and `/settlements` derive their numbers from the same expense/share tables — the frontend consumes those endpoints directly rather than recomputing balances client-side.

Access tokens expire after 30 minutes; the frontend transparently exchanges the (longer-lived, rotating) refresh token for a new one on a 401 instead of forcing a re-login. `/auth/login`, `/auth/register`, and `/auth/forgot-password` are rate-limited per IP.

### Database schema

```mermaid
erDiagram
    USERS ||--o{ TRIP_MEMBERS : "has (nullable once removed)"
    TRIPS ||--o{ TRIP_MEMBERS : "has"
    TRIPS ||--o{ EXPENSES : "has"
    TRIP_MEMBERS ||--o{ EXPENSES : "pays for"
    EXPENSES ||--o{ EXPENSE_SHARES : "split into"
    TRIP_MEMBERS ||--o{ EXPENSE_SHARES : "owes"

    USERS {
        uuid id PK
        string email UK
        string password_hash
        string display_name
    }
    TRIPS {
        uuid id PK
        string name
        date start_date
        date end_date
    }
    TRIP_MEMBERS {
        uuid id PK
        uuid trip_id FK
        uuid user_id FK "nullable, SET NULL on user delete"
        string display_name
        enum role "owner | member"
    }
    EXPENSES {
        uuid id PK
        uuid trip_id FK
        uuid paid_by_id FK
        string title
        int amount_cents
        enum expense_type "shared | personal"
        enum category
        date date
        string currency
        text note
    }
    EXPENSE_SHARES {
        uuid id PK
        uuid expense_id FK
        uuid member_id FK
        int amount_cents
    }
```

`trip_members` is the join between a `User` account and a `Trip` — its `user_id` is nullable so a guest can be added by name only (no account) and a trip owner can't accidentally lock themselves out by deleting their own user record elsewhere. `expenses.amount_cents` and `expense_shares.amount_cents` are integers (not floats) specifically to avoid floating-point rounding drift when splitting a bill; see [Calculation Logic](#calculation-logic).

## Backend Setup

Requirements:

- Python 3.11+
- Docker Desktop
- Docker Compose

Start PostgreSQL from the project root:

```bash
docker compose up -d db
```

Set up and start the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The API will run at:

```text
http://localhost:8000
```

Health check:

```text
GET /api/health
```

Interactive API docs:

```text
http://localhost:8000/docs
```

## Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at:

```text
http://localhost:5173
```

By default, the frontend calls the backend at `http://localhost:8000/api`.

## Deployment

The backend runs as a container (`backend/Dockerfile`) on [Railway](https://railway.app), and the frontend is a static build on [Vercel](https://vercel.com). Both are connected to this repo's `main` branch — pushing redeploys them automatically.

- **Frontend:** https://tripsplit-ledger.vercel.app
- **Backend health check:** the Railway service's `/api/health` endpoint

The steps below are what was actually used to stand this up, kept here so the deployment is reproducible.

### Backend on Railway

1. Sign up / log in at railway.app with your GitHub account.
2. **New Project → Deploy from GitHub repo** → select this repo.
3. On the service Railway creates, open **Settings → Root Directory** and set it to `backend` (this is a monorepo — Railway needs to know which subfolder has the Dockerfile).
4. In the same project, click **New → Database → Add PostgreSQL**.
5. On the backend service's **Variables** tab, add:
   - `DATABASE_URL` → reference the Postgres plugin's connection string (Railway lets you pick `${{Postgres.DATABASE_URL}}` from a dropdown — no need to type it by hand; a bare `postgresql://` URL is fine, the app upgrades it to the `psycopg` driver itself)
   - `JWT_SECRET_KEY` → a random secret, e.g. generate one locally with `python3 -c "import secrets; print(secrets.token_hex(32))"`
   - `CORS_ORIGINS` → your Vercel URL once you have it (see below); use `http://localhost:5173` as a placeholder until then
6. Railway builds the Dockerfile and deploys. Under **Settings → Networking**, click **Generate Domain** to get a public URL like `https://your-app.up.railway.app`.
7. Verify it: `curl https://your-app.up.railway.app/api/health` should return `{"status":"ok"}`. The Dockerfile runs `alembic upgrade head` on every start, so the schema is created automatically on first boot.

### Frontend on Vercel

1. Sign up / log in at vercel.com with your GitHub account.
2. **Add New → Project** → import this repo.
3. Set **Root Directory** to `frontend` (Vite framework preset is auto-detected).
4. Add an environment variable **before** the first deploy: `VITE_API_BASE_URL` = `https://your-app.up.railway.app/api` (Vite bakes this into the static build at build time — changing it later requires a redeploy, not just a restart).
5. Deploy. Vercel gives you a URL like `https://your-app.vercel.app`. `vercel.json` in this repo rewrites all paths to `index.html` so refreshing a client-side route (e.g. `/trips/abc123`) doesn't 404.

### Wire them together

Go back to the Railway backend's `CORS_ORIGINS` variable and set it to your actual Vercel URL (e.g. `https://your-app.vercel.app`), then redeploy the backend service so the browser is allowed to call it.

### Smoke test

Once both are live, walk through this once end-to-end:

- [ ] Register an account
- [ ] Create a trip
- [ ] Add a participant
- [ ] Add, edit, and delete an expense
- [ ] View the dashboard and category breakdown
- [ ] View the settlement summary
- [ ] Log out, log back in
- [ ] Confirm the trip and its data are still there
- [ ] Register a second account and confirm it can't see the first account's trips

## API Overview

Authentication:

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
POST /api/auth/forgot-password
POST /api/auth/reset-password
GET  /api/auth/me
```

Trips:

```text
GET    /api/trips
POST   /api/trips
GET    /api/trips/{trip_id}
PUT    /api/trips/{trip_id}
DELETE /api/trips/{trip_id}
```

Participants:

```text
GET    /api/trips/{trip_id}/participants
POST   /api/trips/{trip_id}/participants
POST   /api/trips/{trip_id}/participants/invite
DELETE /api/trips/{trip_id}/participants/{participant_id}
```

Expenses:

```text
GET    /api/trips/{trip_id}/expenses?limit=&offset=   # limit 1-200, default 50
POST   /api/trips/{trip_id}/expenses
GET    /api/trips/{trip_id}/expenses/{expense_id}
PUT    /api/trips/{trip_id}/expenses/{expense_id}
DELETE /api/trips/{trip_id}/expenses/{expense_id}
```

Dashboard and settlements:

```text
GET /api/trips/{trip_id}/dashboard
GET /api/trips/{trip_id}/settlements
```

## Calculation Logic

The backend calculates:

- Total trip spending
- Spending by category (shared and personal separately)
- Spending by day
- Amount paid by each person
- Amount owed by each person
- Net balances
- Simplified settlement payments

Expense shares are calculated in cents to avoid floating point drift.

## Example Expense Payload

```json
{
  "title": "Airport dinner",
  "amount": 84.5,
  "paid_by": "participant-id",
  "split_among": ["participant-id", "another-participant-id"],
  "category": "food",
  "date": "2026-07-01",
  "currency": "USD",
  "note": "First meal of the trip"
}
```

Supported categories:

```text
food, hotel, transportation, gas, tickets, shopping, other
```

## Tests

Backend integration tests use a separate PostgreSQL database so development data is never modified.

Create and migrate the test database once:

```bash
docker compose exec db createdb -U tripsplit tripsplit_test

cd backend
source .venv/bin/activate
DATABASE_URL=postgresql+psycopg://tripsplit:tripsplit@localhost:5432/tripsplit_test alembic upgrade head
```

Run the complete backend test suite from the `backend` directory:

```bash
python -m unittest discover -s tests
```

Each integration test runs inside a database transaction that is rolled back after the test.

To see coverage (also enforced in CI with a 90% floor):

```bash
pip install -r requirements-dev.txt
coverage run --source=app -m unittest discover -s tests
coverage report -m
```

Frontend tests use Vitest and React Testing Library and don't need a database or a running backend — API calls are mocked. Run them from the `frontend` directory:

```bash
npm test
```

Both suites run in CI on every push and pull request (see the badge at the top of this README).