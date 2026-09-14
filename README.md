# Tool Crib Checkout

Shop-floor tool crib tracking. Operators scan a badge then a tool at a
touchscreen terminal to check equipment in and out. A board screen shows
what's currently out, to whom, and for how long.

## Problem

The tool crib has no record of who holds which tool. Tools go missing,
calibration due dates lapse unnoticed, and finding a specific instrument
means asking around the floor.

## Status

Backend is functional; frontend is not built yet.

- [x] Data model — `Employee`, `Tool`, `Checkout`
- [x] Django admin for all three models
- [x] `seed_crib` management command (re-runnable demo data)
- [x] `POST /api/scan/` — check a tool in or out, with full pytest coverage
- [ ] `GET /api/board/` — what's currently out
- [ ] Terminal UI (scan-driven, touch-first)
- [ ] Board UI (auto-refreshing)

## Stack

- Django 5.2, plain views returning `JsonResponse` — no DRF
- SQLite for local development (`db.sqlite3`)
- pytest / pytest-django for tests
- Vanilla ES6 + Bootstrap 5.3 planned for the frontend — no build step, no npm

## Data model

A tool is **out** iff it has a `Checkout` row with `returned_at IS NULL`.
That's the entire state model — no status field on `Tool`, no
denormalization.

- **Employee** — `badge_id` (unique), `name`, `department`, `is_active`
- **Tool** — `asset_tag` (unique), `description`, `calibration_due`
  (nullable), `is_active`
- **Checkout** — `tool`, `employee`, `checked_out_at`, `due_back_at`,
  `returned_at` (nullable). Default loan period is 8 hours.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_crib        # 20 employees, 30 tools, 5 open checkouts
python manage.py createsuperuser  # to browse /admin
python manage.py runserver
```

## Testing

```bash
pytest
```

## API

### `POST /api/scan/`

Body: `{"badge": "E-1001", "asset_tag": "T-0001"}`

| Condition | Status | Response |
|---|---|---|
| Tool free | 200 | `{action: "checked_out", tool, employee, due_back_at}` |
| Tool held by this employee | 200 | `{action: "returned", tool, duration_minutes}` |
| Tool held by someone else | 409 | `{error: "held_by_other", holder_name, since}` |
| Unknown badge | 404 | `{error: "unknown_badge", value}` |
| Unknown asset tag | 404 | `{error: "unknown_tool", value}` |
| Tool inactive | 409 | `{error: "tool_inactive"}` |
| Past calibration due | 409 | `{error: "calibration_overdue", calibration_due}` |
| Same badge+tool scanned again within 2s | 200 | previous result replayed, state unchanged |

All business logic lives in `crib/services.py::handle_scan()`; the view only
parses the request and maps the result to a status code.

## Project layout

```
config/            settings, urls, wsgi
crib/
  models.py        Employee, Tool, Checkout
  services.py       handle_scan() — all business rules
  views.py           /api/scan/
  admin.py
  management/commands/seed_crib.py
tests/
  test_services.py
```

Non-obvious design decisions and their rejected alternatives are logged in
`DECISIONS.md`.
