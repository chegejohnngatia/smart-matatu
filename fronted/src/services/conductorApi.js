
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '';

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
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error || `Could not load requests: ${response.status}`
    );
  }

  return data.requests || [];
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
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error || `Could not resolve request: ${response.status}`
    );
  }

  return data;
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

// Acknowledge an emergency alert using the authenticated session and CSRF token.
export async function acknowledgeEmergencyAlert(alertId, csrfToken) {
  if (!csrfToken) {
    throw new Error('Your session has expired. Please log in again.');
  }

  const response = await fetch(
    `${API_BASE_URL}/api/conductor/emergency-alerts/${alertId}/acknowledge`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
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

export async function getConductorQRCode() {
  const response = await fetch(
    `${API_BASE_URL}/api/conductor/qr-code`,
    {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error ||
      data.message ||
      `Could not generate QR code: ${response.status}`
    );
  }

  return data;
}
