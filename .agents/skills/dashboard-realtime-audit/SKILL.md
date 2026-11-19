---
name: dashboard-realtime-audit
description: Smart Matatu API contract and realtime transport reference. Use whenever connecting frontend widgets to backend endpoints, debugging dashboard data, adding stats cards, wiring conductor/admin/passenger pages, or diagnosing 401/403/empty-widget issues in this repo — even if the user just says "the dashboard is broken" or "wire this up".
---

# Smart Matatu dashboard integration contract

Verified 2026-11-19 against `app.py` (~6,750 lines) and `fronted/src`. Flask + SQLite backend; React 19 frontend in `fronted/`. There is **no WebSocket/SSE** — realtime is HTTP polling only. `.env`'s `SOCKETIO_ASYNC_MODE=eventlet` is dead config; do not build on it.

## Transport

| Surface | Pattern |
|---|---|
| Passenger (`fronted/src/pages/Passenger.jsx:162-179`) | 3s `setTimeout` chain, gated on `navigator.onLine && document.visibilityState === "visible"`. **Protected logic — do not rewrite.** |
| Conductor pages | `setInterval` 1000ms with in-flight guards (`ConductorDashboard/Requests/EmergencyAlerts/Balances`). Trip page (`ConductorSectionPage.jsx`) polls 3s visibility-gated. |
| Admin pages | Load-on-mount via `Promise.all`; stats derived client-side from lists (no stats endpoint). |

## The four fetch layers (keep their contracts straight)

| Layer | Base URL default | credentials | Paths |
|---|---|---|---|
| `src/api/client.js` | `${hostname}:5000/api` (cross-origin) | include | NO `/api` prefix (base has it) |
| `src/services/adminApi.js` | `''` (same-origin via Vite proxy) | include | WITH `/api` prefix |
| `src/services/conductorApi.js` | `''` | include | WITH `/api` prefix |
| `src/context/AuthContext.jsx` | `''` | include | `/api/auth/*` |

Rules: every fetch carries `credentials: "include"`; every mutating call sends `X-CSRF-Token` from `useAuth().csrfToken`. CSRF is enforced by `@csrf_required` (app.py:711) on ALL admin/conductor mutations — a missing token is a guaranteed 403, not a config issue. Conductor `matatu_id` always comes from `useAuth().currentUser.matatu.id` (served by `/api/auth/me`), never from `VITE_CONDUCTOR_MATATU_ID`.

## Endpoint schemas (success shapes)

Admin (`@admin_required`):
- `GET /api/admin/matatus` → `{success, matatus:[{id, registration_number, route_id, route_name, is_archived, archived_at}]}`
- `GET /api/admin/matatus/available` → `{success, matatus:[{id, registration_number, route_name}]}` (no route_id)
- `GET /api/admin/routes` → `{success, routes:[{id, name, description, is_active, created_at, updated_at, stage_count}]}`
- `GET /api/admin/routes/:id/stages` → `{success, route:{...}, stages:[{id, route_id, route_name, name, latitude, longitude, sequence_number, is_archived, archived_at}]}`
- `GET /api/admin/conductors` → `{success, conductors:[{id, full_name, email, status:"Active"|"Archived"|"Deleted", created_at, matatu:{id, registration_number, route_name}|null}]}`
- `GET /api/admin/dashboard` → `{stats:{matatus, active_trips, available_vehicles, maintenance_vehicles(hardcoded 0), users(None)}, matatus[], routes[], trips[], alerts(hardcoded [])}` — **no UI calls this**; management pages derive stats from list endpoints.
- `GET /api/admin/matatus/:id/qr` → `{matatu_id, registration, route, qr_url, qr_data_url}`

Conductor (`@conductor_required`; URL matatu_id must equal the session assignment):
- `GET /api/conductor/dashboard/:id` → `{vehicle:{id, registration_number, route_name}, passenger_count, passengers:[{id, passenger_id, destination_stage_id, destination, stage_sequence}]}`
- `GET /api/conductor/emergency-alerts/:id` → `{unresolved_count, active_alerts[], history[]}`; alert rows: `{alert_id, journey_id, passenger_id, alert_type, message, status, created_at, acknowledged_at, ...}`
- `GET /api/conductor/balances/:id` → `{pending_balances[], awaiting_confirmation[], history[]}`; rows keyed `balance_id, passenger_id, amount, status, journey_id, ...`
- `GET /api/conductor/destination-change-requests/:id` → `{requests:[{request_id, journey_id, passenger_id, current_destination, requested_destination, status, created_at}]}`
- `GET /api/conductor/qr-code` → `{success, matatu:{...}, qr_url, qr_image}` (server derives matatu from session)

Passenger (no session auth; bearer token only for journey-scoped endpoints):
- `GET /api/passenger/trip-info?matatu_id=` → `{id, plate, route, code, stages:[{id, name, latitude, longitude, sequence_number}]}`
- `GET /api/vehicle-status/:id` (alias `/vehicle-status/:id`) → `{matatu, location:{latitude, longitude, speed, accuracy, source, last_updated_at, age_seconds, stale}, passengers:[{id, destination, distance, speed, status, eta}]}`
- `POST /api/matatus/:id/location` — conductor GPS ingest, guarded by `X-Conductor-Token` header (env `CONDUCTOR_LOCATION_TOKEN`), NOT session auth.

## Error envelopes (three coexisting styles — read all three when handling failures)

1. `{error: {message, fields?}}` — 404 handler for `/api/*`, trip-info, vehicle-status API 404s, passenger/register
2. `{error: "string"}` — every conductor endpoint
3. `{success: false, message}` — admin/auth endpoints and both auth decorators

Handle with `data?.error?.message || data?.error || data?.message` when writing a new caller.

## Known pitfalls (verified during the 2026-11-19 audit)

- **Migrations:** fresh databases need `migrate_matatu_lifecycle` + `migrate_routes` beyond `init_db`, or admin endpoints 500 with `no such column: m.is_archived` / `no such table: routes`. `migrate_routes` only knows its hardcoded legacy route names — routes seeded by hand in SQL need a `routes` row + `route_id` backfill done manually (see INTEGRATION-style notes in repo history).
- `SameSite=Lax` session cookie still flows on cross-**origin** same-**site** fetches (localhost:5173 → localhost:5000), but only with `credentials: "include"`.
- Conductor data pages previously used `VITE_CONDUCTOR_MATATU_ID || "1"` — this 403s any conductor not assigned matatu 1 (`conductor_required` checks URL id vs assignment). Always derive from auth.
- Timestamps from location writers are Z-suffixed UTC ISO; SQLite `datetime('now')` is naive and crashes `location_age_seconds` — never seed with it.
- `templates/conductor.html` and `/move-matatu/<id>` are legacy demo paths; the React app is the real UI.
