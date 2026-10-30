# Smart Matatu (Flask + SQLite) — Implementation Checklist

**Builds on existing Flask project. Uses raw SQL. Follows v3 DB design.**

---

## Phase 0 — Project Structure & Config (1–2 hrs)

- [ ] Split `app.py` into modules:
  ```
  smart_matatu/
  ├── app/
  │   ├── __init__.py          # Flask factory
  │   ├── config.py            # Config from .env
  │   ├── database.py          # DB connection + migrations (raw SQL)
  │   ├── gps.py               # Haversine (already done)
  │   ├── models/              # SQL query helpers (not ORM)
  │   │   ├── __init__.py
  │   │   ├── matatu.py
  │   │   ├── route.py
  │   │   ├── stage.py
  │   │   ├── trip.py
  │   │   ├── journey.py
  │   │   ├── user.py
  │   │   ├── notification.py
  │   │   └── location.py
  │   ├── services/            # Business logic
  │   │   ├── __init__.py
  │   │   ├── tracking.py      # position, distance, ETA
  │   │   ├── notification.py  # dispatch, thresholds
  │   │   └── trip.py          # trip lifecycle
  │   ├── routes/              # View functions
  │   │   ├── __init__.py
  │   │   ├── auth.py
  │   │   ├── passenger.py
  │   │   ├── conductor.py
  │   │   ├── admin.py
  │   │   └── api.py           # JSON endpoints for real-time
  │   ├── templates/           # Reorganize
  │   └── static/
  ├── migrations/              # Raw SQL migration files
  ├── tests/
  ├── .env.example
  ├── requirements.txt
  └── run.py
  ```
- [ ] Create `.env` / `.env.example` with `SECRET_KEY`, `DATABASE_URL`, `HOST`, `PORT`
- [ ] Update `requirements.txt` with: `flask`, `python-dotenv`, `qrcode[pil]`, `gunicorn`, `websocket-client` (for testing), `pytest`
- [ ] Move templates to `app/templates/` with structure: `base.html`, `layouts/`, `components/`, `passenger/`, `conductor/`, `admin/`
- [ ] Verify `python run.py` works

---

## Phase 1 — Database Migrations to v3 Schema (3–4 hrs)

Create migration files in `migrations/` (run in order):

| # | Migration | Purpose |
|---|-----------|---------|
| 001 | `001_create_routes_table.sql` | `route(id, name, description, created_at)` |
| 002 | `002_alter_stages_add_route_fk.sql` | Add `route_id` FK to `stages`, drop `route_name` string, add unique constraint `(route_id, sequence_order)` |
| 003 | `003_alter_matatus_add_fields.sql` | Add `operator`, `created_at` to `matatus`; add `qr_code` table |
| 004 | `004_create_qr_codes_table.sql` | `qr_code(id, matatu_id UNIQUE, code_value UNIQUE, status, created_at)` |
| 005 | `005_create_user_accounts_table.sql` | `user_account(id, name, email_or_phone UNIQUE, password_hash, role, status, matatu_id FK nullable, created_at)` |
| 006 | `006_create_active_trips_table.sql` | `active_trip(id, matatu_id FK, route_id FK, start_time, end_time nullable, status, current_latitude, current_longitude, last_ping_at)` |
| 007 | `007_create_journey_sessions_table.sql` | `journey_session(id, passenger_id FK, trip_id FK, destination_stage_id FK, start_time, end_time nullable, status)` |
| 008 | `008_migrate_passenger_destinations.sql` | Migrate data from `passenger_destinations` → `journey_session` (map `passenger_token` → anonymous passenger user or create placeholder) |
| 009 | `009_create_notifications_table.sql` | `notification(id, recipient_type, recipient_id, journey_id FK nullable, message, timestamp, status)` |
| 010 | `010_create_trip_location_log.sql` | `trip_location_log(id, trip_id FK, latitude, longitude, recorded_at)` |
| 011 | `011_create_system_config.sql` | `system_config(id, key UNIQUE, value, description, updated_at)` |
| 012 | `012_alter_matatu_locations.sql` | Migrate `matatu_locations` → `trip_location_log` (one row per trip) + keep current position cache on `active_trip` |

