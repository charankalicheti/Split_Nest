# Split Money App

A starter repository for a group expense-splitting application.

## Project layout

- `backend/` — FastAPI API and its tests
- `frontend/` — React application built with Vite
- `docker-compose.yml` — local PostgreSQL service

## Expense API

Authenticated group expenses use `POST /api/groups/{group_id}/expenses` and
`GET /api/groups/{group_id}/expenses`. The request body accepts a description,
amount, and `paid_by_user_id`; `split_type` is `equal` by default or `custom`.
Custom requests include a `splits` array of `{ "user_id": ..., "amount": ... }`
entries whose amounts must add up exactly to the expense amount. Equal splits
are calculated across all group members, with any remaining cents assigned in
ascending member-ID order.

## Getting started

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to
`frontend/.env`, then replace the placeholder values as needed.

Run the database with `docker compose up -d`.

For backend and frontend setup instructions, see their respective directories.
