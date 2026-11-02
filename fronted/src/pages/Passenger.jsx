import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Bus, History, ChevronUp, ChevronDown, QrCode, X } from "lucide-react";
import { Html5Qrcode } from "html5-qrcode";
import { api, ApiError } from "../api/client";

export default function Passenger() {
  const { matatuId } = useParams();
  const navigate = useNavigate();
  const [dest, setDest] = useState("");
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(false);
  const [trip, setTrip] = useState({
    plate: "",
    route: "",
    code: "",
    stages: [],
  });
  const [history, setHistory] = useState([]);
  const [matatus, setMatatus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [scanError, setScanError] = useState("");
  const scannerRef = useRef(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    const load = matatuId
      ? Promise.all([
          api.getPassengerTrip(matatuId),
          api.getPassengerHistory(matatuId),
        ])
      : api.listMatatus();

    load
      .then((data) => {
        if (!active) return;
        if (matatuId) {
          setTrip(data[0]);
          setHistory(data[1]);
          setConnected(true);
        } else {
          setMatatus(data);
        }
      })
      .catch((requestError) => {
        if (active)
          setError(requestError.message || "Could not connect to the backend.");
      })
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [matatuId]);

  useEffect(() => {
    if (matatuId || !scanOpen) return undefined;

    const scanner = new Html5Qrcode("passenger-qr-reader");
    scannerRef.current = scanner;
    setScanError("");

    const handleScan = (value) => {
      const match = value.match(/\/passenger\/(\d+)(?:[/?#]|$)/);
      const scannedMatatuId = match?.[1] || value.trim().match(/^\d+$/)?.[0];

      if (!scannedMatatuId) {
        setScanError("This QR code is not a Smart Matatu vehicle code.");
        return;
      }

      setScanOpen(false);
      navigate(`/passenger/${scannedMatatuId}`);
    };

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        handleScan,
        () => {},
      )
      .catch(() =>
        setScanError(
          "Camera access was unavailable. Check your browser permissions.",
        ),
      );

    return () => {
      if (scanner.isScanning) {
        scanner.stop().catch(() => {});
      }
      scanner.clear().catch(() => {});
      scannerRef.current = null;
    };
  }, [matatuId, navigate, scanOpen]);

  const register = async (e) => {
    e.preventDefault();
    if (!dest || !matatuId || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const item = await api.registerPassenger(matatuId, dest);
      setHistory([item, ...history]);
      setDest("");
      setOpen(true);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Registration failed.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!matatuId) {
    return (
      <div className="min-h-screen bg-slate-950 text-white p-4 flex items-center justify-center">
        <div className="max-w-md w-full space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center gap-2">
            <Bus className="w-5 text-blue-500" />
            <span className="font-bold">Matatu Smart</span>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div>
              <h1 className="font-bold">Choose your matatu</h1>
              <p className="text-sm text-slate-400 mt-1">
                Select a vehicle to view its live route.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setScanOpen(true)}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 rounded-lg p-3 text-sm font-medium"
            >
              <QrCode size={18} /> Scan vehicle QR code
            </button>
            {scanOpen && (
              <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold">Scan QR code</p>
                  <button
                    type="button"
                    onClick={() => setScanOpen(false)}
                    aria-label="Close QR scanner"
                    className="text-slate-400 hover:text-white"
                  >
                    <X size={18} />
                  </button>
                </div>
                <div
                  id="passenger-qr-reader"
                  className="overflow-hidden rounded-md"
                />
                {scanError && (
                  <p className="mt-2 text-xs text-rose-400" role="alert">
                    {scanError}
                  </p>
                )}
              </div>
            )}
            {loading && (
              <p className="text-sm text-slate-400">Loading vehicles...</p>
            )}
            {error && (
              <p className="text-sm text-rose-400" role="alert">
                {error}
              </p>
            )}
            {!loading && !error && matatus.length === 0 && (
              <p className="text-sm text-slate-400">
                No vehicles are registered yet.
              </p>
            )}
            <div className="space-y-2">
              {matatus.map((matatu) => (
                <button
                  key={matatu.id}
                  type="button"
                  onClick={() => navigate(`/passenger/${matatu.id}`)}
                  className="w-full text-left bg-slate-950 border border-slate-800 rounded-lg p-3 hover:border-blue-500"
                >
                  <span className="block font-semibold">
                    {matatu.registration_number}
                  </span>
                  <span className="text-xs text-slate-400">
                    {matatu.route_name}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-4 flex flex-col justify-between pb-20">
      <div className="max-w-md w-full space-y-4 mx-auto">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex justify-between items-center">
          <span className="font-bold flex items-center gap-2">
            <Bus className="w-5 text-blue-500" /> Matatu Smart
          </span>
          <span
            className={`text-xs px-2.5 py-1 rounded-full ${connected ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}
          >
            {connected ? "Live" : "Offline"}
          </span>
        </div>

        <div className="grid grid-cols-3 bg-slate-900 border border-slate-800 rounded-xl p-3 text-center text-sm font-bold">
          <div>
            <p className="text-[10px] text-slate-500">PLATE</p>
            {trip.plate || "---"}
          </div>
          <div className="border-x border-slate-800">
            <p className="text-[10px] text-slate-500">ROUTE</p>
            {trip.route || "---"}
          </div>
          <div>
            <p className="text-[10px] text-slate-500">TRIP</p>
            <span className="text-blue-400">{trip.code || "---"}</span>
          </div>
        </div>

        <form
          onSubmit={register}
          className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3"
        >
          <h2 className="text-sm font-semibold">Select Destination</h2>
          <select
            value={dest}
            onChange={(e) => setDest(e.target.value)}
            disabled={!connected}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm disabled:opacity-50"
            required
          >
            <option value="" disabled>
              {connected ? "Select stage..." : "Please connect to backend"}
            </option>
            {trip.stages?.map((stage) => (
              <option key={stage.id} value={stage.id}>
                {stage.name}
              </option>
            ))}
          </select>
          <button
            disabled={!connected || submitting}
            className="w-full bg-blue-600 hover:bg-blue-500 py-2.5 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {submitting ? "Registering..." : "Register Journey"}
          </button>
          {error && (
            <p className="text-xs text-rose-400" role="alert">
              {error}
            </p>
          )}
        </form>
      </div>

      <div className="fixed bottom-0 left-0 right-0 flex justify-center p-3 bg-slate-950/80">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl">
          <button
            onClick={() => setOpen(!open)}
            className="w-full p-3 flex justify-between items-center text-sm"
          >
            <span className="flex items-center gap-2">
              <History className="w-4 text-slate-400" /> History (
              {history.length})
            </span>
            {open ? (
              <ChevronDown className="w-4" />
            ) : (
              <ChevronUp className="w-4" />
            )}
          </button>
          {open && (
            <div className="p-3 pt-0 space-y-2 max-h-48 overflow-y-auto border-t border-slate-800 text-sm">
              {!connected ? (
                <p className="text-xs text-amber-400 text-center py-3">
                  Please connect to backend
                </p>
              ) : history.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-3">
                  No history yet.
                </p>
              ) : (
                history.map((item, i) => (
                  <div
                    key={i}
                    className="flex justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs"
                  >
                    <span>{item.destination}</span>
                    <span className="text-blue-400">{item.status}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
