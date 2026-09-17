# TripSplit Ledger

A self-hosted group expense tracker for trips — split bills, track who paid what, and see a full spending breakdown by category, day, and person instead of just a final settlement number.

[![CI](https://github.com/GGGUJINGGG/tripsplit-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/GGGUJINGGG/tripsplit-ledger/actions/workflows/ci.yml)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8?logo=pwa&logoColor=white)

**Live demo:** [tripsplit-ledger.vercel.app](https://tripsplit-ledger.vercel.app) — log in with the demo account below (pre-loaded with sample data) or register your own (see [Deployment](#deployment) for how the frontend/backend are hosted).

- **Email:** `demo@tripsplitledger.com`
- **Password:** `TripSplitDemo2026!`

This is a shared, publicly-writable account — anyone can edit or delete its data, so don't rely on it staying in any particular state. It comes pre-loaded with a sample trip (multiple participants, expenses across categories, a settlement suggestion, and a payment awaiting confirmation) so there's something to look at immediately instead of an empty state.

## Screenshots

![Trip Detail](screenshots/trip-detail.png)

![Expense Ledger](screenshots/expense-ledger.png)

## Contents

- [Features](#features)
- [Known Limitations](#known-limitations)
- [Planned](#planned)
- [Architecture](#architecture)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Deployment](#deployment)
- [API Overview](#api-overview)
- [Calculation Logic](#calculation-logic)
- [Tests](#tests)

## Features

**Trip management**
- Create trips with date ranges
- Per-trip dashboard showing total spending, shared spending, and personal spending at a glance
- Invite anyone to a trip by email (owner-only) — they show up as a pending placeholder right away, but only become a real member once they accept: an unregistered email accepts by registering, a registered one accepts from a "Pending Invites" list on their Trips page (with a Decline option too)
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

**Settlements**
- Simplified payment plan that minimizes the number of transactions, computed independently per currency for mixed-currency trips
- Settlement amounts consistent with per-participant net balances
- Record an actual payment between two participants — one click from a suggested settlement, or a freeform amount/currency/date/note for a partial or unprompted payment
- Payments to registered members require recipient confirmation before they affect balances and settlement suggestions; the recipient can confirm or reject them, while payments to placeholder members take effect immediately
- Delete a recorded payment if it was entered by mistake; balances and settlement suggestions update accordingly

**Reminders**
- Automated email reminders for outstanding balances: the day after a trip's `end_date` (if set), or every Monday for a trip with no end date — skipped once everyone's settled up, and requires no manual trigger once the scheduled job is deployed (see [Deployment](#deployment))

**Visualizations**
- Daily spending trend chart, a category breakdown pie chart, and a per-participant "who paid" comparison chart, each split into one series per currency for mixed-currency trips

**Mobile**
- Installable as a Progressive Web App — "Add to Home Screen" on iOS/Android for a full-screen, app-like launch experience with no browser chrome
- Full-screen PWA layout respects iOS's safe areas (notch/Dynamic Island and home indicator) via `env(safe-area-inset-*)`, so the top bar and bottom-corner buttons don't sit under the system UI
- Floating quick-jump buttons (Add Expense, Record Payment, back to top) on the trip detail page below the 880px breakpoint, so a long trip doesn't require scrolling back up to reach them; hidden above that width since the two-column desktop layout already keeps everything in reach

**Export**
- CSV export of the full expense ledger with all filters applied

## Known Limitations

- **No exchange-rate conversion** — settlements, spending totals, and the category/daily/who-paid charts are all computed independently per currency (a trip with both USD and CNY shared expenses gets two separate settlement suggestions, two separate chart series, and so on), but nothing is ever converted into a common currency. The one exception is the backend's `/dashboard` `total_trip_spending`/`paid_by_person`/`owed_by_person`/`net_balances` fields — those still sum raw amounts across currencies without segmenting them, so those specific numbers aren't meaningful for a mixed-currency trip; the frontend works around it by computing its own per-currency breakdowns instead (and shows "Mixed currencies" in place of a number for shared responsibility/net balance when a trip has more than one currency).
- **No frontend UI for inviting members beyond the invite-by-email form** — the API also enforces owner-only rules here, but there's no bulk invite or member-management screen beyond that one form.
- **Expense Ledger pagination is client-side** — `GET /trips/{id}/expenses` supports real `limit`/`offset` query params, but the frontend still loads a trip's full expense list in one request (it's embedded in `GET /trips/{id}`, which the dashboard and CSV export also depend on) and paginates 25 rows at a time in the browser. That keeps the table usable at moderate scale but doesn't reduce what's transferred over the network — a trip with tens of thousands of expenses would need the frontend to fetch pages from the paginated endpoint directly instead.
- **Settlement reminders run on a fixed UTC cron schedule, not each trip's local time** — the reminder job (see [Deployment](#deployment)) fires once daily at a fixed UTC hour; "the day after a trip ends" and "every Monday" are both evaluated in UTC, so depending on timezone a reminder can land a few hours earlier or later than local midnight/Monday.
- **Rate limiting is in-memory and single-instance** — `/auth/login`, `/auth/register`, and `/auth/forgot-password` are rate-limited per IP, but the counters live in the API process's memory. Fine for this app's one Railway container; a multi-instance deployment would need a shared store (Redis, etc.) instead.

## Planned

- Exchange-rate conversion, so a mixed-currency trip shows one combined settlement instead of one per currency
- Budget tracking per trip or per category
- Native app-store packaging (Capacitor or React Native) — the current PWA installs to a home screen but isn't listed on the App Store or Google Play

## Architecture

```mermaid
flowchart LR
    subgraph Client["Browser"]
        FE["React 19 + Vite SPA<br/>access + refresh JWT in localStorage"]
    end

    subgraph Server["FastAPI backend"]
        Auth["/api/auth<br/>register · login · refresh · logout ·<br/>forgot/reset-password · me"]
        Trips["/api/trips<br/>trips · participants · expenses · payments"]
        Invite["/api/invitations<br/>accept/decline a pending invite"]
        Dash["/api/trips/{id}/dashboard"]
        Settle["/api/trips/{id}/settlements"]
    end

    DB[("PostgreSQL<br/>SQLAlchemy 2.0 + Alembic")]

    FE -- "HTTPS, Bearer JWT" --> Auth
    FE -- "HTTPS, Bearer JWT" --> Trips
    FE -- "HTTPS, Bearer JWT" --> Invite
    FE -- "HTTPS, Bearer JWT" --> Dash
    FE -- "HTTPS, Bearer JWT" --> Settle
    Auth --> DB
    Trips --> DB
    Invite --> DB
    Dash --> DB
    Settle --> DB
```

Every route except `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/forgot-password`, and `/api/auth/reset-password` requires a valid JWT and checks that the requesting user is a member of the trip being accessed; only the trip owner can rename/delete a trip or invite new members. `/dashboard` and `/settlements` derive their numbers from the same expense/share tables. Settlement balances come from the backend; the frontend only derives its own per-currency presentation breakdowns where the dashboard's aggregate fields would otherwise mix currencies.

Access tokens expire after 30 minutes; the frontend transparently exchanges the (longer-lived, rotating) refresh token for a new one on a 401 instead of forcing a re-login. `/auth/login`, `/auth/register`, and `/auth/forgot-password` are rate-limited per IP.

The backend logs structured JSON for every request (method, path, status, duration) and reports unhandled exceptions to Sentry in production.

Not shown in the diagram: `backend/app/scripts/send_settlement_reminders.py` runs outside the request/response cycle above, as a separate scheduled job (see [Deployment](#deployment)) rather than an API route — it reads the same database directly and reuses the settlements service to decide who to email.

### Database schema

```mermaid
erDiagram
    USERS ||--o{ TRIP_MEMBERS : "has (nullable once removed)"
    TRIPS ||--o{ TRIP_MEMBERS : "has"
    TRIPS ||--o{ EXPENSES : "has"
    TRIPS ||--o{ PAYMENTS : "has"
    TRIP_MEMBERS ||--o{ EXPENSES : "pays for"
    TRIP_MEMBERS ||--o{ PAYMENTS : "sends (from_member)"
    TRIP_MEMBERS ||--o{ PAYMENTS : "receives (to_member)"
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
        datetime end_date_reminder_sent_at "nullable, one-time reminder guard"
        date last_weekly_reminder_date "nullable, weekly reminder guard"
    }
    TRIP_MEMBERS {
        uuid id PK
        uuid trip_id FK
        uuid user_id FK "nullable, SET NULL on user delete"
        string display_name
        string invited_email "nullable, set for a pending email invite"
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
    PAYMENTS {
        uuid id PK
        uuid trip_id FK
        uuid from_member_id FK
        uuid to_member_id FK
        int amount_cents
        string currency
        date date
        text note
        enum status "pending | confirmed | rejected"
        datetime responded_at "nullable"
    }
```

`trip_members` is the join between a `User` account and a `Trip` — its `user_id` is nullable so a guest can be added by name only (no account) and a trip owner can't accidentally lock themselves out by deleting their own user record elsewhere. `invited_email` is set on the same nullable-`user_id` row for a pending email invite (regardless of whether that email is already registered) — it isn't a real membership until accepted: registering with a matching email claims every such row across every trip at once (see `register_user()` in `app/routers/auth.py`), and a registered user accepts individually from `GET /api/invitations` (see `app/routers/invitations.py`). `expenses.amount_cents`, `expense_shares.amount_cents`, and `payments.amount_cents` are integers (not floats) specifically to avoid floating-point rounding drift when splitting a bill or recording a payment; see [Calculation Logic](#calculation-logic).

A `Payment` is a real transfer between two trip members recorded to settle an existing debt — it isn't spending, so it never counts toward any spending total. A payment to a registered member starts as `pending` and only affects that currency's balances and settlement suggestions after the recipient confirms it; the recipient may reject it instead. A payment to a placeholder member is confirmed immediately because that member has no account with which to respond. `trips.end_date_reminder_sent_at` and `trips.last_weekly_reminder_date` exist purely so the settlement-reminder job (see [Deployment](#deployment)) doesn't email the same trip twice for the same occasion.

## Backend Setup

Requirements:

- Python 3.11+
- Node.js 20+
- Docker with Docker Compose

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
npm ci
npm run dev
```

The frontend will run at:

```text
http://localhost:5173
```

By default, the frontend calls the backend at `http://localhost:8000/api`.

## Deployment

The backend runs as a container (`backend/Dockerfile`) on [Railway](https://railway.app), and the frontend is a static build on [Vercel](https://vercel.com). Both are connected to this repo's `main` branch — pushing redeploys them automatically. The production URL is intentionally not published here.

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

**Optional — real email delivery:** password-reset and trip-invite emails are logged to the backend's output instead of actually sent unless you also add `RESEND_API_KEY` (and optionally `RESEND_FROM_EMAIL`) to the same Variables tab. Get a free key at [resend.com](https://resend.com); without your own verified sending domain, Resend restricts delivery to its default `onboarding@resend.dev` sender and to your own Resend account's email address, so you'd only be able to email yourself until you verify a domain. This deployment has both configured (`RESEND_API_KEY` plus a domain verified via Cloudflare), so its emails go out for real.

### Frontend on Vercel

1. Sign up / log in at vercel.com with your GitHub account.
2. **Add New → Project** → import this repo.
3. Set **Root Directory** to `frontend` (Vite framework preset is auto-detected).
4. Add an environment variable **before** the first deploy: `VITE_API_BASE_URL` = `https://your-app.up.railway.app/api` (Vite bakes this into the static build at build time — changing it later requires a redeploy, not just a restart).
5. Deploy. Vercel gives you a URL like `https://your-app.vercel.app`. `vercel.json` in this repo rewrites all paths to `index.html` so refreshing a client-side route (e.g. `/trips/abc123`) doesn't 404.

### Settlement-reminder cron job on Railway

`backend/app/scripts/send_settlement_reminders.py` emails trip members who still owe money — once the day after a dated trip's `end_date`, or every Monday for a trip with no `end_date` — but the web service above has no built-in scheduler, so this needs its own Railway service:

1. In the same Railway project, click **New → Empty Service** (not "from GitHub repo" — this reuses the backend service's existing image once linked below).
2. On the new service's **Settings**, set **Source Repo** to this repo and **Root Directory** to `backend`, same as the web service.
3. Under **Settings → Deploy**, set **Custom Start Command** to `python -m app.scripts.send_settlement_reminders` (this replaces the Dockerfile's default `CMD`, so it runs the script once and exits instead of starting `uvicorn`).
4. Under **Settings → Cron Schedule**, set it to `0 9 * * *` (9am UTC daily — the script itself decides whether today is the right day for each trip, so daily is the correct cadence).
5. Copy the same `DATABASE_URL` and `RESEND_API_KEY`/`RESEND_FROM_EMAIL` variables from the web service's **Variables** tab (this service needs its own copies — Railway doesn't share variables between services automatically).
6. Trigger a manual run once (Railway's dashboard has a "Trigger" button on cron services) and check the logs for `Sent settlement reminders for N trip(s)`.

Billed the same as any other Railway service — per-second compute while it runs, $0 while idle — so a job that runs for a couple of seconds once a day costs a negligible fraction of a cent on top of whatever plan is already covering the web service.

### Wire them together

Go back to the Railway backend's `CORS_ORIGINS` variable and set it to your actual Vercel URL (e.g. `https://your-app.vercel.app`), then redeploy the backend service so the browser is allowed to call it.

### Smoke test

Once both are live, walk through this once end-to-end:

- [ ] Register an account
- [ ] Create a trip
- [ ] Add a participant
- [ ] Add, edit, and delete an expense
- [ ] View the dashboard, category breakdown, and spending charts
- [ ] View the settlement summary; record a payment and confirm balances update
- [ ] Log out, log back in
- [ ] Confirm the trip and its data are still there
- [ ] Register a second account and confirm it can't see the first account's trips
- [ ] Open the deployed frontend on a phone browser and confirm it offers "Add to Home Screen"
- [ ] Manually trigger the settlement-reminder cron service once and confirm its logs show `Sent settlement reminders for N trip(s)`

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

Invitations (pending, cross-trip — for the invitee, not the trip owner):

```text
GET    /api/invitations
POST   /api/invitations/{invitation_id}/accept
DELETE /api/invitations/{invitation_id}
```

Expenses:

```text
GET    /api/trips/{trip_id}/expenses?limit=&offset=   # limit 1-200, default 50
POST   /api/trips/{trip_id}/expenses
GET    /api/trips/{trip_id}/expenses/{expense_id}
PUT    /api/trips/{trip_id}/expenses/{expense_id}
DELETE /api/trips/{trip_id}/expenses/{expense_id}
```

Payments:

```text
GET    /api/trips/{trip_id}/payments
POST   /api/trips/{trip_id}/payments
POST   /api/trips/{trip_id}/payments/{payment_id}/confirm
POST   /api/trips/{trip_id}/payments/{payment_id}/reject
DELETE /api/trips/{trip_id}/payments/{payment_id}
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
- Simplified settlement payments, computed independently per currency

Confirmed payments (an actual transfer between two participants, not an expense) net directly into that currency's balances and settlement suggestions — a payment moves a debtor's balance toward zero and a creditor's balance down by the same amount, without changing anyone's spending totals or share of the trip's costs. Pending and rejected payments do not affect the calculation.

Expense shares and payment amounts are calculated in cents to avoid floating point drift.

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
