# ApplyTrack

ApplyTrack is a job application tracker built with **Next.js, React, TypeScript, and FastAPI**. The MVP includes an application dashboard, searchable status tracking, follow-up dates, and CSV export.

## Run with Docker Compose

```sh
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). The API docs are at [http://localhost:8000/docs](http://localhost:8000/docs). Application records are stored in a persistent SQLite volume.

## Run locally

Start the API:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In another terminal, start the frontend:

```sh
npm install
npm run dev
```

The frontend reads `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`. The API stores data in `backend/app/applytrack.db` by default; set `APPLYTRACK_DB_PATH` to change it. Configure comma-separated browser origins with `CORS_ORIGINS`.

## Included

- Create, update, and delete job applications
- Track company, title, job link, location, salary, contact, notes, status, application date, and follow-up date
- Search and filter by status
- Dashboard totals, activity chart, and application snapshot
- Export application records to CSV
- FastAPI validation, SQLite persistence, health endpoint, and interactive API docs

## MVP boundaries

This initial version has no user accounts or per-user access control. The API is intended for local development and a single personal workspace; do not expose it publicly with private application data until authentication and authorization are added. Email reminders and optional CC notification recipients are planned but not implemented. The database is SQLite for a simple local MVP; the schema can move to PostgreSQL as the service grows.
