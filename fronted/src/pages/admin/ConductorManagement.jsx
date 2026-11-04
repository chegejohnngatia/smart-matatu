
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Users,
  Search,
  RefreshCw,
  AlertCircle,
  Bus,
  Pencil,
  Archive,
  RotateCcw,
  Trash2,
  X,
} from 'lucide-react'

import { useAuth } from '../../context/AuthContext'
import {
  getAdminConductors,
  getAvailableMatatus,
  updateConductor,
  archiveConductor,
  restoreConductor,
  deleteConductor,
} from '../../services/adminApi'

const statusStyles = {
  Active: 'bg-emerald-50 text-emerald-700',
  Archived: 'bg-amber-50 text-amber-700',
  Deleted: 'bg-rose-50 text-rose-700',
}

function formatDate(value) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleDateString()
}

const inputClass =
  'w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

export default function ConductorManagement() {
  const { csrfToken } = useAuth()

  const [conductors, setConductors] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [modal, setModal] = useState(null)
  const [modalError, setModalError] = useState('')
  const [modalLoading, setModalLoading] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState(null)

  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [passportPhoto, setPassportPhoto] = useState(null)

  const [availableMatatus, setAvailableMatatus] = useState([])
  const [selectedMatatuId, setSelectedMatatuId] = useState('')

  const loadConductors = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const records = await getAdminConductors()
      setConductors(records)
    } catch (err) {
      setError(err.message || 'Unable to load conductors.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConductors()
  }, [loadConductors])

  const filteredConductors = useMemo(() => {
    const term = search.trim().toLowerCase()

    return conductors.filter((conductor) => {
      const matchesStatus =
        statusFilter === 'All' || conductor.status === statusFilter

      const matchesSearch =
        !term ||
        [
          conductor.full_name,
          conductor.email,
          conductor.matatu?.registration_number,
          conductor.matatu?.route_name,
        ].some((value) => value?.toLowerCase().includes(term))

      return matchesStatus && matchesSearch
    })
  }, [conductors, search, statusFilter])

  const counts = useMemo(() => ({
    All: conductors.length,
    Active: conductors.filter((item) => item.status === 'Active').length,
    Archived: conductors.filter((item) => item.status === 'Archived').length,
    Deleted: conductors.filter((item) => item.status === 'Deleted').length,
  }), [conductors])

  function closeModal() {
    if (modalLoading) return

    setModal(null)
    setModalError('')
    setPassportPhoto(null)
    setSelectedMatatuId('')
  }

  function openEdit(conductor) {
    setEditName(conductor.full_name || '')
    setEditEmail(conductor.email || '')
    setPassportPhoto(null)
    setModalError('')
    setModal({ type: 'edit', conductor })
  }

  async function openRestore(conductor) {
    setModalError('')
    setAvailableMatatus([])
    setSelectedMatatuId('')
    setModal({ type: 'restore', conductor })
    setModalLoading(true)

    try {
      const records = await getAvailableMatatus()
      setAvailableMatatus(records)

      if (records.length === 0) {
        setModalError(
          'There are no registered matatus available for assignment.'
        )
      }
    } catch (err) {
      setModalError(err.message || 'Unable to load available matatus.')
    } finally {
      setModalLoading(false)
    }
  }

  async function handleArchive(conductor) {
    const confirmed = window.confirm(
      `Archive ${conductor.full_name}?\n\nThe conductor will become inactive, will not be able to log in, and their active matatu assignment will end.`
    )

    if (!confirmed) return

    setActionLoadingId(conductor.id)
    setError('')

    try {
      await archiveConductor(conductor.id, csrfToken)
      await loadConductors()
    } catch (err) {
      setError(err.message || 'Unable to archive conductor.')
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleDelete(conductor) {
    const confirmed = window.confirm(
      `Permanently delete ${conductor.full_name}?\n\nThis account must remain archived. Its login details will be anonymised, while historical records will be retained. This action cannot be undone.`
    )

    if (!confirmed) return

    setActionLoadingId(conductor.id)
    setError('')

    try {
      await deleteConductor(conductor.id, csrfToken)
      await loadConductors()
    } catch (err) {
      setError(err.message || 'Unable to delete conductor.')
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleEditSubmit(event) {
    event.preventDefault()
    setModalError('')

    const formData = new FormData()
    formData.append('full_name', editName.trim())
    formData.append('email', editEmail.trim())

    if (passportPhoto) {
      formData.append('passport_photo', passportPhoto)
    }

    setModalLoading(true)

    try {
      await updateConductor(
        modal.conductor.id,
        formData,
        csrfToken
      )

      setModal(null)
      setPassportPhoto(null)
      await loadConductors()
    } catch (err) {
      setModalError(err.message || 'Unable to update conductor.')
    } finally {
      setModalLoading(false)
    }
  }

  async function handleRestoreSubmit(event) {
    event.preventDefault()
    setModalError('')

    if (!selectedMatatuId) {
      setModalError('Please select a matatu.')
      return
    }

    setModalLoading(true)

    try {
      await restoreConductor(
        modal.conductor.id,
        selectedMatatuId,
        csrfToken
      )

      setModal(null)
      setSelectedMatatuId('')
      await loadConductors()
    } catch (err) {
      setModalError(err.message || 'Unable to restore conductor.')
    } finally {
      setModalLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
            Administration
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            Conductor Management
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            View and manage registered conductor accounts.
          </p>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'All conductors', value: counts.All },
          { label: 'Active', value: counts.Active },
          { label: 'Archived', value: counts.Archived },
          { label: 'Deleted', value: counts.Deleted },
        ].map((item) => (
          <article
            key={item.label}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-500">
              {item.label}
            </p>
            <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
              {loading ? '—' : item.value}
            </p>
          </article>
        ))}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="space-y-4 border-b border-slate-100 p-5 sm:p-6">
          <div>
            <h3 className="font-bold text-slate-900">
              Registered conductors
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Conductor accounts retrieved from the Smart Matatu backend.
            </p>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full lg:max-w-md">
              <Search
                size={18}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search name, email, matatu or route..."
                className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              {['All', 'Active', 'Archived', 'Deleted'].map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setStatusFilter(status)}
                  className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                    statusFilter === status
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {status} ({counts[status]})
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="m-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            <AlertCircle size={19} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Conductor operation failed</p>
              <p className="mt-1">{error}</p>
              <button
                type="button"
                onClick={loadConductors}
                className="mt-2 font-semibold underline"
              >
                Reload records
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <RefreshCw size={26} className="animate-spin text-blue-600" />
            <p className="mt-4 text-sm font-medium text-slate-600">
              Loading conductor records...
            </p>
          </div>
        ) : !error && filteredConductors.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-5 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
              <Users size={26} />
            </div>
            <h3 className="mt-4 font-bold text-slate-800">
              {conductors.length === 0
                ? 'No conductors registered'
                : 'No matching conductors'}
            </h3>
            <p className="mt-2 max-w-md text-sm text-slate-500">
              {conductors.length === 0
                ? 'Registered conductor accounts will appear here.'
                : 'Try changing your search or status filter.'}
            </p>
          </div>
        ) : !error ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-4 font-semibold">Conductor</th>
                  <th className="px-5 py-4 font-semibold">Assigned matatu</th>
                  <th className="px-5 py-4 font-semibold">Route</th>
                  <th className="px-5 py-4 font-semibold">Date registered</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredConductors.map((conductor) => {
                  const actionBusy = actionLoadingId === conductor.id

                  return (
                    <tr
                      key={conductor.id}
                      className="border-b border-slate-50 last:border-0 hover:bg-slate-50/70"
                    >
                      <td className="px-5 py-4">
                        <p className="font-semibold text-slate-800">
                          {conductor.full_name}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {conductor.email}
                        </p>
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {conductor.matatu ? (
                          <span className="inline-flex items-center gap-2">
                            <Bus size={16} className="text-slate-400" />
                            {conductor.matatu.registration_number}
                          </span>
                        ) : (
                          'Not assigned'
                        )}
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {conductor.matatu?.route_name || '—'}
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {formatDate(conductor.created_at)}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                            statusStyles[conductor.status] ||
                            'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {conductor.status}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex flex-wrap items-center gap-2">
                          {conductor.status === 'Active' && (
                            <>
                              <button
                                type="button"
                                onClick={() => openEdit(conductor)}
                                disabled={actionBusy}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                              >
                                <Pencil size={14} />
                                Edit
                              </button>

                              <button
                                type="button"
                                onClick={() => handleArchive(conductor)}
                                disabled={actionBusy}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100 disabled:opacity-50"
                              >
                                <Archive size={14} />
                                {actionBusy ? 'Working...' : 'Archive'}
                              </button>
                            </>
                          )}

                          {conductor.status === 'Archived' && (
                            <>
                              <button
                                type="button"
                                onClick={() => openRestore(conductor)}
                                disabled={actionBusy}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                              >
                                <RotateCcw size={14} />
                                Restore
                              </button>

                              <button
                                type="button"
                                onClick={() => handleDelete(conductor)}
                                disabled={actionBusy}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                              >
                                <Trash2 size={14} />
                                {actionBusy ? 'Working...' : 'Delete'}
                              </button>
                            </>
                          )}

                          {conductor.status === 'Deleted' && (
                            <span className="text-xs text-slate-400">
                              No actions available
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        {!loading && !error && filteredConductors.length > 0 && (
          <div className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
            Showing {filteredConductors.length} of {conductors.length} conductors
          </div>
        )}
      </section>

      {modal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/50 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeModal()
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="conductor-modal-title"
            className="my-auto w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3
                  id="conductor-modal-title"
                  className="text-lg font-bold text-slate-900"
                >
                  {modal.type === 'edit'
                    ? 'Edit conductor'
                    : 'Restore conductor'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {modal.conductor.full_name}
                </p>
              </div>

              <button
                type="button"
                onClick={closeModal}
                disabled={modalLoading}
                aria-label="Close dialog"
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
              >
                <X size={19} />
              </button>
            </div>

            {modalError && (
              <div
                role="alert"
                className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
              >
                {modalError}
              </div>
            )}

            {modal.type === 'edit' ? (
              <form onSubmit={handleEditSubmit} className="mt-5 space-y-4">
                <div>
                  <label
                    htmlFor="edit-conductor-name"
                    className="mb-1.5 block text-sm font-medium text-slate-700"
                  >
                    Full name
                  </label>
                  <input
                    id="edit-conductor-name"
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                    minLength={3}
                    maxLength={100}
                    required
                    className={inputClass}
                  />
                </div>

                <div>
                  <label
                    htmlFor="edit-conductor-email"
                    className="mb-1.5 block text-sm font-medium text-slate-700"
                  >
                    Email address
                  </label>
                  <input
                    id="edit-conductor-email"
                    type="email"
                    value={editEmail}
                    onChange={(event) => setEditEmail(event.target.value)}
                    required
                    className={inputClass}
                  />
                </div>

                <div>
                  <label
                    htmlFor="edit-conductor-photo"
                    className="mb-1.5 block text-sm font-medium text-slate-700"
                  >
                    Replace passport photograph (optional)
                  </label>
                  <input
                    id="edit-conductor-photo"
                    type="file"
                    accept="image/jpeg,image/png"
                    onChange={(event) =>
                      setPassportPhoto(event.target.files?.[0] || null)
                    }
                    className="w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-slate-700 hover:file:bg-slate-200"
                  />
                  <p className="mt-1 text-xs text-slate-400">
                    Leave empty to keep the existing photograph.
                  </p>
                </div>

                <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
                  <button
                    type="button"
                    onClick={closeModal}
                    disabled={modalLoading}
                    className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={modalLoading}
                    className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {modalLoading ? 'Saving...' : 'Save changes'}
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleRestoreSubmit} className="mt-5 space-y-4">
                <div>
                  <label
                    htmlFor="restore-matatu"
                    className="mb-1.5 block text-sm font-medium text-slate-700"
                  >
                    Assign matatu
                  </label>

                  <select
                    id="restore-matatu"
                    value={selectedMatatuId}
                    onChange={(event) =>
                      setSelectedMatatuId(event.target.value)
                    }
                    disabled={modalLoading || availableMatatus.length === 0}
                    required
                    className={inputClass}
                  >
                    <option value="">
                      {modalLoading
                        ? 'Loading available matatus...'
                        : availableMatatus.length === 0
                          ? 'No available matatus'
                          : 'Select a matatu'}
                    </option>

                    {availableMatatus.map((matatu) => (
                      <option key={matatu.id} value={matatu.id}>
                        {matatu.registration_number} — {matatu.route_name}
                      </option>
                    ))}
                  </select>
                </div>

                <p className="text-xs text-slate-500">
                  Restoring reactivates this conductor and creates a new
                  matatu assignment.
                </p>

                <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
                  <button
                    type="button"
                    onClick={closeModal}
                    disabled={modalLoading}
                    className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={
                      modalLoading ||
                      availableMatatus.length === 0 ||
                      !selectedMatatuId
                    }
                    className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {modalLoading ? 'Restoring...' : 'Restore conductor'}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