- [ ] Add migration runner in `database.py`: `apply_migrations()` that executes `.sql` files in order, tracks applied migrations in a `schema_migrations` table
- [ ] Run migrations against `smart_matatu.db`
- [ ] Verify schema matches v3 ERD

---

## Phase 2 — Model Query Helpers (Raw SQL Wrappers) (2–3 hrs)

Create `app/models/*.py` — **no ORM**, just typed query functions:

- [ ] `matatu.py` — CRUD + QR code
- [ ] `route.py` — CRUD
- [ ] `stage.py` — CRUD + `get_stages_for_route(route_id)` ordered
- [ ] `trip.py` — `create_trip`, `get_active_trip_for_matatu`, `end_trip`, `update_position`
- [ ] `journey.py` — `create_journey`, `get_journey`, `update_status`, `list_for_trip`, `list_for_passenger`
- [ ] `user.py` — `create_user`, `get_by_email_or_phone`, `verify_password`, `assign_matatu`
- [ ] `notification.py` — `create_notification`, `mark_read`, `list_for_user`
- [ ] `location.py` — `log_location`, `get_recent_for_trip`

---

## Phase 3 — Service Layer (Business Logic) (3–4 hrs)

- [ ] **`services/tracking.py`**
  - `get_current_stage(trip_id)` → stage dict (uses `active_trip.current_stage_sequence` or GPS proximity)
  - `calculate_distance_to_stage(trip_id, stage_id)` → meters (haversine)
  - `estimate_eta(trip_id, stage_id)` → minutes (distance / speed)
  - `check_approaching_threshold(trip_id, journey_id)` → bool (configurable radius from `system_config`)
- [ ] **`services/notification.py`**
  - `dispatch_approaching(journey_id)` — creates notification for passenger + conductor
  - `dispatch_arrived(journey_id)` — creates notification
  - `dispatch_batch_to_conductor(trip_id, message)` — batch alert
- [ ] **`services/trip.py`**
  - `start_trip(matatu_id, route_id)` → trip_id
  - `advance_trip_to_next_stage(trip_id)` — updates `current_stage_sequence`
  - `cancel_trip(trip_id)`
- [ ] Unit tests for each service function (use `sqlite3` in-memory DB + test fixtures)

---

## Phase 4 — Auth & Role-Based Access (2–3 hrs)

- [ ] Password hashing — use `werkzeug.security.generate_password_hash` / `check_password_hash`
- [ ] Session management — Flask `session` + `login_required` decorator
- [ ] Role decorator — `@role_required('passenger')`, `@role_required('conductor')`, `@role_required('administrator')`
- [ ] Routes (`routes/auth.py`):
  - `GET/POST /register` — passenger self-registration
  - `GET/POST /login` — shared login, redirects by role
  - `POST /logout`
  - `GET /profile` — update name, password
- [ ] Admin-only: `POST /admin/users/<id>/assign-matatu` — assign conductor to matatu (1:1)

---

## Phase 5 — Passenger Journey Flow (3–4 hrs)

- [ ] **QR Scan** (`routes/passenger.py`):
  - `GET /scan` — camera page (JS reads QR, submits code)
  - `POST /scan` — validate QR → lookup `matatu` → find `active_trip` → redirect to stage selection
  - Error: no active trip → "Matatu not on active trip"
- [ ] **Stage Selection**:
  - `GET /journey/select/<trip_id>` — list stages for trip's route (from `stage` model)
  - `POST /journey/select/<trip_id>` — create `journey_session` (destination locked per FR-P-21)
