
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

const MATATU_ID =
  import.meta.env.VITE_CONDUCTOR_MATATU_ID || "1";

export async function getConductorDashboard() {
  const response = await fetch(
    `${API_BASE_URL}/api/conductor/dashboard/${MATATU_ID}`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));

    throw new Error(
      errorData.error || `Dashboard request failed: ${response.status}`
    );
  }

  return response.json();
}


export async function getDestinationChangeRequests() {
  const response = await fetch(
    `${API_BASE_URL}/api/conductor/destination-change-requests/${MATATU_ID}`
  )

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      data.error || `Could not load requests: ${response.status}`
    )
  }

  return data.requests || []
}

export async function decideDestinationChangeRequest(requestId, action) {
  const response = await fetch(
    `${API_BASE_URL}/api/conductor/destination-change-requests/${requestId}/decision`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ action }),
    }
  )

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      data.error || `Could not resolve request: ${response.status}`
    )
  }

  return data
}


export async function getConductorEmergencyAlerts() {
  const response = await fetch(
    `${API_BASE_URL}/api/conductor/emergency-alerts/${MATATU_ID}`
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error || `Could not load emergency alerts: ${response.status}`
    );
  }

  return data;
}

export async function acknowledgeEmergencyAlert(alertId) {
  const response = await fetch(
    `${API_BASE_URL}/api/conductor/emergency-alerts/${alertId}/acknowledge`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        matatu_id: Number(MATATU_ID),
      }),
    }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error || `Could not acknowledge alert: ${response.status}`
    );
  }

  return data;
}


