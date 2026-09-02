# TripSplit Ledger

[![CI](https://github.com/GGGUJINGGG/tripsplit-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/GGGUJINGGG/tripsplit-ledger/actions/workflows/ci.yml)

After a group trip, I used Splitwise to settle expenses with friends and ran into a few frustrations: the free tier limits how many expenses you can log per day, and it doesn't show a full spending breakdown for the trip — only who owes whom. I wanted to see total spending by category, by day, and per person, not just the final settlement numbers.

That gap was the starting point. As I logged our actual trip expenses into an early version of this app, I kept noticing other things I wanted — filtering, expense types, CSV export, a per-person spending summary — and added them one by one. TripSplit Ledger is the result: a personal expense tracker built around how I actually think about group travel spending.

The current implementation uses a React/Vite frontend, a FastAPI backend, and PostgreSQL persistence through SQLAlchemy 2.0. Database schema changes are managed with Alembic, and backend integration tests run against a separate PostgreSQL test database.

## Screenshots

![Trip Detail](screenshots/trip-detail.png)

![Expense Ledger](screenshots/expense-ledger.png)

## Features

**Trip management**
- Create, edit, and delete trips with date ranges
- Per-trip dashboard showing total spending, shared spending, and personal spending at a glance

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

- **Local development only** — accounts, login, and trip-level authorization are implemented, but the app is not deployed anywhere yet. Running it requires a local PostgreSQL instance and backend/frontend processes.
- **No multi-currency settlement** — expenses can be tagged with a currency, but settlement calculations are hidden when a trip mixes currencies. Exchange-rate conversion is not yet implemented.
- **Local development setup** — PostgreSQL currently runs through Docker Compose. Production database configuration and hosted deployment are not yet included.

## Planned

- Production deployment for the API, database, and frontend
- Exchange-rate conversion to enable settlements across mixed-currency trips
- Budget tracking per trip or per category

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

## API Overview

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
DELETE /api/trips/{trip_id}/participants/{participant_id}
```

Expenses:

```text
GET    /api/trips/{trip_id}/expenses
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