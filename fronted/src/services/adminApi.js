
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    credentials: 'include',
    ...options,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(
      data.message || data.error || `Request failed: ${response.status}`
    )
  }

  return data
}

function csrfHeaders(csrfToken) {
  if (!csrfToken) {
    throw new Error('Your session has expired. Please log in again.')
  }

  return {
    'X-CSRF-Token': csrfToken,
  }
}

// Retrieve all conductor accounts.
export async function getAdminConductors() {
  const data = await request('/api/admin/conductors')
  return data.conductors || []
}

// Retrieve matatus available for conductor assignment.
export async function getAvailableMatatus() {
  const data = await request('/api/admin/matatus/available')
  return data.matatus || []
}

// Update conductor details and optionally replace passport photograph.
export async function updateConductor(conductorId, formData, csrfToken) {
  return request(`/api/admin/conductors/${conductorId}`, {
    method: 'PUT',
    headers: csrfHeaders(csrfToken),
    body: formData,
  })
}

// Archive an active conductor.
export async function archiveConductor(conductorId, csrfToken) {
  return request(`/api/admin/conductors/${conductorId}/archive`, {
    method: 'POST',
    headers: csrfHeaders(csrfToken),
  })
}

// Restore an archived conductor and assign an available matatu.
export async function restoreConductor(conductorId, matatuId, csrfToken) {
  return request(`/api/admin/conductors/${conductorId}/restore`, {
    method: 'POST',
    headers: {
      ...csrfHeaders(csrfToken),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      matatu_id: Number(matatuId),
    }),
  })
}

// Permanently delete an already archived conductor.
export async function deleteConductor(conductorId, csrfToken) {
  return request(`/api/admin/conductors/${conductorId}`, {
    method: 'DELETE',
    headers: csrfHeaders(csrfToken),
  })
}
