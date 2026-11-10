import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BusFront,
  CalendarDays,
  ChevronDown,
  CircleHelp,
  Gauge,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  MoreHorizontal,
  Navigation,
  Plus,
  QrCode,
  Route as RouteIcon,
  Search,
  Settings,
  ShieldCheck,
  Users,
  X,
  Bell,
} from "lucide-react";
import "./admin-dashboard.css";

const nav = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "fleet", label: "Fleet & Matatus", icon: BusFront },
  { id: "routes", label: "Route Management", icon: RouteIcon },
  { id: "trips", label: "Trip Monitoring", icon: Navigation },
  { id: "users", label: "User Management", icon: Users },
];
const titles = {
  overview: ["Overview", "Here's what's happening across your fleet today."],
  fleet: [
    "Fleet & Matatus",
    "Manage vehicles, capacity, assignments and availability.",
  ],
  routes: [
    "Route Management",
    "Organise routes, stages and route assignments.",
  ],
  trips: [
    "Trip Monitoring",
    "Review active journeys, distance and estimated arrivals.",
  ],
  users: [
    "User Management",
    "Review registered users and their platform roles.",
  ],
};
const money = (n) => new Intl.NumberFormat("en-KE").format(n);

function Status({ value }) {
  return (
    <span
      className={`status status-${value.toLowerCase().replaceAll(" ", "-")}`}
    >
      {value}
    </span>
  );
}
function Heading({ title, description, action }) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
function Stat({ label, value, note, icon: Icon, tone }) {
  return (
    <article className="stat-card">
      <div className={`stat-icon ${tone}`}>
        <Icon size={19} />
      </div>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>
        <ArrowUpRight size={13} /> {note}
      </small>
    </article>
  );
}
function SearchBar({ value, onChange, placeholder }) {
  return (
    <div className="search-bar">
      <Search size={16} />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}
function Overview({ data, go }) {
  const active = data.trips.filter((t) => t.status === "In progress");
  return (
    <>
      <div className="stats-grid">
        <Stat
          label="Registered matatus"
          value={money(data.stats.matatus)}
          note="Vehicles in the system"
          icon={BusFront}
          tone="blue"
        />
        <Stat
          label="Active trips"
          value={money(data.stats.activeTrips)}
          note="Journeys currently running"
          icon={Navigation}
          tone="green"
        />
        <Stat
          label="Registered users"
          value={money(data.stats.users)}
          note="All platform roles"
          icon={Users}
          tone="purple"
        />
        <Stat
          label="Available vehicles"
          value={money(data.stats.availableVehicles)}
          note="Ready for assignment"
          icon={Gauge}
          tone="amber"
        />
      </div>
      <div className="overview-grid">
        <section className="panel">
          <Heading
            title="Live trip overview"
            description="Sample trip records for the dashboard prototype"
            action={
              <button className="link-button" onClick={() => go("trips")}>
                View all trips →
              </button>
            }
          />
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Matatu</th>
                  <th>Route</th>
                  <th>Progress</th>
                  <th>ETA</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {active.slice(0, 4).map((t) => (
                  <tr key={t.id}>
                    <td>
                      <b>{t.registration}</b>
                      <small>{t.id}</small>
                    </td>
                    <td>{t.route}</td>
                    <td>
                      <div className="progress">
                        <span style={{ width: `${t.progress}%` }} />
                      </div>
                      <small>{t.progress}%</small>
                    </td>
                    <td>
                      <b>{t.eta}</b>
                      <small>{t.distanceRemaining} remaining</small>
                    </td>
                    <td>
                      <Status value={t.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="disclaimer">
            <Activity size={14} /> Sample values only — connect GPS and backend
            APIs for live information.
          </p>
        </section>
        <section className="panel">
          <Heading
            title="Operational alerts"
            description="Items that may need attention"
          />
          <div className="alerts">
            {data.alerts.map((a) => (
              <div className="alert" key={a.id}>
                <span className={`alert-icon ${a.level}`}>
                  <AlertTriangle size={16} />
                </span>
                <div>
                  <b>{a.title}</b>
                  <p>{a.description}</p>
                  <small>{a.time}</small>
                </div>
              </div>
            ))}
          </div>
          <button className="secondary full" onClick={() => go("trips")}>
            Review operations
          </button>
        </section>
      </div>
      <section className="panel">
        <Heading
          title="Fleet status"
          description="Availability snapshot across registered vehicles"
          action={
            <button className="link-button" onClick={() => go("fleet")}>
              Manage fleet →
            </button>
          }
        />
        <div className="fleet-summary">
          <div>
            <i className="dot available-dot" />
            Available<strong>{data.stats.availableVehicles}</strong>
          </div>
          <div>
            <i className="dot trip-dot" />
            On trip<strong>{data.stats.activeTrips}</strong>
          </div>
          <div>
            <i className="dot maintenance-dot" />
            Maintenance<strong>{data.stats.maintenanceVehicles}</strong>
          </div>
          <div className="meter">
            <div>
              <span
                style={{
                  width: `${data.stats.matatus ? Math.round((data.stats.availableVehicles / data.stats.matatus) * 100) : 0}%`,
                }}
              />
            </div>
            <small>
              {data.stats.matatus
                ? Math.round(
                    (data.stats.availableVehicles / data.stats.matatus) * 100,
                  )
                : 0}
              % available
            </small>
          </div>
        </div>
      </section>
    </>
  );
}
function Fleet({ data, search, setSearch, onGenerateQr }) {
  const rows = data.matatus.filter((x) =>
    `${x.registration} ${x.route}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <section className="panel">
      <Heading
        title="Fleet & Matatus"
        description="Vehicle registry and operational status"
        action={
          <button
            className="primary"
            onClick={() =>
              window.alert(
                "Vehicle creation is not available in the existing backend.",
              )
            }
          >
            <Plus size={15} /> Add matatu
          </button>
        }
      />
      <div className="toolbar">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search registration or route..."
        />
        <button className="secondary">
          <CalendarDays size={15} /> All dates <ChevronDown size={14} />
        </button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Registration</th>
              <th>Route</th>
              <th>Passengers</th>
              <th>GPS</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.id}>
                <td>
                  <b>{m.registration}</b>
                  <small>Vehicle #{m.id}</small>
                </td>
                <td>{m.route}</td>
                <td>{m.passenger_count}</td>
                <td>
                  {m.location
                    ? m.location.stale
                      ? "Stale"
                      : "Current"
                    : "Not initialized"}
                </td>
                <td>
                  <Status value={m.status} />
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`Generate QR code for ${m.registration}`}
                    title="Generate passenger QR code"
                    onClick={() => onGenerateQr(m)}
                  >
                    <QrCode size={18} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label={`More options for ${m.registration}`}
                    onClick={() =>
                      window.alert(
                        "Vehicle actions are not available in the existing backend.",
                      )
                    }
                  >
                    <MoreHorizontal size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && (
        <p className="empty">No vehicles match that search.</p>
      )}
      <small className="table-foot">
        Showing {rows.length} of {data.matatus.length} vehicles
      </small>
    </section>
  );
}

function QrDialog({ qr, loading, error, onClose }) {
  if (!qr && !loading && !error) return null;
  return (
    <div className="qr-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="qr-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="qr-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          className="qr-modal-close"
          aria-label="Close QR code dialog"
          onClick={onClose}
        >
          <X size={18} />
        </button>
        <h2 id="qr-dialog-title">Passenger QR code</h2>
        {loading && <p>Generating QR code...</p>}
        {error && <p className="qr-modal-error">{error}</p>}
        {qr && (
          <>
            <p className="qr-modal-meta">
              <b>{qr.registration}</b>
              <span>{qr.route}</span>
            </p>
            <img
              className="qr-image"
              src={qr.qr_data_url}
              alt={`Passenger QR code for ${qr.registration}`}
            />
            <p className="qr-url">{qr.qr_url}</p>
            <a
              className="primary qr-open-link"
              href={qr.qr_url}
              target="_blank"
              rel="noreferrer"
            >
              Open passenger page
            </a>
          </>
        )}
      </section>
    </div>
  );
}
function RoutesPage({ data, search, setSearch }) {
  const rows = data.routes.filter((x) =>
    `${x.name} ${x.origin} ${x.destination}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <section className="panel">
      <Heading
        title="Route Management"
        description="Manage corridors, stages and route availability"
        action={
          <button
            className="primary"
            onClick={() =>
              window.alert(
                "Route creation is not available in the existing backend.",
              )
            }
          >
            <Plus size={15} /> Add route
          </button>
        }
      />
      <div className="toolbar">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search routes or endpoints..."
        />
      </div>
      <div className="route-grid">
        {rows.map((r) => (
          <article className="route-card" key={r.name}>
            <div className="route-top">
              <span className="route-icon">
                <RouteIcon size={18} />
              </span>
              <Status value={r.status} />
            </div>
            <h3>{r.name}</h3>
            <p className="route-end">
              <MapPin size={14} /> {r.origin || "Unknown"} <span>→</span>{" "}
              {r.destination || "Unknown"}
            </p>
            <div className="route-metrics">
              <div>
                <small>Distance</small>
                <b>{r.distance_km == null ? "—" : `${r.distance_km} km`}</b>
              </div>
              <div>
                <small>Stages</small>
                <b>{r.stage_count}</b>
              </div>
              <div>
                <small>Matatus</small>
                <b>{r.vehicle_count}</b>
              </div>
            </div>
            <button
              className="secondary full"
              onClick={() =>
                window.alert(
                  `${r.stage_count} stages are available through the backend route data.`,
                )
              }
            >
              View route details
            </button>
          </article>
        ))}
      </div>
      {rows.length === 0 && (
        <p className="empty">No routes match that search.</p>
      )}
    </section>
  );
}
function Trips({ data, search, setSearch }) {
  const rows = data.trips.filter((t) =>
    `${t.id} ${t.registration} ${t.route}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <section className="panel">
      <Heading
        title="Trip Monitoring"
        description="Journey status, GPS freshness and passenger requests"
        action={
          <span className="demo-chip">
            <i /> Live backend feed
          </span>
        }
      />
      <div className="toolbar">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search vehicle or route..."
        />
        <button className="secondary">
          <Activity size={15} /> All statuses <ChevronDown size={14} />
        </button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Trip / Matatu</th>
              <th>Route</th>
              <th>Passengers</th>
              <th>GPS update</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id}>
                <td>
                  <b>{t.id}</b>
                  <small>{t.registration}</small>
                </td>
                <td>{t.route}</td>
                <td>{t.passenger_count}</td>
                <td>
                  {t.location
                    ? t.location.last_updated_at || "Available"
                    : "Not initialized"}
                </td>
                <td>
                  <Status value={t.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && (
        <p className="empty">No trips match that search.</p>
      )}
      <small className="table-foot">
        Showing {rows.length} of {data.trips.length} trips
      </small>
    </section>
  );
}
function UsersPage({ data, search, setSearch }) {
  const rows = data.users.filter((u) =>
    `${u.name} ${u.email} ${u.role}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <section className="panel">
      <Heading
        title="User Management"
        description="Registered accounts and access roles"
        action={
          <button
            className="primary"
            onClick={() =>
              window.alert(
                "Invite User form will be connected to the backend later.",
              )
            }
          >
            <Plus size={15} /> Add user
          </button>
        }
      />
      <div className="toolbar">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search name, email or role..."
        />
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Joined</th>
              <th>Account status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id}>
                <td>
                  <div className="user-name">
                    <span>
                      {u.name
                        .split(" ")
                        .map((n) => n[0])
                        .slice(0, 2)
                        .join("")}
                    </span>
                    <b>{u.name}</b>
                  </div>
                </td>
                <td>{u.email}</td>
                <td>
                  <span className="role-label">{u.role}</span>
                </td>
                <td>{u.joined}</td>
                <td>
                  <Status value={u.status} />
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`More options for ${u.name}`}
                    onClick={() =>
                      window.alert("User actions will be connected to the API.")
                    }
                  >
                    <MoreHorizontal size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && (
        <p className="empty">No users match that search.</p>
      )}
      <small className="table-foot">
        Showing {rows.length} of {data.users.length} sample users
      </small>
    </section>
  );
}

export default function AdminDashboard() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const [page, setPage] = useState("overview"),
    [search, setSearch] = useState(""),
    [menuOpen, setMenuOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [qr, setQr] = useState(null);
  const [qrLoading, setQrLoading] = useState(false);
  const [qrError, setQrError] = useState("");
  useEffect(() => {
    api
      .getAdminDashboard()
      .then(setData)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false));
  }, []);
  const [title, description] = titles[page];
  const go = (id) => {
    setPage(id);
    setSearch("");
    setMenuOpen(false);
  };
  async function generateQr(matatu) {
    setQr(null);
    setQrError("");
    setQrLoading(true);
    try {
      setQr(await api.getAdminMatatuQr(matatu.id));
    } catch (requestError) {
      setQrError(requestError.message || "Could not generate the QR code.");
    } finally {
      setQrLoading(false);
    }
  }
  if (loading)
    return (
      <div className="admin-shell">
        <main className="admin-main">
          <div className="page-content">
            <p>Loading admin data...</p>
          </div>
        </main>
      </div>
    );
  if (error || !data)
    return (
      <div className="admin-shell">
        <main className="admin-main">
          <div className="page-content">
            <p className="empty">{error || "No admin data is available."}</p>
          </div>
        </main>
      </div>
    );
  return (
    <div className="admin-shell">
      {menuOpen && (
        <button
          className="mobile-overlay"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`admin-sidebar ${menuOpen ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">
            <BusFront size={22} />
          </span>
          <div>
            <b>Matatu Smart</b>
            <small>ADMIN CONSOLE</small>
          </div>
          <button
            className="mobile-close icon-button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav>
          {nav.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${page === id ? "selected" : ""}`}
              onClick={() => go(id)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === "trips" && (
                <i className="nav-count">{data.stats.activeTrips}</i>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="help-card">
          <CircleHelp size={20} />
          <b>Need assistance?</b>
          <p>Check the operations guide or contact the system team.</p>
          <button
            onClick={() => window.alert("Help content will be added later.")}
          >
            Open help centre →
          </button>
        </div>
        <div className="sidebar-bottom">
          <button
            className="nav-item"
            onClick={() =>
              window.alert("Settings will be added in a later phase.")
            }
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>
          <button className="nav-item" onClick={handleLogout}>
            <LogOut size={18} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <header className="topbar">
          <button
            className="mobile-menu icon-button"
            aria-label="Open menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={21} />
          </button>
          <div className="breadcrumb">
            <span>Smart Matatu</span>
            <i>/</i>
            <b>{title}</b>
          </div>
          <div className="top-actions">
            <span className="environment">
              <i /> Demo environment
            </span>
            <button
              className="icon-button notification"
              aria-label="Notifications"
              onClick={() => go("trips")}
            >
              <Bell size={18} />
            </button>
            <div className="top-divider" />
            <div className="admin-user">
              <span>AD</span>
              <div>
                <b>Administrator</b>
                <small>System Admin</small>
              </div>
              <ChevronDown size={14} />
            </div>
          </div>
        </header>
        <div className="page-content">
          <div className="page-heading">
            <div>
              <small>SMART MATATU / ADMIN</small>
              <h1>{title}</h1>
              <p>{description}</p>
            </div>
            {page === "overview" && (
              <button
                className="secondary"
                onClick={() =>
                  window.alert(
                    "Date filters will be connected to reporting APIs.",
                  )
                }
              >
                <CalendarDays size={15} /> Today <ChevronDown size={14} />
              </button>
            )}
          </div>
          {page === "overview" && <Overview data={data} go={go} />}{" "}
          {page === "fleet" && (
            <Fleet
              data={data}
              search={search}
              setSearch={setSearch}
              onGenerateQr={generateQr}
            />
          )}{" "}
          {page === "routes" && (
            <RoutesPage data={data} search={search} setSearch={setSearch} />
          )}{" "}
          {page === "trips" && (
            <Trips data={data} search={search} setSearch={setSearch} />
          )}{" "}
          {page === "users" && (
            <UsersPage data={data} search={search} setSearch={setSearch} />
          )}
          <footer className="page-footer">
            <span>© 2026 Matatu Smart · Admin Console</span>
            <span>
              <ShieldCheck size={14} /> Access-controlled area · Prototype UI
            </span>
          </footer>
        </div>
      </main>
      <QrDialog
        qr={qr}
        loading={qrLoading}
        error={qrError}
        onClose={() => {
          setQr(null);
          setQrError("");
        }}
      />
    </div>
  );
}
