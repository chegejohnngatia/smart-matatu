const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api"
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
  getPassengerTrip: (matatuId) =>
    request(`/passenger/trip-info?matatu_id=${matatuId}`),
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
