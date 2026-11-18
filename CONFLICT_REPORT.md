# Merge Conflict Report

- Date: 2026-11-16
- Current branch: `feature/passenger-qr-scanner`
- Branch merged in: `origin/main` at `d30056916d843c2210564af032ee44487785c0ea`
- Common ancestor: `8657a9e85793e8bad4070882c1b5818c16321a0a`
- Operation: merge, recorded by `95967be499a6a6188d84565a637fa5bdf9cf7193`
- Totals: 13 conflict paths from the resolution record; exact original hunk total is not recoverable after the merge index and conflict markers were removed; 13 resolved paths.

## Summary table

Hunk counts below are reconstructed from the merge commit's combined-diff regions where available; whole-file delete/edit and binary conflicts are counted as one logical conflict unit. They are not counts of original marker blocks, which were not preserved.

| File | Hunks | Cause | Resolution | Risk (low/med/high) |
|---|---:|---|---|---|
| `.gitignore` | 1 | Same file edited | Combined ignore rules | low |
| `app.py` | 2 | Same code areas edited | Combined endpoints and access controls | high |
| `database.py` | 2 | Schema and database setup edited | Combined schema and location support | high |
| `fronted/src/App.jsx` | 2 | Routes edited on both sides | Combined management and passenger routes | med |
| `fronted/src/components/AdminDashboard.jsx` | 1 | Deleted vs edited | Removed legacy dashboard | low |
| `fronted/src/components/admin-dashboard.css` | 1 | Deleted vs edited | Removed legacy dashboard styles | low |
| `fronted/src/components/admin/AdminLayout.jsx` | 2 | Same layout edited | Kept main navigation/branding | med |
| `fronted/src/components/conductor/ConductorLayout.jsx` | 3 | Same layout edited | Kept main navigation/branding | med |
| `fronted/src/pages/admin/Dashboard.jsx` | 1 | Deleted vs edited | Removed obsolete dashboard page | low |
| `fronted/src/services/dashboardApi.js` | 1 | Deleted vs edited | Removed obsolete service | med |
| `fronted/src/pages/conductor/ConductorDashboard.jsx` | 1 | Same page edited | Kept main live dashboard and feature trip link | high |
| `fronted/vite.config.js` | 1 | Same config edited | Combined hotspot host/port and API proxy | med |
| `smart_matatu.db` | 1 | Binary delete vs edit | Deleted database file | med |

## Details per file

### `.gitignore`
- Cause: same file edited on both sides.
- My branch changed: ignored the local database and related generated/backup files (`c7760b5`, `fc186d9`).
- Main changed: added operational database exclusions (`20b87fb`).
- Resolution: combined both sets of ignore rules.
- Before and after: feature: `*.db`; main: `/AGENTS.md`, `/INTEGRATION.md`; final: both ignore groups are retained.
- Type: independent.
- Follow-up needed: none identified.

### `app.py`
- Cause: overlapping edits to Flask setup and routes.
- My branch changed: passenger QR/trip and live-location APIs (`c4d5071`, `d81e8f4`, `1a2c184`).
- Main changed: admin, conductor, lifecycle, and management APIs (`20b87fb`, `92ac0d5`, `c7c9d9c`, `a793067`, `85388bd`).
- Resolution: combined both route sets; unique feature admin endpoints use `admin_required`, matching main's access-control policy.
- Before and after: feature: `@app.route("/api/matatus/<int:matatu_id>/location"...)`; main: `@app.route("/api/admin/trips"...)`; final: both route families remain, with `@admin_required` on admin routes.
- Type: overlapping.
- Follow-up needed: keep endpoint authorization covered by `test_admin_api.py` and the full backend suite.

### `database.py`
- Cause: overlapping schema and connection changes.
- My branch changed: location fields/history and location indexes (`c4d5071`).
- Main changed: lifecycle, conductor, audit, and transactional schema support (`92ac0d5`, `bcd640c`, `c7c9d9c`).
- Resolution: combined main's schema and transaction setup with feature location data support; supports `SMART_MATATU_DB` and `DATABASE_PATH`.
- Before and after: feature: `DATABASE = os.getenv("DATABASE_PATH", ...)`; main: lifecycle/conductor schema; final: location schema and configurable DB path coexist.
- Type: overlapping.
- Follow-up needed: database migration and fresh-database behavior should remain covered by tests.

### `fronted/src/App.jsx`
- Cause: both branches changed route registration.
- My branch changed: passenger journey/trip routes (`d20b46b`, `1a2c184`).
- Main changed: admin and conductor management routes (`a793067`, `85388bd`).
- Resolution: combined route families so management and passenger flows remain reachable.
- Before and after: feature: `/passenger/:matatuId`; main: `/admin` and `/conductor`; final: both passenger and management route groups are registered.
- Type: independent.
- Follow-up needed: none identified by the recorded checks.

### `fronted/src/components/AdminDashboard.jsx`
- Cause: deleted vs edited; main removed the legacy component while the feature branch had changed it (`d20b46b`; main `c7c9d9c`).
- My branch changed: retained and modified the older admin dashboard component.
- Main changed: removed it in favor of the management-page structure.
- Resolution: deleted the obsolete component, as approved during resolution.
- Before and after: feature: `import { demoDashboardData } from '../services/dashboardApi'`; main: component deleted; final: file absent.
- Type: contradictory.
- Follow-up needed: verify no imports remain; frontend build passed.

### `fronted/src/components/admin-dashboard.css`
- Cause: deleted vs edited; main removed styles belonging to the legacy dashboard while the feature had restyled them (`1a2c184`; main `c7c9d9c`).
- My branch changed: updated the legacy dashboard stylesheet.
- Main changed: removed the obsolete stylesheet with its component.
- Resolution: deleted the stylesheet with the obsolete component.
- Before and after: feature: `.admin-shell{...}`; main: stylesheet deleted; final: file absent.
- Type: contradictory.
- Follow-up needed: no dangling stylesheet imports; frontend build passed.

