# Tool Crib Checkout

Shop-floor tool crib tracking. Operators scan a badge then a tool at a
touchscreen terminal to check equipment in and out. A board screen shows
what's currently out, to whom, and for how long.

## Problem

The tool crib has no record of who holds which tool. Tools go missing,
calibration due dates lapse unnoticed, and finding a specific instrument
means asking around the floor.

## Status

Backend and frontend are both functional end-to-end.

- [x] Data model — `Employee`, `Tool`, `Checkout`
- [x] Django admin for all three models
- [x] `seed_crib` management command (re-runnable demo data)
- [x] `POST /api/scan/` — check a tool in or out, with full pytest coverage
- [x] `GET /api/board/` — what's currently out
- [x] Terminal UI — scan-driven, touch-first, three-state machine
      (`scanner.js` detects real scans by keystroke timing; `dev-scanner.js`
      simulates them when `DEBUG=True`)
- [x] `api.js` — every scan gets a timeout, and a network failure is queued
      and retried automatically rather than lost
- [x] Board UI — live over a Django Channels WebSocket (not polling):
      pushed on every checkout/return, flags overdue tools, reconnects
      automatically (capped backoff + immediate retry on the browser's
      `online` event), and shows a stale indicator after 15s with no
      message

## Stack

- Django 5.2, plain views returning `JsonResponse` — no DRF
- Django Channels + Daphne (ASGI) for the live board; Redis as the channel
  layer in dev/prod, `channels.layers.InMemoryChannelLayer` in tests
- SQLite for local development (`db.sqlite3`)
- pytest / pytest-django (+ pytest-asyncio for the WebSocket consumer tests)
- Vanilla ES6 + Bootstrap 5.3 (CDN) for the frontend — no build step, no npm,
  no framework

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

redis-server &                    # needed for the live board (not the scan API)

python manage.py migrate
python manage.py seed_crib        # 20 employees, 30 tools, 5 open checkouts
python manage.py createsuperuser  # to browse /admin
python manage.py runserver        # serves over ASGI/Daphne (channels + daphne installed)
```

`handle_scan()` degrades gracefully if Redis isn't running — checking a
tool in/out never fails because the live-board push failed — but the board
page won't receive live updates until Redis is back.

## Testing

```bash
pytest
```

Tests don't need Redis running — the WebSocket consumer tests
(`tests/test_consumers.py`) swap in Channels' in-memory layer for the
duration of the test.

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

### `GET /api/board/`

Returns everything currently checked out, ordered soonest-due-first:

```json
{
  "tools": [
    {"asset_tag": "T-0003", "description": "Cordless drill", "holder_name": "James Nguyen",
     "checked_out_at": "...", "due_back_at": "...", "overdue": false}
  ],
  "generated_at": "..."
}
```

### `ws://.../ws/board/`

Pushes the same shape as `GET /api/board/` as `{"type": "board_state", ...}`
on connect, and again on every checkout/return — see
`crib/consumers.py::BoardConsumer`. Accepts `{"type": "ping"}`, replies
`{"type": "pong"}` (keep-alive, used by `board.js` to detect a half-dead
connection).

## Pages

- `/` — the scan terminal (`terminal.html` + `terminal.js` + `scanner.js`)
- `/board/` — the live board (`board.html` + `board.js`, over WebSocket)

## Project layout

```
config/
  settings.py                    channels/daphne, CHANNEL_LAYERS (Redis)
  asgi.py                        ProtocolTypeRouter: http + websocket
crib/
  models.py                      Employee, Tool, Checkout
  services.py                    handle_scan(), board_state() — all business rules
  consumers.py                   BoardConsumer — pushes board_state() over WS
  routing.py                     websocket_urlpatterns
  views.py                       terminal, board_page, /api/scan/, /api/board/
  admin.py
  management/commands/seed_crib.py
  templates/crib/
    base.html                    Bootstrap 5.3 (CDN), touch-first sizing
    terminal.html
    board.html
static/js/
  scanner.js                     keystroke-timing scan detection
  dev-scanner.js                 DEBUG-only scan simulator
  terminal.js                    three-state terminal state machine
  api.js                         fetch wrapper: timeout, offline queue, retry
  board.js                       WebSocket client: reconnect, stale indicator
tests/
  conftest.py                    shared fixtures
  test_services.py
  test_board.py
  test_consumers.py              WebsocketCommunicator, in-memory channel layer
```

Non-obvious design decisions and their rejected alternatives are logged in
`DECISIONS.md`.
