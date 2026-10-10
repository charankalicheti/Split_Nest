Doplyment run command : sudo systemctl start split-nest-api
sudo systemctl start nginx
----------------------------------------------------------------------------
# Split Money App

A starter repository for a group expense-splitting application.

## Project layout

- `backend/` — FastAPI API and its tests
- `frontend/` — React application built with Vite
- `docker-compose.yml` — local PostgreSQL service

## Using the app

Open the frontend to see the dashboard—no account, sign-in, or registration is
needed. Create a group, add participant names, then record expenses and see
each participant's balance. Equal splits are calculated across all group
participants, with remaining cents assigned in ascending participant-ID order.
Custom expense splits use `{ "member_id": ..., "amount": ... }` entries.

## Getting started

Set `DATABASE_URL` in `backend/.env` to the PostgreSQL connection string. Copy
`frontend/.env.example` to `frontend/.env` only if you need to override the API
URL.

Run the database with `docker compose up -d`.

## Database schema

The backend stores the workflow in five PostgreSQL tables:

- `groups` stores shared-expense groups and their currency.
- `group_members` stores participant names within each group.
- `expenses` stores each group's recorded charges.
- `expense_splits` stores each member's share of an expense.
- `settlements` stores repayments between group members.

New groups can select a currency from AED, AUD, CAD, CHF, EUR, GBP, INR, NZD,
SGD, or USD. Amounts are stored in that group currency; the app does not
convert between currencies.

Apply the schema migrations from the backend directory with
`python -m alembic upgrade head`. Set `DATABASE_URL` in `backend/.env` to the
PostgreSQL connection string before running the migration. Existing installs
are upgraded by the named-participants migration.

Run the API from `backend/` with `python -m uvicorn app.main:app --reload`.
Run the frontend from `frontend/` with `npm run dev`. The frontend calls the
API at `http://localhost:8000/api` by default; set `VITE_API_BASE_URL` to
override it.

This version has no access control: anyone who can reach the app/API can view
and edit its groups and expenses. Keep it on a trusted private network.
