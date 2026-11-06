
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(url, options = {}) {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    credentials: 'include',
    ...options,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const error = new Error(
      data.message || data.error || `Request failed: ${response.status}`
    )
    error.status = response.status
    error.data = data
    throw error
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

// JSON headers for protected API mutations.
function csrfJsonHeaders(csrfToken) {
  return {
    ...csrfHeaders(csrfToken),
    'Content-Type': 'application/json',
  }
}

// Retrieve all administrative routes.
export async function getAdminRoutes() {
  const data = await request('/api/admin/routes')
  return data.routes || []
}

// Create a route.
export async function createAdminRoute(routeData, csrfToken) {
  return request('/api/admin/routes', {
    method: 'POST',
    headers: csrfJsonHeaders(csrfToken),
    body: JSON.stringify(routeData),
  })
}

// Update route details.
export async function updateAdminRoute(routeId, routeData, csrfToken) {
  return request(`/api/admin/routes/${routeId}`, {
    method: 'PUT',
    headers: csrfJsonHeaders(csrfToken),
    body: JSON.stringify(routeData),
  })
}

// Activate an inactive route.
export async function activateAdminRoute(routeId, csrfToken) {
  return request(`/api/admin/routes/${routeId}/activate`, {
    method: 'POST',
    headers: csrfHeaders(csrfToken),
  })
}

// Deactivate an active route.
export async function deactivateAdminRoute(routeId, csrfToken) {
  return request(`/api/admin/routes/${routeId}/deactivate`, {
    method: 'POST',
    headers: csrfHeaders(csrfToken),
  })
}

// Permanently delete a route.
// Error responses retain their status and dependency details.
export async function deleteAdminRoute(routeId, csrfToken) {
  return request(`/api/admin/routes/${routeId}`, {
    method: 'DELETE',
    headers: csrfHeaders(csrfToken),
  })
}

// Retrieve active and archived stages belonging to a route.
export async function getAdminRouteStages(routeId) {
  const data = await request(`/api/admin/routes/${routeId}/stages`)
  return {
    route: data.route,
    stages: data.stages || [],
  }
}

// Create a stage at the specified position.
export async function createAdminStage(routeId, stageData, csrfToken) {
  return request(`/api/admin/routes/${routeId}/stages`, {
    method: 'POST',
    headers: csrfJsonHeaders(csrfToken),
    body: JSON.stringify(stageData),
  })
}

// Update stage name and coordinates without changing its route or position.
export async function updateAdminStage(stageId, stageData, csrfToken) {
  return request(`/api/admin/stages/${stageId}`, {
    method: 'PUT',
    headers: csrfJsonHeaders(csrfToken),
    body: JSON.stringify(stageData),
  })
}

// Archive an active stage.
export async function archiveAdminStage(stageId, csrfToken) {
  return request(`/api/admin/stages/${stageId}/archive`, {
    method: 'POST',
    headers: csrfHeaders(csrfToken),
  })
}

// Restore an archived stage at an administrator-selected position.
export async function restoreAdminStage(stageId, position, csrfToken) {
  return request(`/api/admin/stages/${stageId}/restore`, {
    method: 'POST',
    headers: csrfJsonHeaders(csrfToken),
    body: JSON.stringify({
      position: Number(position),
    }),
  })
}

// Permanently delete an archived stage after explicit confirmation.
export async function deleteAdminStage(stageId, csrfToken) {
  return request(`/api/admin/stages/${stageId}`, {
    method: 'DELETE',
    headers: csrfJsonHeaders(csrfToken),
    body: JSON.stringify({
      confirm: true,
    }),
  })
}

// Reorder every active stage in a route.
export async function reorderAdminStages(routeId, stageIds, csrfToken) {
  return request(`/api/admin/routes/${routeId}/stages/reorder`, {
    method: 'PUT',
    headers: csrfJsonHeaders(csrfToken),
    body: JSON.stringify({
      stage_ids: stageIds,
    }),
  })
}
