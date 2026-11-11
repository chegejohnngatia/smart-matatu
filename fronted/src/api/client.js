const defaultApiBaseUrl = `${window.location.protocol}//${window.location.hostname}:5000/api`;
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status, fields = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fields = fields;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = data.error || {};
    throw new ApiError(
      error.message || `Request failed with status ${response.status}`,
      response.status,
      error.fields,
    );
  }
  return data;
}

export const api = {
  listMatatus: () => request("/matatus"),
  getAdminMatatus: () => request("/admin/matatus"),
  getAdminRoutes: () => request("/admin/routes"),
  getAdminTrips: () => request("/admin/trips"),
  getAdminMatatuQr: (matatuId) => request(`/admin/matatus/${matatuId}/qr`),
  getAdminDashboard: async () => {
    const data = await request("/admin/dashboard");
    return {
      ...data,
      stats: {
        matatus: data.stats.matatus,
        activeTrips: data.stats.active_trips,
        availableVehicles: data.stats.available_vehicles,
        maintenanceVehicles: data.stats.maintenance_vehicles,
        users: data.stats.users,
      },
      matatus: data.matatus.map((matatu) => ({
        ...matatu,
        passengerCount: matatu.passenger_count,
      })),
      routes: data.routes.map((route) => ({
        ...route,
        stageCount: route.stage_count,
        vehicleCount: route.vehicle_count,
      })),
      trips: data.trips.map((trip) => ({
        ...trip,
        matatuId: trip.matatu_id,
        passengerCount: trip.passenger_count,
      })),
    };
  },
  getPassengerTrip: (matatuId) =>
    request(`/passenger/trip-info?matatu_id=${matatuId}`),
  getVehicleStatus: (matatuId) => request(`/vehicle-status/${matatuId}`),
  getPassengerHistory: (matatuId) =>
    request(`/passenger/history?matatu_id=${matatuId}`),
  registerPassenger: (matatuId, destinationStageId) =>
    request("/passenger/register", {
      method: "POST",
      body: JSON.stringify({
        matatu_id: Number(matatuId),
        destination_stage_id: Number(destinationStageId),
      }),
    }),
};
