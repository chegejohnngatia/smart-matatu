# Smart Matatu Integration

## Scope

The React admin dashboard is connected to the existing Flask and SQLite data for matatus, route stages, and trip/location monitoring. The existing browser-only demo authentication remains unchanged. Admin create/update actions, users, assignments, and trip history are not implemented because the backend has no corresponding data model or authenticated API contract.

## Run locally

Backend:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
flask --app app run --host 0.0.0.0 --port 5000
```

Frontend:

```bash
cd fronted
npm install
npm run dev
```

Default URLs:

- Flask API: `http://127.0.0.1:5000`
- Vite frontend: `http://127.0.0.1:5173`
- Connected admin dashboard: `http://127.0.0.1:5173/admin` after demo admin sign-in

## Open the passenger dashboard from a phone hotspot

1. Connect the phone and PC to the same phone hotspot.
2. Start Flask with the network bind shown above, and start Vite with `npm run dev` (Vite listens on `0.0.0.0:5173`).
3. On the PC, open the admin dashboard using the PC's hotspot-network IP, for example `http://192.168.43.20:5173/admin`. The phone can then scan a generated vehicle QR code, or open that same IP and passenger path directly.

When `VITE_API_BASE_URL` is unset, the frontend uses the current page's hostname on port `5000`. Development CORS accepts the Vite origin on port `5173` only when it uses the same host as the Flask request. QR links use the frontend origin; when the admin page is opened through localhost, the QR link substitutes the PC's detected network IP. If the PC has multiple network adapters or IP detection picks the wrong one, set backend `FRONTEND_URL` to the PC's hotspot address, such as `http://192.168.43.20:5173`.

Allow inbound TCP ports `5000` and `5173` for the hotspot/private network in the PC firewall if prompted. Device isolation or firewall rules on the hotspot can still prevent phone-to-PC connections.

## Environment

Backend `.env` values:

- `DATABASE_PATH`: SQLite database path.
- `FRONTEND_URL`: URL embedded in generated passenger QR links.
- `FRONTEND_ORIGINS`: comma-separated allowed browser origins for API CORS headers.
- `LOCATION_SOURCE`: `simulation` or `gps`.
- `CONDUCTOR_LOCATION_TOKEN`: shared secret for GPS updates; do not expose it in the frontend.

Frontend `fronted/.env` values:

- `VITE_API_BASE_URL`: API base URL, normally `http://127.0.0.1:5000/api`.

If `VITE_API_BASE_URL` is unset, the frontend uses the current page's hostname on port `5000`, which supports localhost and hotspot access.

## Admin API

All paths below are under the configured API base URL and currently require no backend authentication because the existing backend has no auth implementation.

| Method | Path               | Request | Response                                                                                                | Errors                                                                            |
| ------ | ------------------ | ------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `GET`  | `/admin/dashboard` | None    | `{ stats, matatus, routes, trips, alerts }`                                                             | JSON `404` for an unknown API path; network/API errors are shown by the dashboard |
| `GET`  | `/admin/matatus`   | None    | Array of vehicle records with registration, route, passenger count, status, and optional location       | Same API error handling                                                           |
| `GET`  | `/admin/routes`    | None    | Array of route records with origin, destination, distance in km, stage count, vehicle count, and stages | Same API error handling                                                           |
| `GET`  | `/admin/trips`     | None    | Array of current matatu trip/location records with passenger count and status                           | Same API error handling                                                           |

## Passenger live journey API

The passenger React dashboard polls the vehicle status endpoint every three seconds while its page is visible and the browser is online. The same Flask handler is available under the API base URL for cross-origin development; the original `/vehicle-status/<matatu_id>` route remains available to the Flask templates.

| Method | Path | Request | Response |
| ------ | ---- | ------- | -------- |
| `GET` | `/vehicle-status/<matatu_id>` | None | `{ matatu, location, passengers }`; `location` contains latitude, longitude, speed, accuracy, source, last_updated_at, age_seconds, and stale. `passengers` contains destination, status, remaining distance, speed, and ETA. |
| `GET` | `/passenger/trip-info?matatu_id=<id>` | Vehicle ID | Trip identity and ordered stages, including stage latitude and longitude for drawing the route. |

The passenger UI treats a location older than 60 seconds as stale and continues showing the last reported point. `heading` is estimated in the browser from successive coordinates because the current backend payload does not include heading. The React app does not send GPS updates and must never contain `CONDUCTOR_LOCATION_TOKEN`.

Backend location fields retain snake_case. `fronted/src/api/client.js` converts admin response names to the existing React camelCase convention. Distances are kilometres; speed is kilometres per hour; GPS timestamps are ISO-8601 strings; coordinates are decimal degrees.

## Decisions

- The existing `fronted/` directory remains authoritative; no rename or framework change was made.
- The existing `AdminDashboard` design and navigation were preserved. Mock resource rows were replaced with API data.
- The `/admin` entry point now opens the connected dashboard at `/admin-prototype`.
- Add and action controls remain visibly present but report that the current backend does not provide write endpoints. No new business rules or CRUD endpoints were invented.
- The existing manual Flask CORS implementation and origin allow-list were preserved.
- The pre-existing modified `smart_matatu.db` and untracked `Pipfile` were left untouched.
