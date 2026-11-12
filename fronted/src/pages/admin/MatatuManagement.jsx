import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bus,
  Plus,
  RefreshCw,
  AlertCircle,
  Pencil,
  Archive,
  RotateCcw,
  Trash2,
  X,
  MapPin,
} from 'lucide-react'

import { useAuth } from '../../context/AuthContext'
import {
  getAdminMatatus,
  getAdminRoutes,
  createAdminMatatu,
  updateAdminMatatu,
  archiveAdminMatatu,
  restoreAdminMatatu,
  deleteAdminMatatu,
} from '../../services/adminApi'

const inputClass =
  'w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

export default function MatatuManagement() {
  const { csrfToken } = useAuth()

  const [matatus, setMatatus] = useState([])
  const [routes, setRoutes] = useState([])
  const [loading, setLoading] = useState(true)
  const [pageError, setPageError] = useState('')
  const [modal, setModal] = useState(false)
  const [editingMatatu, setEditingMatatu] = useState(null)
  const [registrationNumber, setRegistrationNumber] = useState('')
  const [routeId, setRouteId] = useState('')
  const [modalError, setModalError] = useState('')
  const [saving, setSaving] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState(null)

  const activeRoutes = useMemo(
    () => routes.filter((route) => route.is_active),
    [routes]
  )

  const activeCount = matatus.filter(
    (matatu) => !matatu.is_archived
  ).length

  const archivedCount = matatus.filter(
    (matatu) => Boolean(matatu.is_archived)
  ).length

  const loadData = useCallback(async () => {
    setLoading(true)
    setPageError('')

    try {
      const [matatuData, routeData] = await Promise.all([
        getAdminMatatus(),
        getAdminRoutes(),
      ])

      setMatatus(matatuData)
      setRoutes(routeData)
    } catch (error) {
      setPageError(error.message || 'Unable to load matatus.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  function openCreateModal() {
    setEditingMatatu(null)
    setRegistrationNumber('')
    setRouteId('')
    setModalError('')
    setModal(true)
  }

  function openEditModal(matatu) {
    setEditingMatatu(matatu)
    setRegistrationNumber(matatu.registration_number || '')
    setRouteId(String(matatu.route_id || ''))
    setModalError('')
    setModal(true)
  }

  function closeModal() {
    if (saving) return
    setModal(false)
    setEditingMatatu(null)
    setModalError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setModalError('')

    const normalizedRegistration = registrationNumber.trim().toUpperCase()
    const selectedRouteId = Number(routeId)

    if (!normalizedRegistration) {
      setModalError('Enter the matatu registration number.')
      return
    }

    if (!Number.isInteger(selectedRouteId) || selectedRouteId <= 0) {
      setModalError('Select a valid route.')
      return
    }

    setSaving(true)

    try {
      const payload = {
        registration_number: normalizedRegistration,
        route_id: selectedRouteId,
      }

      if (editingMatatu) {
        await updateAdminMatatu(editingMatatu.id, payload, csrfToken)
      } else {
        await createAdminMatatu(payload, csrfToken)
      }

      setModal(false)
      setEditingMatatu(null)
      await loadData()
    } catch (error) {
      setModalError(error.message || 'Unable to save the matatu.')
    } finally {
      setSaving(false)
    }
  }

  async function handleArchive(matatu) {
    const confirmed = window.confirm(
      `Archive ${matatu.registration_number}?\n\n` +
      'Any active conductor assignments for this matatu will be ended. ' +
      'You can restore the matatu later, but conductors will not be automatically reassigned.'
    )

    if (!confirmed) return

    setActionLoadingId(matatu.id)
    setPageError('')

    try {
      await archiveAdminMatatu(matatu.id, csrfToken)
      await loadData()
    } catch (error) {
      setPageError(error.message || 'Unable to archive the matatu.')
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleRestore(matatu) {
    const confirmed = window.confirm(
      `Restore ${matatu.registration_number}?\n\n` +
      'The matatu will become active again. Previous conductor assignments will not be recreated automatically.'
    )

    if (!confirmed) return

    setActionLoadingId(matatu.id)
    setPageError('')

    try {
      await restoreAdminMatatu(matatu.id, csrfToken)
      await loadData()
    } catch (error) {
      setPageError(error.message || 'Unable to restore the matatu.')
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleDelete(matatu) {
    const confirmed = window.confirm(
      `PERMANENTLY DELETE ${matatu.registration_number}?\n\n` +
      'This action cannot be undone. Related operational records will be deleted. ' +
      'Anonymized audit history, registration history and the permanent registration reservation will be retained.\n\n' +
      'Continue only if you are certain.'
    )

    if (!confirmed) return

    setActionLoadingId(matatu.id)
    setPageError('')

    try {
      await deleteAdminMatatu(matatu.id, csrfToken)
      await loadData()
    } catch (error) {
      setPageError(error.message || 'Unable to permanently delete the matatu.')
    } finally {
      setActionLoadingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Matatu Management
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Register matatus, assign routes and manage their operational status.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>

          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            <Plus size={17} />
            Register Matatu
          </button>
        </div>
      </div>

      {pageError && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <span>{pageError}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Total Matatus</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{matatus.length}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Active Matatus</p>
          <p className="mt-2 text-3xl font-bold text-emerald-600">{activeCount}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Archived Matatus</p>
          <p className="mt-2 text-3xl font-bold text-amber-600">{archivedCount}</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold text-slate-900">Registered Vehicles</h2>
          <p className="mt-1 text-sm text-slate-500">
            Active and archived matatus registered in the system.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 px-5 py-14 text-sm text-slate-500">
            <RefreshCw size={17} className="animate-spin" />
            Loading matatus...
          </div>
        ) : matatus.length === 0 ? (
          <div className="px-5 py-14 text-center">
            <Bus size={34} className="mx-auto text-slate-300" />
            <p className="mt-3 font-medium text-slate-700">No matatus registered</p>
            <p className="mt-1 text-sm text-slate-500">
              Register a matatu to get started.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Matatu</th>
                  <th className="px-5 py-3 font-semibold">Assigned Route</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  <th className="px-5 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {matatus.map((matatu) => {
                  const archived = Boolean(matatu.is_archived)
                  const busy = actionLoadingId === matatu.id

                  return (
                    <tr key={matatu.id} className="hover:bg-slate-50/70">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="rounded-xl bg-blue-50 p-2 text-blue-600">
                            <Bus size={19} />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900">
                              {matatu.registration_number}
                            </p>
                            <p className="text-xs text-slate-500">
                              Vehicle ID: {matatu.id}
                            </p>
                          </div>
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2 text-slate-700">
                          <MapPin size={15} className="text-slate-400" />
                          {matatu.route_name || 'No route assigned'}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        {archived ? (
                          <span className="inline-flex rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                            Archived
                          </span>
                        ) : (
                          <span className="inline-flex rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                            Active
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex items-center justify-end gap-2">
                          {!archived && (
                            <>
                              <button
                                type="button"
                                onClick={() => openEditModal(matatu)}
                                title="Edit matatu"
                                className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-100"
                              >
                                <Pencil size={16} />
                              </button>

                              <button
                                type="button"
                                onClick={() => handleArchive(matatu)}
                                disabled={busy}
                                title="Archive matatu"
                                className="rounded-lg border border-amber-200 p-2 text-amber-700 hover:bg-amber-50 disabled:opacity-50"
                              >
                                <Archive size={16} />
                              </button>
                            </>
                          )}

                          {archived && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleRestore(matatu)}
                                disabled={busy}
                                title="Restore matatu"
                                className="rounded-lg border border-emerald-200 p-2 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                              >
                                <RotateCcw size={16} />
                              </button>

                              <button
                                type="button"
                                onClick={() => handleDelete(matatu)}
                                disabled={busy}
                                title="Permanently delete matatu"
                                className="rounded-lg border border-rose-200 p-2 text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                              >
                                <Trash2 size={16} />
                              </button>
                            </>
                          )}

                          {busy && (
                            <RefreshCw size={15} className="animate-spin text-slate-400" />
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  {editingMatatu ? 'Edit Matatu' : 'Register Matatu'}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Enter the vehicle details below.
                </p>
              </div>

              <button
                type="button"
                onClick={closeModal}
                disabled={saving}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={19} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5 p-6">
              {modalError && (
                <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                  <AlertCircle size={17} className="mt-0.5 shrink-0" />
                  <span>{modalError}</span>
                </div>
              )}

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Registration Number
                </label>
                <input
                  type="text"
                  value={registrationNumber}
                  onChange={(event) => setRegistrationNumber(event.target.value)}
                  placeholder="e.g. KDA 123A"
                  className={inputClass}
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Assigned Route
                </label>
                <select
                  value={routeId}
                  onChange={(event) => setRouteId(event.target.value)}
                  className={inputClass}
                  required
                >
                  <option value="">Select an active route</option>
                  {activeRoutes.map((route) => (
                    <option key={route.id} value={route.id}>
                      {route.name}
                    </option>
                  ))}
                </select>

                {activeRoutes.length === 0 && (
                  <p className="mt-2 text-xs text-amber-700">
                    No active routes are available. Create or activate a route first.
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={closeModal}
                  disabled={saving}
                  className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={saving || activeRoutes.length === 0}
                  className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {saving
                    ? 'Saving...'
                    : editingMatatu
                      ? 'Save Changes'
                      : 'Register Matatu'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}