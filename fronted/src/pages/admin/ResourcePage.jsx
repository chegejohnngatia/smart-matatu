import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { AlertCircle, Bus, Map, QrCode, Route, X } from "lucide-react";
import { api } from "../../api/client";

const pageDetails = {
  "/admin/matatus": {
    title: "Matatu Management",
    description:
      "Manage vehicle registration, fleet details, and vehicle status.",
    resource: "matatus",
  },
  "/admin/routes": {
    title: "Route Management",
    description: "Manage transport routes, stages, and route information.",
    resource: "routes",
  },
  "/admin/users": {
    title: "User Management",
    description: "Review passenger, conductor, and administrator accounts.",
    resource: "users",
  },
  "/admin/trips": {
    title: "Trip Management",
    description: "Monitor trips, assignments, and trip statuses.",
    resource: "trips",
  },
  "/admin/requests": {
    title: "Destination Requests",
    description: "Review passenger destination requests and their statuses.",
    resource: "destination requests",
  },
};

export default function ResourcePage() {
  const { pathname } = useLocation();
  const page = pageDetails[pathname] ?? {
    title: "Management",
    description: "Manage Smart Matatu platform records.",
    resource: "records",
  };
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [qr, setQr] = useState(null);
  const [qrLoading, setQrLoading] = useState(false);
  const [qrError, setQrError] = useState("");

  useEffect(() => {
    const loaders = {
      matatus: api.getAdminMatatus,
      routes: api.getAdminRoutes,
      trips: api.getAdminTrips,
    };
    const load = loaders[page.resource];

    if (!load) {
      setLoading(false);
      return undefined;
    }

    setLoading(true);
    setError("");
    load()
      .then(setRecords)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false));

    return undefined;
  }, [page.resource]);

  const Icon =
    page.resource === "matatus"
      ? Bus
      : page.resource === "routes"
        ? Route
        : Map;

  async function generateQr(record) {
    setQr(null);
    setQrError("");
    setQrLoading(true);
    try {
      setQr(await api.getAdminMatatuQr(record.id));
    } catch (requestError) {
      setQrError(requestError.message || "Could not generate the QR code.");
    } finally {
      setQrLoading(false);
    }
  }

  function closeQr() {
    setQr(null);
    setQrError("");
  }

  function renderRecords() {
    if (loading) {
      return (
        <div className="flex items-center justify-center gap-3 py-12 text-sm text-slate-500">
          <span className="loading loading-spinner loading-md" /> Loading live
          records...
        </div>
      );
    }
    if (error) {
      return (
        <div role="alert" className="alert alert-error alert-soft">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      );
    }
    if (records.length === 0) {
      return (
        <div className="py-12 text-center text-sm text-slate-500">
          No live {page.resource} records were found.
        </div>
      );
    }
    if (page.resource === "matatus") {
      return (
        <div className="overflow-x-auto">
          <table className="table table-zebra">
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
              {records.map((record) => (
                <tr key={record.id}>
                  <td className="font-semibold">{record.registration}</td>
                  <td>{record.route}</td>
                  <td>{record.passenger_count}</td>
                  <td>
                    {record.location
                      ? record.location.stale
                        ? "Stale"
                        : "Current"
                      : "Not initialized"}
                  </td>
                  <td>{record.status}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      title="Generate passenger QR code"
                      aria-label={`Generate QR code for ${record.registration}`}
                      onClick={() => generateQr(record)}
                    >
                      <QrCode size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    if (page.resource === "routes") {
      return (
        <div className="overflow-x-auto">
          <table className="table table-zebra">
            <thead>
              <tr>
                <th>Route</th>
                <th>Origin</th>
                <th>Destination</th>
                <th>Stages</th>
                <th>Matatus</th>
                <th>Distance</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.name}>
                  <td className="font-semibold">{record.name}</td>
                  <td>{record.origin || "—"}</td>
                  <td>{record.destination || "—"}</td>
                  <td>{record.stage_count}</td>
                  <td>{record.vehicle_count}</td>
                  <td>
                    {record.distance_km == null
                      ? "—"
                      : `${record.distance_km} km`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    return (
      <div className="overflow-x-auto">
        <table className="table table-zebra">
          <thead>
            <tr>
              <th>Trip</th>
              <th>Matatu</th>
              <th>Route</th>
              <th>Passengers</th>
              <th>GPS update</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td className="font-semibold">{record.id}</td>
                <td>{record.registration}</td>
                <td>{record.route}</td>
                <td>{record.passenger_count}</td>
                <td>{record.location?.last_updated_at || "Not initialized"}</td>
                <td>{record.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
          Administration
        </p>
        <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
          {page.title}
        </h2>
        <p className="mt-2 text-sm text-slate-500">{page.description}</p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
            <Icon size={24} />
          </div>
          <div>
            <h3 className="text-lg font-bold">Live {page.resource}</h3>
            <p className="text-sm text-slate-500">
              Loaded from the Flask backend.
            </p>
          </div>
        </div>
        {renderRecords()}
      </div>
      {(qr || qrLoading || qrError) && (
        <dialog
          className="modal modal-open"
          open
          aria-labelledby="qr-dialog-title"
        >
          <div className="modal-box max-w-sm text-center">
            <button
              type="button"
              className="btn btn-ghost btn-sm btn-circle absolute right-3 top-3"
              aria-label="Close QR code dialog"
              onClick={closeQr}
            >
              <X size={17} />
            </button>
            <h3 id="qr-dialog-title" className="text-lg font-bold">
              Passenger QR code
            </h3>
            {qrLoading && (
              <p className="py-8 text-sm text-slate-500">
                Generating QR code...
              </p>
            )}
            {qrError && (
              <p role="alert" className="py-8 text-sm text-error">
                {qrError}
              </p>
            )}
            {qr && (
              <>
                <p className="py-3 text-sm text-slate-500">
                  <strong className="block text-slate-900">
                    {qr.registration}
                  </strong>
                  {qr.route}
                </p>
                <img
                  className="mx-auto h-60 w-60"
                  src={qr.qr_data_url}
                  alt={`Passenger QR code for ${qr.registration}`}
                />
                <p className="break-all py-3 text-xs text-slate-500">
                  {qr.qr_url}
                </p>
                <a
                  className="btn btn-primary"
                  href={qr.qr_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open passenger page
                </a>
              </>
            )}
          </div>
          <form method="dialog" className="modal-backdrop">
            <button type="button" onClick={closeQr}>
              close
            </button>
          </form>
        </dialog>
      )}
    </div>
  );
}
