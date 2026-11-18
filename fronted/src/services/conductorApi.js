const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '';

const DEFAULT_MATATU_ID =
  import.meta.env.VITE_CONDUCTOR_MATATU_ID || "1";

export async function getConductorDashboard(matatuId) {
  const url = matatuId
    ? `${API_BASE_URL}/api/conductor/dashboard/${matatuId}`
    : `${API_BASE_URL}/api/conductor/dashboard`;
  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));

    throw new Error(
      errorData.error || `Dashboard request failed: ${response.status}`
    );
  }

  return response.json();
}

export async function getDestinationChangeRequests(matatuId) {
  const url = matatuId
    ? `${API_BASE_URL}/api/conductor/destination-change-requests/${matatuId}`
    : `${API_BASE_URL}/api/conductor/destination-change-requests`;
  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error || `Could not load requests: ${response.status}`
    );
  }

  return data.requests || [];
}

export async function decideDestinationChangeRequest(requestId, action, csrfToken) {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/conductor/destination-change-requests/${requestId}/decision`,
    {
      method: 'POST',
      credentials: 'include',
      headers,
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

export async function getConductorEmergencyAlerts(matatuId) {
  const url = matatuId
    ? `${API_BASE_URL}/api/conductor/emergency-alerts/${matatuId}`
    : `${API_BASE_URL}/api/conductor/emergency-alerts`;
  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.error || `Could not load emergency alerts: ${response.status}`
    );
  }

  return data;
}

export async function acknowledgeEmergencyAlert(alertId, csrfToken, matatuId = DEFAULT_MATATU_ID) {
  if (!csrfToken) {
    throw new Error('Your session has expired. Please log in again.');
  }

  const targetId = matatuId || DEFAULT_MATATU_ID;
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
        matatu_id: Number(targetId),
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

export async function moveConductorMatatu(matatuId = DEFAULT_MATATU_ID) {
  const targetId = matatuId || DEFAULT_MATATU_ID;
  const response = await fetch(
    `${API_BASE_URL}/api/matatus/${targetId}/move`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error?.message || `Could not advance vehicle: ${response.status}`);
  }

  return data;
}

export async function resetConductorMatatu(matatuId = DEFAULT_MATATU_ID) {
  const targetId = matatuId || DEFAULT_MATATU_ID;
  const response = await fetch(
    `${API_BASE_URL}/api/matatus/${targetId}/reset`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    }
  );

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error?.message || `Could not reset vehicle: ${response.status}`);
  }

  return data;
}
