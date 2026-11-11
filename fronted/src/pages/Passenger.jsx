import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { BusFront, QrCode, X } from "lucide-react";
import { Html5Qrcode } from "html5-qrcode";
import { api, ApiError } from "../api/client";
import PassengerMap from "../components/passenger/PassengerMap";
import TripSheet from "../components/passenger/TripSheet";
import "../components/passenger/passenger.css";

const initialTrip = { plate: "", route: "", code: "", stages: [] };

function directionBetween(previous, next) {
  const toRadians = (degrees) => degrees * Math.PI / 180;
  const lat1 = toRadians(Number(previous.latitude));
  const lat2 = toRadians(Number(next.latitude));
  const deltaLon = toRadians(Number(next.longitude) - Number(previous.longitude));
  const y = Math.sin(deltaLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLon);
  const degrees = (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
  return `${Math.round(degrees / 45) * 45 % 360}°`;
}

function updatedAgo(location, now) {
  if (!location?.last_updated_at) return "Waiting for update";
  const timestamp = Date.parse(location.last_updated_at);
  if (!Number.isFinite(timestamp)) return "Waiting for update";
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  return `Updated ${seconds}s ago`;
}

function PassengerDashboard({ matatuId }) {
  const navigate = useNavigate();
  const [trip, setTrip] = useState(initialTrip);
  const [history, setHistory] = useState([]);
  const [matatus, setMatatus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [location, setLocation] = useState(null);
  const [locationStatus, setLocationStatus] = useState("reconnecting");
  const [locationError, setLocationError] = useState("");
  const [statusResponse, setStatusResponse] = useState(null);
  const [now, setNow] = useState(() => Date.now());
  const [heading, setHeading] = useState(null);
  const [destination, setDestination] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [scanError, setScanError] = useState("");
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("passenger-theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "passenger-dark" : "passenger-light");
    } catch {
      return "passenger-light";
    }
  });
  const locationRef = useRef(null);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    let active = true;
    const load = matatuId
      ? Promise.all([api.getPassengerTrip(matatuId), api.getPassengerHistory(matatuId)])
      : api.listMatatus();

    load.then((data) => {
      if (!active) return;
      if (matatuId) {
        setTrip(data[0]);
        setHistory(data[1]);
        setConnected(true);
      } else {
        setMatatus(data);
      }
    }).catch((error) => {
      if (active) setLoadError(error.message || "Could not connect to the service.");
    }).finally(() => {
      if (active) setLoading(false);
    });

    return () => { active = false; };
  }, [matatuId]);

  useEffect(() => {
    if (matatuId || !scanOpen) return undefined;
    const scanner = new Html5Qrcode("passenger-qr-reader");
    let disposed = false;
    let scanHandled = false;
    let cleanupPromise;
    let startPromise;

    const stopAndClear = () => {
      cleanupPromise ||= (async () => {
        try { await startPromise; } catch { /* Startup can fail before the camera opens. */ }
        try {
          if (scanner.isScanning) await scanner.stop();
        } catch { /* Continue cleanup if the browser already stopped the camera. */ }
        try { await scanner.clear(); } catch { /* The scanner may already be cleared. */ }
      })();
      return cleanupPromise;
    };

    const handleScan = async (value) => {
      if (disposed || scanHandled) return;
      const match = value.match(/\/passenger\/(\d+)(?:[/?#]|$)/);
      const scannedId = match?.[1] || value.trim().match(/^\d+$/)?.[0];
      if (!scannedId) {
        setScanError("This QR code is not a Smart Matatu vehicle code.");
        return;
      }
      scanHandled = true;
      await stopAndClear();
      if (disposed) return;
      setScanError("");
      setScanOpen(false);
      navigate(`/passenger/${scannedId}`, { replace: true });
    };

    startPromise = scanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 240, height: 240 } },
      (value) => { void handleScan(value); },
      () => {},
    );
    startPromise.catch(() => {
      if (!disposed) setScanError("Camera access is unavailable. Check your browser permissions.");
    });

    return () => {
      disposed = true;
      void stopAndClear();
    };
  }, [matatuId, navigate, scanOpen]);

  const updateLocation = useCallback(async () => {
    try {
      const data = await api.getVehicleStatus(matatuId);
      const next = data.location || null;
      if (!next) {
        setStatusResponse(data);
        setLocationStatus("offline");
        setLocationError("No vehicle location has been reported yet.");
        return;
      }
      const previous = locationRef.current;
      if (previous && (previous.latitude !== next.latitude || previous.longitude !== next.longitude)) {
        setHeading(directionBetween(previous, next));
      }
      locationRef.current = next;
      setLocation(next);
      setLocationError("");
      const age = Date.now() - Date.parse(next.last_updated_at || 0);
      setLocationStatus(next.stale || age > 60_000 ? "offline" : "live");
      setTrip((current) => ({ ...current, plate: data.matatu || current.plate }));
      setStatusResponse(data);
    } catch (error) {
      setLocationStatus(navigator.onLine ? "reconnecting" : "offline");
      setLocationError(error instanceof ApiError && error.status === 404 ? "No vehicle location has been reported yet." : "Could not refresh vehicle location.");
    }
  }, [matatuId]);

  useEffect(() => {
    if (!matatuId) return undefined;
    let active = true;
    let timeout;

    const poll = async () => {
      if (!active) return;
      if (navigator.onLine && document.visibilityState === "visible") await updateLocation();
      else setLocationStatus("offline");
      if (active) timeout = window.setTimeout(poll, 3000);
    };

    poll();
    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [matatuId, updateLocation]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    const online = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  useEffect(() => {
    try { localStorage.setItem("passenger-theme", theme); } catch { /* Storage can be disabled by the browser. */ }
  }, [theme]);

  const activeJourney = useMemo(() => {
    const latest = history[0];
    if (!latest || !statusResponse) return null;
    return statusResponse.passengers?.find((passenger) => passenger.id === latest.id) || null;
  }, [history, statusResponse]);

  const visibleLocationStatus = !isOnline || (location && (location.stale || now - Date.parse(location.last_updated_at || 0) > 60_000))
    ? "offline"
    : locationStatus;

  const register = async (event) => {
    event.preventDefault();
    if (!destination || !matatuId || submitting) return;
    setSubmitting(true);
    setLoadError("");
    try {
      const item = await api.registerPassenger(matatuId, destination);
      setHistory((items) => [item, ...items]);
      setDestination("");
    } catch (error) {
      setLoadError(error instanceof ApiError ? error.message : "Could not register this journey.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!matatuId) {
    return (
      <main className="passenger-root selection-page" data-theme={theme}>
        <div className="selection-shell">
          <header className="selection-header"><span className="brand-mark"><BusFront size={19} /></span><span>Matatu Smart</span></header>
          <section className="selection-card">
            <p className="eyebrow">PASSENGER</p>
            <h1>Choose your matatu</h1>
            <p className="text-base-content/65">Scan the vehicle QR code or select your route to follow its location.</p>
            <button className="btn btn-primary w-full" type="button" onClick={() => { setScanError(""); setScanOpen(true); }}><QrCode size={18} />Scan vehicle QR code</button>
            {scanOpen && <div className="scanner-panel"><div className="mb-2 flex items-center justify-between"><h2 className="font-semibold">Scan QR code</h2><button className="btn btn-ghost btn-circle btn-sm" type="button" onClick={() => setScanOpen(false)} aria-label="Close QR scanner"><X size={18} /></button></div><div id="passenger-qr-reader" className="overflow-hidden rounded-md" />{scanError && <p className="mt-2 text-sm text-error" role="alert">{scanError}</p>}</div>}
            {loading && <div className="space-y-3" aria-label="Loading vehicles"><div className="skeleton h-16 w-full" /><div className="skeleton h-16 w-full" /></div>}
            {loadError && <p className="alert alert-error text-sm" role="alert">{loadError}</p>}
            {!loading && !loadError && !matatus.length && <p className="py-4 text-sm text-base-content/60">No vehicles are registered yet.</p>}
            <div className="space-y-2">
              {matatus.map((matatu) => <button className="vehicle-choice" key={matatu.id} type="button" onClick={() => navigate(`/passenger/${matatu.id}`)}><span className="vehicle-choice-icon"><BusFront size={18} /></span><span className="min-w-0 flex-1 text-left"><strong className="block">{matatu.registration_number}</strong><span className="block truncate text-sm text-base-content/60">{matatu.route_name}</span></span><span className="text-base-content/40">›</span></button>)}
            </div>
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="passenger-root passenger-dashboard" data-theme={theme}>
      <header className="map-topbar">
        <button className="map-back" type="button" onClick={() => navigate("/passenger")} aria-label="Choose another vehicle"><span className="brand-mark"><BusFront size={17} /></span><span className="topbar-copy"><strong>Matatu Smart</strong><span>{trip.route || "Live journey"}</span></span></button>
        <div className="topbar-vehicle"><span className="topbar-plate">{trip.plate || "Vehicle"}</span><span className="topbar-code">{trip.code}</span></div>
      </header>
      <div className="passenger-content">
        {loading ? (
          <div className="dashboard-skeleton" aria-label="Loading live journey"><div className="skeleton map-skeleton" /><div className="skeleton sheet-skeleton" /></div>
        ) : (
          <>
            <PassengerMap stages={trip.stages} location={location} registration={trip.plate} status={visibleLocationStatus} />
            <TripSheet trip={trip} history={history} location={location} journeyProgress={activeJourney} locationStatus={visibleLocationStatus} heading={heading} updatedLabel={updatedAgo(location, now)} error={loadError || locationError} destination={destination} setDestination={setDestination} onRegister={register} submitting={submitting} connected={connected} expanded={expanded} setExpanded={setExpanded} theme={theme} setTheme={setTheme} isOnline={isOnline} />
          </>
        )}
      </div>
    </main>
  );
}

export default function Passenger() {
  const { matatuId } = useParams();
  return <PassengerDashboard key={matatuId || "vehicle-selection"} matatuId={matatuId} />;
}
