# ApplyTrack

ApplyTrack is a personal job application tracker. This first MVP gives you one place to record applications, see your search at a glance, and keep follow-ups in view.

## Start the app

This version is a static web app with no build step or dependencies. From this directory, run:

```sh
python3 -m http.server 8000
```

Then open [http://localhost:8000](http://localhost:8000).

## MVP features

- Dashboard totals for applications, pending responses, interviews, offers, and upcoming follow-ups
- Create, edit, and delete applications with role, company, link, location, status, dates, salary, contact, and notes
- Search and filter applications by status
- Application activity chart and a compact search snapshot
- Export application records to CSV
- Browser-local persistence using `localStorage`

The dashboard opens with a few sample records so it is useful immediately. The first saved change replaces those examples with your own records.

## Current limits

This is a personal-use frontend prototype. Data stays in the current browser and is not synced, backed up, or protected by accounts. Email reminders, optional CC recipients, authentication, a server API, and PostgreSQL are not implemented yet. Do not enter sensitive information you need to keep private or backed up.

## Next steps

1. Add a FastAPI backend and PostgreSQL schema with per-user ownership.
2. Add authentication and move browser records into the account-backed API.
3. Add scheduled reminders and notification settings, including explicit opt-in CC recipients.
4. Add document/version tracking and richer analytics.
