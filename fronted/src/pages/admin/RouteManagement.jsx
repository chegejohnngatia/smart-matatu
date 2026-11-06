import { Fragment, useCallback, useEffect, useState } from 'react'
import {
  Route,
  Plus,
  RefreshCw,
  AlertCircle,
  Pencil,
  Power,
  Trash2,
  X,
  MapPin,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

import { useAuth } from '../../context/AuthContext'
import {
  getAdminRoutes,
  createAdminRoute,
  updateAdminRoute,
  activateAdminRoute,
  deactivateAdminRoute,
  deleteAdminRoute,
  getAdminRouteStages,
  createAdminStage,
  updateAdminStage,
  archiveAdminStage,
  restoreAdminStage,
  deleteAdminStage,
  reorderAdminStages,
} from '../../services/adminApi'

const inputClass =
  'w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100'

export default function RouteManagement() {
  const { csrfToken } = useAuth()

  const [routes, setRoutes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const [modalError, setModalError] = useState('')
  const [modalLoading, setModalLoading] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState(null)
  const [expandedRouteId, setExpandedRouteId] = useState(null)
  const [routeStages, setRouteStages] = useState({})
  const [stageLoadingId, setStageLoadingId] = useState(null)
  const [stageErrors, setStageErrors] = useState({})
  const [stageFormRouteId, setStageFormRouteId] = useState(null)
  const [newStageName, setNewStageName] = useState('')
  const [newStageLatitude, setNewStageLatitude] = useState('')
  const [newStageLongitude, setNewStageLongitude] = useState('')
  const [newStagePosition, setNewStagePosition] = useState('')
  const [stageFormError, setStageFormError] = useState('')
  const [stageFormLoading, setStageFormLoading] = useState(false)

  const [editingStageId, setEditingStageId] = useState(null)
  const [editStageName, setEditStageName] = useState('')
  const [editStageLatitude, setEditStageLatitude] = useState('')
  const [editStageLongitude, setEditStageLongitude] = useState('')
  const [editStageError, setEditStageError] = useState('')
  const [editStageLoading, setEditStageLoading] = useState(false)
  const [archivingStageId, setArchivingStageId] = useState(null)
  const [restoringStageId, setRestoringStageId] = useState(null)
  const [restoreStagePosition, setRestoreStagePosition] = useState('1')
  const [restoreStageError, setRestoreStageError] = useState('')
  const [deletingStageId, setDeletingStageId] = useState(null)
  const [deleteStageErrors, setDeleteStageErrors] = useState({})
  const [reorderingRouteId, setReorderingRouteId] = useState(null)
  const [reorderErrors, setReorderErrors] = useState({})

  const [routeName, setRouteName] = useState('')
  const [routeDescription, setRouteDescription] = useState('')

  const loadRoutes = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const records = await getAdminRoutes()
      setRoutes(records)
    } catch (err) {
      setError(err.message || 'Unable to load routes.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRoutes()
  }, [loadRoutes])

  async function loadRouteStages(routeId) {
    setStageLoadingId(routeId)
    setStageErrors((previous) => ({ ...previous, [routeId]: '' }))

    try {
      const result = await getAdminRouteStages(routeId)
      setRouteStages((previous) => ({
        ...previous,
        [routeId]: result.stages || [],
      }))
    } catch (err) {
      setStageErrors((previous) => ({
        ...previous,
        [routeId]: err.message || 'Unable to load route stages.',
      }))
    } finally {
      setStageLoadingId(null)
    }
  }

  async function handleReorderStage(stageId, routeId, direction) {
    const activeStages = (routeStages[routeId] || [])
      .filter((stage) => !stage.is_archived)
      .sort((a, b) => a.sequence_number - b.sequence_number)

    const currentIndex = activeStages.findIndex(
      (stage) => stage.id === stageId
    )
    const targetIndex = currentIndex + direction

    if (
      currentIndex === -1 ||
      targetIndex < 0 ||
      targetIndex >= activeStages.length
    ) {
      return
    }

    const orderedIds = activeStages.map((stage) => stage.id)
    ;[orderedIds[currentIndex], orderedIds[targetIndex]] = [
      orderedIds[targetIndex],
      orderedIds[currentIndex],
    ]

    setReorderingRouteId(routeId)
    setReorderErrors((previous) => ({
      ...previous,
      [routeId]: '',
    }))

    try {
      await reorderAdminStages(routeId, orderedIds, csrfToken)
      await loadRouteStages(routeId)
    } catch (err) {
      setReorderErrors((previous) => ({
        ...previous,
        [routeId]: err.message || 'Unable to reorder stages.',
      }))
    } finally {
      setReorderingRouteId(null)
    }
  }

  async function toggleRouteStages(routeId) {
    if (expandedRouteId === routeId) {
      setExpandedRouteId(null)
      return
    }

    setExpandedRouteId(routeId)
    await loadRouteStages(routeId)
  }

  function resetStageForm() {
    setNewStageName('')
    setNewStageLatitude('')
    setNewStageLongitude('')
    setNewStagePosition('')
    setStageFormError('')
  }

  async function handleDeleteStage(stageId, routeId, stageName) {
    const confirmed = window.confirm(
      `Permanently delete "${stageName}"? This cannot be undone. Historical records, if any, will prevent deletion.`
    )

    if (!confirmed) return

    setDeletingStageId(stageId)
    setDeleteStageErrors((previous) => ({
      ...previous,
      [stageId]: '',
    }))

    try {
      await deleteAdminStage(stageId, csrfToken)
      await loadRouteStages(routeId)
    } catch (err) {
      setDeleteStageErrors((previous) => ({
        ...previous,
        [stageId]: err.message || 'Unable to permanently delete stage.',
      }))
    } finally {
      setDeletingStageId(null)
    }
  }
  async function handleRestoreStage(stageId, routeId) {
    const position = Number(restoreStagePosition)
    const activeCount = (routeStages[routeId] || []).filter(
      (stage) => !stage.is_archived
    ).length

    if (
      !Number.isInteger(position) ||
      position < 1 ||
      position > activeCount + 1
    ) {
      setRestoreStageError(
        `Choose a position between 1 and ${activeCount + 1}.`
      )
      return
    }

    setRestoringStageId(stageId)
    setRestoreStageError('')

    try {
      await restoreAdminStage(stageId, position, csrfToken)
      setRestoringStageId(null)
      await loadRouteStages(routeId)
    } catch (err) {
      setRestoreStageError(err.message || 'Unable to restore stage.')
    } finally {
      setRestoringStageId(null)
    }
  }
  async function handleArchiveStage(stageId, routeId, stageName) {
    const confirmed = window.confirm(
      `Archive "${stageName}"? It will no longer be available for new passenger destinations. Historical records will be preserved.`
    )

    if (!confirmed) return

    setArchivingStageId(stageId)
    setStageErrors((previous) => ({ ...previous, [routeId]: '' }))

    try {
      await archiveAdminStage(stageId, csrfToken)

      if (editingStageId === stageId) {
        setEditingStageId(null)
        setEditStageError('')
      }

      await loadRouteStages(routeId)
    } catch (err) {
      setStageErrors((previous) => ({
        ...previous,
        [routeId]: err.message || 'Unable to archive stage.',
      }))
    } finally {
      setArchivingStageId(null)
    }
  }
  async function handleUpdateStage(event, stageId, routeId) {
    event.preventDefault()

    const latitude = Number(editStageLatitude)
    const longitude = Number(editStageLongitude)

    if (!editStageName.trim()) {
      setEditStageError('Stage name is required.')
      return
    }

    if (
      editStageLatitude.trim() === '' ||
      !Number.isFinite(latitude) ||
      latitude < -90 ||
      latitude > 90
    ) {
      setEditStageError('Enter a valid latitude between -90 and 90.')
      return
    }

    if (
      editStageLongitude.trim() === '' ||
      !Number.isFinite(longitude) ||
      longitude < -180 ||
      longitude > 180
    ) {
      setEditStageError('Enter a valid longitude between -180 and 180.')
      return
    }

    setEditStageLoading(true)
    setEditStageError('')

    try {
      await updateAdminStage(
        stageId,
        {
          name: editStageName.trim(),
          latitude,
          longitude,
        },
        csrfToken
      )

      setEditingStageId(null)
      await loadRouteStages(routeId)
    } catch (err) {
      setEditStageError(err.message || 'Unable to update stage.')
    } finally {
      setEditStageLoading(false)
    }
  }
  async function handleCreateStage(event) {
    event.preventDefault()

    if (stageFormRouteId == null) return

    const routeId = stageFormRouteId
    const activeStages = (routeStages[routeId] || []).filter(
      (stage) => !stage.is_archived
    )

    const latitude = Number(newStageLatitude)
    const longitude = Number(newStageLongitude)
    const position = Number(
      newStagePosition || activeStages.length + 1
    )

    if (!newStageName.trim()) {
      setStageFormError('Stage name is required.')
      return
    }

    if (
      newStageLatitude.trim() === '' ||
      !Number.isFinite(latitude) ||
      latitude < -90 ||
      latitude > 90
    ) {
      setStageFormError('Enter a valid latitude between -90 and 90.')
      return
    }

    if (
      newStageLongitude.trim() === '' ||
      !Number.isFinite(longitude) ||
      longitude < -180 ||
      longitude > 180
    ) {
      setStageFormError('Enter a valid longitude between -180 and 180.')
      return
    }

    if (
      !Number.isInteger(position) ||
      position < 1 ||
      position > activeStages.length + 1
    ) {
      setStageFormError(
        `Position must be between 1 and ${activeStages.length + 1}.`
      )
      return
    }

    setStageFormLoading(true)
    setStageFormError('')

    try {
      await createAdminStage(
        routeId,
        {
          name: newStageName.trim(),
          latitude,
          longitude,
          position,
        },
        csrfToken
      )

      resetStageForm()
      setStageFormRouteId(null)

      await loadRouteStages(routeId)

      try {
        const refreshedRoutes = await getAdminRoutes()
        setRoutes(refreshedRoutes)
      } catch {
        // Stage creation succeeded; route-list refresh can be retried separately.
      }
    } catch (err) {
      setStageFormError(err.message || 'Unable to create stage.')
    } finally {
      setStageFormLoading(false)
    }
  }

  function openCreate() {
    setRouteName('')
    setRouteDescription('')
    setModalError('')
    setModal({ type: 'create' })
  }

  function openEdit(route) {
    setRouteName(route.name || '')
    setRouteDescription(route.description || '')
    setModalError('')
    setModal({ type: 'edit', route })
  }

  function closeModal() {
    if (modalLoading) return

    setModal(null)
    setModalError('')
  }

  async function handleRouteSubmit(event) {
    event.preventDefault()
    setModalError('')

    const name = routeName.trim()
    const description = routeDescription.trim()

    if (!name) {
      setModalError('Please enter a route name.')
      return
    }

    setModalLoading(true)

    try {
      if (modal.type === 'create') {
        await createAdminRoute({ name, description }, csrfToken)
      } else {
        await updateAdminRoute(
          modal.route.id,
          { name, description },
          csrfToken
        )
      }

      setModal(null)
      await loadRoutes()
    } catch (err) {
      setModalError(err.message || 'Unable to save route.')
    } finally {
      setModalLoading(false)
    }
  }

  async function handleStatusChange(route) {
    const activating = !route.is_active
    const action = activating ? 'activate' : 'deactivate'

    const confirmed = window.confirm(
      `${activating ? 'Activate' : 'Deactivate'} route "${route.name}"?`
    )

    if (!confirmed) return

    setActionLoadingId(route.id)
    setError('')

    try {
      if (activating) {
        await activateAdminRoute(route.id, csrfToken)
      } else {
        await deactivateAdminRoute(route.id, csrfToken)
      }

      await loadRoutes()
    } catch (err) {
      setError(err.message || `Unable to ${action} route.`)
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleDelete(route) {
    const confirmed = window.confirm(
      `Permanently delete route "${route.name}"?\n\nThis action cannot be undone. Routes with stages or matatu dependencies cannot be deleted.`
    )

    if (!confirmed) return

    setActionLoadingId(route.id)
    setError('')

    try {
      await deleteAdminRoute(route.id, csrfToken)
      await loadRoutes()
    } catch (err) {
      const dependencies = err.data?.dependencies

      if (err.status === 409 && dependencies) {
        setError(
          `Cannot delete "${route.name}". It has ${dependencies.stages || 0} stage(s) and ${dependencies.matatus || 0} matatu(s) depending on it.`
        )
      } else {
        setError(err.message || 'Unable to delete route.')
      }
    } finally {
      setActionLoadingId(null)
    }
  }

  const activeCount = routes.filter((item) => item.is_active).length
  const inactiveCount = routes.length - activeCount

  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
            Administration
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            Route Management
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Create and manage transport routes and their operational status.
          </p>
        </div>

        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
        >
          <Plus size={18} />
          Create route
        </button>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Total routes', value: routes.length },
          { label: 'Active routes', value: activeCount },
          { label: 'Inactive routes', value: inactiveCount },
        ].map((item) => (
          <article
            key={item.label}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-500">
              {item.label}
            </p>
            <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
              {loading ? '-' : item.value}
            </p>
          </article>
        ))}
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div>
            <h3 className="font-bold text-slate-900">Registered routes</h3>

          </div>

          <button
            type="button"
            onClick={loadRoutes}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="m-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
          >
            <AlertCircle size={19} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Route operation failed</p>
              <p className="mt-1">{error}</p>
              <button
                type="button"
                onClick={loadRoutes}
                className="mt-2 font-semibold underline"
              >
                Reload routes
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <RefreshCw size={26} className="animate-spin text-blue-600" />
            <p className="mt-4 text-sm font-medium text-slate-600">
              Loading route records...
            </p>
          </div>
        ) : !error && routes.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-5 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
              <Route size={26} />
            </div>
            <h3 className="mt-4 font-bold text-slate-800">
              No routes registered
            </h3>
            <p className="mt-2 max-w-md text-sm text-slate-500">
              Create a route to begin organising its physical stages.
            </p>
            <button
              type="button"
              onClick={openCreate}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <Plus size={17} />
              Create first route
            </button>
          </div>
        ) : !error ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-5 py-4 font-semibold">Route</th>
                  <th className="px-5 py-4 font-semibold">Stages</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                  <th className="px-5 py-4 font-semibold">Last updated</th>
                  <th className="px-5 py-4 font-semibold">Actions</th>
                </tr>
              </thead>

              <tbody>
                {routes.map((route) => {
                  const actionBusy = actionLoadingId === route.id
                  const stages = routeStages[route.id] || []
        const activeStages = stages
          .filter((stage) => !stage.is_archived)
          .sort((a, b) => a.sequence_number - b.sequence_number)

                  return (
                    <Fragment key={route.id}>
<tr
                      key={route.id}
                      className="border-b border-slate-50 last:border-0 hover:bg-slate-50/70"
                    >
                      <td className="px-5 py-4">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                            <MapPin size={17} />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-800">
                              {route.name}
                            </p>
                            <p className="mt-1 max-w-sm text-xs text-slate-500">
                              {route.description || 'No description provided'}
                            </p>
                          </div>
                        </div>
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {route.stage_count ?? 0}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                            route.is_active
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-amber-50 text-amber-700'
                          }`}
                        >
                          {route.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {route.updated_at
                          ? new Date(route.updated_at).toLocaleDateString()
                          : '-'}
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => toggleRouteStages(route.id)}
                            disabled={stageLoadingId === route.id}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                          >
                            {expandedRouteId === route.id ? (
                              <>
                                <ChevronUp size={14} />
                                Hide stages
                              </>
                            ) : (
                              <>
                                <ChevronDown size={14} />
                                Manage stages
                              </>
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => openEdit(route)}
                            disabled={actionBusy}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                          >
                            <Pencil size={14} />
                            Edit
                          </button>

                          <button
                            type="button"
                            onClick={() => handleStatusChange(route)}
                            disabled={actionBusy}
                            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold disabled:opacity-50 ${
                              route.is_active
                                ? 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100'
                                : 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                            }`}
                          >
                            <Power size={14} />
                            {actionBusy
                              ? 'Working...'
                              : route.is_active
                                ? 'Deactivate'
                                : 'Activate'}
                          </button>

                          <button
                            type="button"
                            onClick={() => handleDelete(route)}
                            disabled={actionBusy}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                          >
                            <Trash2 size={14} />
                            {actionBusy ? 'Working...' : 'Delete'}
                          </button>
                        </div>
                      </td>
</tr>
                    {expandedRouteId === route.id && (
                      <tr className="border-b border-slate-100 bg-slate-50/70">
                        <td colSpan={5} className="px-5 py-5">
                          {stageLoadingId === route.id ? (
                            <div className="py-4 text-sm text-slate-500">
                              Loading stages...
                            </div>
                          ) : stageErrors[route.id] ? (
                            <div className="flex flex-wrap items-center gap-3 py-3">
                              <p className="text-sm text-rose-600">
                                {stageErrors[route.id]}
                              </p>
                              <button
                                type="button"
                                onClick={() => loadRouteStages(route.id)}
                                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                              >
                                Retry
                              </button>
                            </div>
                          ) : (
                            <div>
                              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                                <h3 className="font-semibold text-slate-800">
                                  Stages for {route.name}
                                </h3>
                                <p className="text-xs text-slate-500">
                                  {stages.filter((stage) => !stage.is_archived).length} active
                                  {' · '}
                                  {stages.filter((stage) => stage.is_archived).length} archived
                                </p>

                                <button
                                  type="button"
                                  onClick={() => {
                                    const activeCount = stages.filter(
                                      (stage) => !stage.is_archived
                                    ).length

                                    if (stageFormRouteId === route.id) {
                                      setStageFormRouteId(null)
                                      setStageFormError('')
                                    } else {
                                      setStageFormRouteId(route.id)
                                      setNewStagePosition(String(activeCount + 1))
                                      setStageFormError('')
                                    }
                                  }}
                                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                                >
                                  <Plus size={14} />
                                  {stageFormRouteId === route.id ? 'Cancel' : 'Add stage'}
                                </button>
                              </div>

                              {stageFormRouteId === route.id && (
                                <form
                                  onSubmit={handleCreateStage}
                                  className="mb-5 rounded-xl border border-blue-100 bg-white p-4"
                                >
                                  <h4 className="mb-4 text-sm font-semibold text-slate-800">
                                    Add a stage to {route.name}
                                  </h4>

                                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                                    <div className="lg:col-span-2">
                                      <label className="mb-1.5 block text-xs font-semibold text-slate-600">
                                        Stage name *
                                      </label>
                                      <input
                                        type="text"
                                        value={newStageName}
                                        onChange={(event) => setNewStageName(event.target.value)}
                                        placeholder="e.g. Kasarani"
                                        required
                                        maxLength={100}
                                        className={inputClass}
                                      />
                                    </div>

                                    <div>
                                      <label className="mb-1.5 block text-xs font-semibold text-slate-600">
                                        Latitude *
                                      </label>
                                      <input
                                        type="number"
                                        step="any"
                                        min="-90"
                                        max="90"
                                        value={newStageLatitude}
                                        onChange={(event) => setNewStageLatitude(event.target.value)}
                                        placeholder="-1.2345"
                                        required
                                        className={inputClass}
                                      />
                                    </div>

                                    <div>
                                      <label className="mb-1.5 block text-xs font-semibold text-slate-600">
                                        Longitude *
                                      </label>
                                      <input
                                        type="number"
                                        step="any"
                                        min="-180"
                                        max="180"
                                        value={newStageLongitude}
                                        onChange={(event) => setNewStageLongitude(event.target.value)}
                                        placeholder="36.8765"
                                        required
                                        className={inputClass}
                                      />
                                    </div>

                                    <div>
                                      <label className="mb-1.5 block text-xs font-semibold text-slate-600">
                                        Insert at position *
                                      </label>
                                      <input
                                        type="number"
                                        min="1"
                                        max={stages.filter((stage) => !stage.is_archived).length + 1}
                                        step="1"
                                        value={newStagePosition}
                                        onChange={(event) => setNewStagePosition(event.target.value)}
                                        required
                                        className={inputClass}
                                      />
                                      <p className="mt-1 text-xs text-slate-500">
                                        Active stages only; defaults to the end.
                                      </p>
                                    </div>
                                  </div>

                                  {stageFormError && (
                                    <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
                                      {stageFormError}
                                    </p>
                                  )}

                                  <div className="mt-4 flex justify-end gap-2">
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setStageFormRouteId(null)
                                        resetStageForm()
                                      }}
                                      disabled={stageFormLoading}
                                      className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                                    >
                                      Cancel
                                    </button>

                                    <button
                                      type="submit"
                                      disabled={stageFormLoading}
                                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                      {stageFormLoading ? 'Creating...' : 'Create stage'}
                                    </button>
                                  </div>
                                </form>
                              )}

                              {stages.length === 0 ? (
                                <p className="rounded-lg border border-dashed border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500">
                                  No stages have been added to this route yet.
                                </p>
                              ) : (
              <>
                                {reorderingRouteId === route.id && (
                          <p className="text-xs text-blue-600">
                            Saving stage order...
                          </p>
                        )}

                        {reorderErrors[route.id] && (
                          <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">
                            {reorderErrors[route.id]}
                          </p>
                        )}

                        <ol className="space-y-2">
                                  {stages.map((stage) => (
                                    <li
  key={stage.id}
  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3"
>
  <div className="flex min-w-0 items-start gap-3">
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-xs font-bold text-blue-700">
      {stage.sequence_number}
    </span>
    <div className="min-w-0">
      <p className="font-medium text-slate-800">{stage.name}</p>
      <p className="mt-1 text-xs text-slate-500">
        {stage.latitude != null && stage.longitude != null
          ? `${stage.latitude}, ${stage.longitude}`
          : 'Coordinates not set'}
      </p>
    </div>
  </div>

  <div className="flex flex-wrap items-center gap-2">
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
        stage.is_archived
          ? 'bg-amber-50 text-amber-700'
          : 'bg-emerald-50 text-emerald-700'
      }`}
    >
      {stage.is_archived ? 'Archived' : 'Active'}
    </span>

    {!stage.is_archived && (
      <>
        <button
          type="button"
          title="Move stage up"
          aria-label={`Move ${stage.name} up`}
          disabled={
            reorderingRouteId === route.id ||
            activeStages.findIndex((item) => item.id === stage.id) <= 0
          }
          onClick={() => handleReorderStage(stage.id, route.id, -1)}
          className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronUp size={15} />
        </button>
        <button
          type="button"
          title="Move stage down"
          aria-label={`Move ${stage.name} down`}
          disabled={
            reorderingRouteId === route.id ||
            activeStages.findIndex((item) => item.id === stage.id) ===
              activeStages.length - 1
          }
          onClick={() => handleReorderStage(stage.id, route.id, 1)}
          className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronDown size={15} />
        </button>
      </>
    )}

    <button
      type="button"
      disabled={editStageLoading}
      onClick={() => {
        if (editingStageId === stage.id) {
          setEditingStageId(null)
          setEditStageError('')
        } else {
          setEditingStageId(stage.id)
          setEditStageName(stage.name || '')
          setEditStageLatitude(
            stage.latitude == null ? '' : String(stage.latitude)
          )
          setEditStageLongitude(
            stage.longitude == null ? '' : String(stage.longitude)
          )
          setEditStageError('')
        }
      }}
      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
    >
      <Pencil size={13} />
      {editingStageId === stage.id ? 'Cancel' : 'Edit'}
    </button>

    {!stage.is_archived && (
      <button
        type="button"
        disabled={archivingStageId === stage.id || editStageLoading}
        onClick={() =>
          handleArchiveStage(stage.id, route.id, stage.name)
        }
        className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 px-3 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {archivingStageId === stage.id ? 'Archiving...' : 'Archive'}
      </button>
    )}

    {stage.is_archived && (
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="number"
          min="1"
          max={stages.filter((item) => !item.is_archived).length + 1}
          step="1"
          value={restoreStagePosition}
          onChange={(event) => {
            setRestoreStagePosition(event.target.value)
            setRestoreStageError('')
          }}
          aria-label={`New position for ${stage.name}`}
          className="w-20 rounded-lg border border-slate-200 px-2 py-2 text-xs outline-none focus:border-blue-500"
        />
        <button
          type="button"
          disabled={restoringStageId === stage.id}
          onClick={() => handleRestoreStage(stage.id, route.id)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {restoringStageId === stage.id ? 'Restoring...' : 'Restore'}
        </button>
        <button
          type="button"
          disabled={deletingStageId === stage.id || restoringStageId === stage.id}
          onClick={() =>
            handleDeleteStage(stage.id, route.id, stage.name)
          }
          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {deletingStageId === stage.id ? 'Deleting...' : 'Delete permanently'}
        </button>
      </div>
    )}
  </div>

  {restoreStageError && stage.is_archived && (
    <p className="w-full rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">
      {restoreStageError}
    </p>
  )}

  {deleteStageErrors[stage.id] && stage.is_archived && (
    <p className="w-full rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">
      {deleteStageErrors[stage.id]}
    </p>
  )}

  {editingStageId === stage.id && (
    <form
      onSubmit={(event) => handleUpdateStage(event, stage.id, route.id)}
      className="w-full rounded-xl border border-blue-100 bg-slate-50 p-4"
    >
      <h4 className="mb-3 text-sm font-semibold text-slate-800">
        Edit stage: {stage.name}
      </h4>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-slate-600">
            Stage name *
          </label>
          <input
            type="text"
            value={editStageName}
            onChange={(event) => setEditStageName(event.target.value)}
            maxLength={100}
            required
            className={inputClass}
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold text-slate-600">
            Latitude *
          </label>
          <input
            type="number"
            step="any"
            min="-90"
            max="90"
            value={editStageLatitude}
            onChange={(event) => setEditStageLatitude(event.target.value)}
            required
            className={inputClass}
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold text-slate-600">
            Longitude *
          </label>
          <input
            type="number"
            step="any"
            min="-180"
            max="180"
            value={editStageLongitude}
            onChange={(event) => setEditStageLongitude(event.target.value)}
            required
            className={inputClass}
          />
        </div>
      </div>

      {editStageError && (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {editStageError}
        </p>
      )}

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          disabled={editStageLoading}
          onClick={() => {
            setEditingStageId(null)
            setEditStageError('')
          }}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          Cancel
        </button>

        <button
          type="submit"
          disabled={editStageLoading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {editStageLoading ? 'Saving...' : 'Save changes'}
        </button>
      </div>
    </form>
  )}
</li>
                                  ))}
                                </ol>
              </>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : null}
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
            aria-labelledby="route-modal-title"
            className="my-auto w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3
                  id="route-modal-title"
                  className="text-lg font-bold text-slate-900"
                >
                  {modal.type === 'create' ? 'Create route' : 'Edit route'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  Enter the route details below.
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

            <form onSubmit={handleRouteSubmit} className="mt-5 space-y-4">
              <div>
                <label
                  htmlFor="route-name"
                  className="mb-1.5 block text-sm font-medium text-slate-700"
                >
                  Route name
                </label>
                <input
                  id="route-name"
                  value={routeName}
                  onChange={(event) => setRouteName(event.target.value)}
                  maxLength={150}
                  required
                  className={inputClass}
                  placeholder="e.g. Nairobi - Thika"
                />
              </div>

              <div>
                <label
                  htmlFor="route-description"
                  className="mb-1.5 block text-sm font-medium text-slate-700"
                >
                  Description (optional)
                </label>
                <textarea
                  id="route-description"
                  value={routeDescription}
                  onChange={(event) => setRouteDescription(event.target.value)}
                  rows={3}
                  className={inputClass}
                  placeholder="Add a short description of this route."
                />
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
                  {modalLoading
                    ? 'Saving...'
                    : modal.type === 'create'
                      ? 'Create route'
                      : 'Save changes'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}