- [ ] **Journey Tracking** (sync first):
  - `GET /journey/<journey_id>` — shows: current stage, destination, next stage, distance, ETA, progress bar
  - Auto-refresh every 5s (meta refresh or JS fetch)
  - `POST /journey/<journey_id>/end` — passenger confirms arrived → status=`ended`
- [ ] **Journey History**:
  - `GET /journey/history` — list past `journey_session` for logged-in passenger

---

## Phase 6 — Conductor Dashboard (2–3 hrs)

- [ ] `GET /conductor/dashboard` — requires `role=conductor`
  - Find conductor's matatu via `user_account.matatu_id`
  - Find `active_trip` for that matatu
  - Show: trip status, current stage, speed
- [ ] **Passenger List** — from `journey_session` where `trip_id` = active trip
  - Group by `destination_stage` → count per stage
  - Show: passenger name/token, destination, status
- [ ] **Upcoming Stages** — next 3 stages with distance/ETA (reuse `services/tracking.py`)
- [ ] **Manual Notify** — button per passenger → `services.notification.dispatch_approaching`

---

## Phase 7 — Admin Interface (2 hrs)

- [ ] `GET /admin` — role=administrator
- [ ] **Matatu Management** — CRUD matatus, generate QR codes
- [ ] **Route/Stage Management** — CRUD routes, inline stage editor
- [ ] **Trip Control** — start/end/cancel trips (FR-A-06)
- [ ] **System Config** — edit `system_config` keys (notification radius, GPS stale threshold, etc.)
- [ ] **View All Journeys** — filter by date, matatu, status

---

## Phase 8 — Real-Time (WebSocket) (4–6 hrs)

- [ ] Add Flask-SocketIO or plain WebSocket (`websockets` lib) for server push
- [ ] **GPS Ingest Endpoint** (conductor app or simulator):
  - `POST /api/trips/<trip_id>/location` — `{lat, lon, speed, timestamp}`
  - Updates `active_trip` cache + inserts `trip_location_log`
  - Triggers position recalculation for all journeys on that trip
- [ ] **WebSocket Channels**:
  - `journey:{journey_id}` — passenger receives: `{current_stage, distance, eta, status}`
  - `conductor:{trip_id}` — conductor receives: passenger list updates, stage counts
- [ ] Frontend JS — connect to WS, update DOM live (no refresh)
- [ ] Simulator script — `scripts/simulate_gps.py` reads stages, posts location every 2s

---

## Phase 9 — Polish & Deployment (ongoing)

- [ ] Seed script — `scripts/seed.py` creates: 1 route + 5 stages, 1 matatu + QR, 1 conductor user, 1 active trip
- [ ] GPS Simulator — for demo without hardware
- [ ] Dockerfile — multi-stage: build → runtime with gunicorn + nginx
- [ ] docker-compose.yml — app + nginx + (optional) redis for SocketIO
- [ ] CI/CD — GitHub Actions: lint → test → build image
- [ ] Monitoring — health check endpoint, structured logs

---

## Migration Priority Order (Do Not Skip)

| Priority | Task | Why |
|----------|------|-----|
| **P0** | Phase 1 migrations (001–012) | Schema is foundation; everything else depends on it |
| **P0** | Phase 2 model helpers | Type-safe queries prevent SQL bugs |
| **P1** | Phase 3 services | Core logic reusable by views + real-time |
| **P1** | Phase 4 auth | Role-gating protects conductor/admin routes |
| **P2** | Phase 5 passenger flow | Core user value |
| **P2** | Phase 6 conductor dashboard | Operational value |
| **P3** | Phase 7 admin | Operational control |
| **P4** | Phase 8 real-time | Enhancement; sync version works first |

---

## Quick Start Commands

```bash
# 1. Set up venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run migrations
python -m app.database migrate

# 3. Seed demo data
python scripts/seed.py

# 4. Run dev server
python run.py

# 5. Test GPS simulator (separate terminal)
python scripts/simulate_gps.py
```