### `fronted/src/components/admin/AdminLayout.jsx`
- Cause: both branches changed the shared admin shell.
- My branch changed: passenger-era shared shell styling/structure (`1a2c184`).
- Main changed: management navigation and Smart Matatu branding (`c7c9d9c`).
- Resolution: kept main's navigation and branding; used the shared primary token for the accent.
- Before and after: feature used the older admin shell; main retained its management navigation; final: `bg-primary` brand mark and `Matatu <span className="text-primary">Smart</span>` with main navigation.
- Type: overlapping.
- Follow-up needed: none identified.

### `fronted/src/components/conductor/ConductorLayout.jsx`
- Cause: both branches changed the shared conductor shell.
- My branch changed: shared-shell styling (`1a2c184`).
- Main changed: conductor navigation and Smart Matatu branding (`20b87fb`, `c7c9d9c`).
- Resolution: kept main's navigation and branding; used the emerald primary token for the accent.
- Before and after: feature used emerald shell classes; main retained its conductor navigation; final: `bg-primary` brand mark and `text-primary` branding with main navigation.
- Type: overlapping.
- Follow-up needed: none identified.

### `fronted/src/pages/admin/Dashboard.jsx`
- Cause: deleted vs edited; main removed the older page while the feature had changed it (`1a2c184`; main `c7c9d9c`).
- My branch changed: retained the older admin dashboard page.
- Main changed: removed it in favor of dedicated management pages.
- Resolution: deleted the obsolete page, as approved during resolution.
- Before and after: feature: `color: 'primary'` in legacy stats; main: page deleted; final: file absent.
- Type: contradictory.
- Follow-up needed: no dangling route imports; frontend build passed.

### `fronted/src/services/dashboardApi.js`
- Cause: deleted vs edited; main removed the legacy dashboard API service while the feature had changed it (`d20b46b`; main `c7c9d9c`).
- My branch changed: kept the service for the legacy dashboard.
- Main changed: deleted the service along with the old page structure.
- Resolution: removed the obsolete service, as approved during resolution.
- Before and after: feature: `export const demoDashboardData = ...`; main: service deleted; final: file absent; management APIs use the newer service modules.
- Type: contradictory.
- Follow-up needed: frontend build passed; check any future dashboard API references if that page is restored.

### `fronted/src/pages/conductor/ConductorDashboard.jsx`
- Cause: overlapping edits to conductor dashboard behavior and presentation.
- My branch changed: added the trip link within the passenger/location feature work (`1a2c184`).
- Main changed: added live conductor dashboard data and emergency features (`20b87fb`).
- Resolution: kept main's live-data dashboard and retained the feature trip link.
- Before and after: feature: `to="/conductor/trip"`; main: live dashboard data; final: trip link and live dashboard remain.
- Type: overlapping.
- Follow-up needed: live location behavior was explicitly out of scope for changes; the report does not claim device-level verification.

### `fronted/vite.config.js`
- Cause: overlapping development-server and proxy configuration edits.
- My branch changed: network hotspot host/port and hostname-aware API access (`1a2c184`).
- Main changed: API proxy configuration (`92ac0d5`).
- Resolution: combined hotspot host/port settings with the `/api` proxy.
- Before and after: feature: `host: '0.0.0.0', port: 5173`; main: `/api` proxy target; final: host/port plus proxy.
- Type: independent.
- Follow-up needed: hotspot access was not tested on a physical device.

### `smart_matatu.db`
- Cause: binary delete vs edit.
- My branch changed: deleted the local database (`1adbac4`).
- Main changed: modified/tracked a database snapshot (`20b87fb`).
- Resolution: kept the deletion, as approved during resolution.
- Before and after: feature: database deleted; main: binary database snapshot; final: `smart_matatu.db` absent.
- Type: contradictory.
- Follow-up needed: deployments must create/migrate their own database; this is not a source-code migration.

## Non-textual risks

- Main introduced a `smart-matatu` gitlink without a `.gitmodules` mapping. It was removed from the merge result with the user's approval; it is not among the 13 text/binary conflict paths above.
- The unified emerald/slate theme was a follow-up styling change after conflict resolution; `fronted/src/index.css` is an ordinary combined-diff path, not counted as one of the original conflicts.
- Admin API behavior changed to require authentication, and `test_admin_api.py` was adapted after initial tests exposed the mismatch. This test file was a follow-up change, not one of the recorded conflict paths.
- Git's combined merge diff also lists paths added only by main; those are ordinary incoming changes, not counted as conflict paths here.

## Verification

- Conflict markers remaining: none (`git grep -nE '^(<<<<<<< |=======$|>>>>>>> )'` returned no matches).
- Backend tests after resolution: `SMART_MATATU_DB=/tmp/smart-matatu-merge-tests.sqlite3 FLASK_SECRET_KEY=merge-test-only pytest -q` — 208 passed.
- Frontend lint after theme resolution: passed with 10 React warnings.
- Frontend production build after theme resolution: passed; Vite warned that the minified JavaScript bundle exceeds 500 kB.
- `git diff --check HEAD^1 HEAD`: reports one extra blank line at EOF in `tests/test_destination_change_security.py` and four trailing-whitespace lines in `tests/test_proximity_alerts.py`.

## Open questions

- The exact original marker-block hunk total cannot be recovered from the committed merge because the conflict markers and unmerged index stages are no longer present. Per-file counts in the summary are explicitly reconstructed logical/combined-diff regions, not original marker counts.
- No unresolved resolution decisions remain in the recorded merge history.
