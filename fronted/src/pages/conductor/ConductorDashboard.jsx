import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle,
  RefreshCw,
  Bus,
  MapPin,
  QrCode,
  BellRing,
  ArrowRight,
  Play,
  RotateCcw,
  CheckCircle2,
  Users,
  Navigation,
  Flag,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import {
  getConductorDashboard,
  moveConductorMatatu,
  resetConductorMatatu,
} from '../../services/conductorApi'

export default function ConductorDashboard() {
  const { currentUser } = useAuth()
  const matatuId = currentUser?.matatu?.id || 1

  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  async function loadDashboard(showLoading = false) {
    try {
      if (showLoading) setLoading(true)
      setError('')
      const data = await getConductorDashboard(matatuId)
      setDashboard(data)
    } catch (err) {
      setError(err.message || 'Could not load destinations.')
    } finally {
      if (showLoading) setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard(true)

    const intervalId = setInterval(() => {
      loadDashboard(false)
    }, 2500)

    return () => clearInterval(intervalId)
  }, [matatuId])

  const handleAdvanceStop = async () => {
    setActionLoading(true)
    try {
      await moveConductorMatatu(matatuId)
      await loadDashboard(false)
    } catch (err) {
      setError(err.message || 'Could not advance vehicle stop.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleResetTrip = async () => {
    if (!window.confirm('Reset this vehicle back to the first route stage?')) return
    setActionLoading(true)
    try {
      await resetConductorMatatu(matatuId)
      await loadDashboard(false)
    } catch (err) {
      setError(err.message || 'Could not reset vehicle trip.')
    } finally {
      setActionLoading(false)
    }
  }

  const currentSequence = dashboard?.location?.current_stage_sequence || 0
  const stages = dashboard?.stages || []

  const currentStage =
    stages.find((s) => s.sequence_number === currentSequence) || stages[0]

  const nextStage =
    stages.find((s) => s.sequence_number === currentSequence + 1) || null

  // Group passengers by their destination stage
  const stageGroups = useMemo(() => {
    return Object.values(
      (dashboard?.passengers || []).reduce((groups, passenger) => {
        const key = passenger.destination_stage_id ?? passenger.destination

        if (!groups[key]) {
          groups[key] = {
            stageId: key,
            stage: passenger.destination,
            sequence: passenger.stage_sequence,
            passengers: [],
          }
        }

        groups[key].passengers.push(passenger)
        return groups
      }, {})
    ).sort((a, b) => {
      if (a.sequence == null) return 1
      if (b.sequence == null) return -1
      return a.sequence - b.sequence
    })
  }, [dashboard?.passengers])

  // Passengers alighting at current stage
  const alightingCurrent = useMemo(() => {
    if (!currentStage) return []
    return (dashboard?.passengers || []).filter(
      (p) => p.stage_sequence === currentStage.sequence_number
    )
  }, [dashboard?.passengers, currentStage])

  // Passengers alighting at next stage
  const alightingNext = useMemo(() => {
    if (!nextStage) return []
    return (dashboard?.passengers || []).filter(
      (p) => p.stage_sequence === nextStage.sequence_number
    )
  }, [dashboard?.passengers, nextStage])

  return (
    <main className="mx-auto w-full max-w-5xl p-5 sm:p-8 space-y-6">
      {/* Header */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <span className="badge badge-primary text-xs font-semibold mb-1">
            Conductor Workspace
          </span>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            Trip & Passenger Destinations
          </h1>
          <p className="mt-0.5 text-sm text-slate-600">
            Monitor route progress, manage vehicle movement, and review upcoming passenger alighting stops.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/conductor/qr-code"
            className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-slate-900 px-3.5 py-2 text-xs font-bold text-white transition hover:bg-slate-800 shadow-sm"
          >
            <QrCode size={16} /> Passenger QR Code
          </Link>
          <Link
            to="/conductor/emergency-alerts"
            className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50 shadow-sm"
          >
            <BellRing size={16} className="text-amber-500" /> Alerts
          </Link>
        </div>
      </header>

      {loading && !dashboard && (
        <div className="p-8 text-center text-slate-500">
          <RefreshCw size={24} className="mx-auto animate-spin text-primary mb-2" />
          <p className="text-sm">Loading conductor workspace...</p>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <p className="text-sm font-medium">{error}</p>
          </div>
          <button
            type="button"
            onClick={() => loadDashboard(true)}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
          >
            <RefreshCw size={14} /> Try again
          </button>
        </div>
      )}

      {dashboard && (
        <>
          {/* VEHICLE & ROUTE CARD */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3.5">
                <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                  <Bus size={28} />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Assigned Vehicle
                  </span>
                  <h2 className="text-xl font-black text-slate-900 leading-tight">
                    {dashboard.vehicle.registration_number}
                  </h2>
                  <p className="text-sm font-medium text-slate-600 flex items-center gap-1.5 mt-0.5">
                    <Navigation size={14} className="text-primary" />
                    <span>Route: {dashboard.vehicle.route_name}</span>
                  </p>
                </div>
              </div>

              {/* Status and Count Badges */}
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <span className="text-xs text-slate-400 font-medium block">
                    Registered Onboard
                  </span>
                  <span className="text-lg font-extrabold text-slate-900">
                    {dashboard.passenger_count || 0} passengers
                  </span>
                </div>
                <div className="rounded-xl bg-slate-100 p-2 text-slate-700">
                  <Users size={22} />
                </div>
              </div>
            </div>

            {/* Current Stage & Movement Controls */}
            <div className="pt-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Current Position
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="flex h-2.5 w-2.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                  </span>
                  <p className="text-base font-bold text-slate-800">
                    {currentStage
                      ? `Stop #${currentStage.sequence_number}: ${currentStage.name}`
                      : 'At Starting Depot'}
                  </p>
                  <span className="badge badge-sm badge-outline font-mono text-[11px]">
                    Speed: {dashboard.location?.speed != null ? `${Number(dashboard.location.speed).toFixed(0)} km/h` : '0 km/h'}
                  </span>
                </div>
              </div>

              {/* Conductor Movement Buttons */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn btn-primary btn-sm gap-2 font-bold shadow-md shadow-primary/20"
                  onClick={handleAdvanceStop}
                  disabled={actionLoading}
                >
                  <Play size={14} className={actionLoading ? 'animate-spin' : ''} />
                  {actionLoading ? 'Advancing...' : 'Advance to Next Stop'}
                </button>
                <button
                  type="button"
                  className="btn btn-outline btn-sm gap-1.5"
                  onClick={handleResetTrip}
                  disabled={actionLoading}
                  title="Reset vehicle back to starting stop"
                >
                  <RotateCcw size={14} />
                  Reset
                </button>
              </div>
            </div>
          </section>

          {/* ALIGHTING NOTIFICATIONS */}
          {alightingCurrent.length > 0 && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/90 p-4 text-emerald-950 flex items-start gap-3 shadow-sm">
              <CheckCircle2 size={24} className="text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-extrabold text-sm">
                  {alightingCurrent.length} Passenger{alightingCurrent.length > 1 ? 's' : ''} Alighting Here ({currentStage?.name})
                </h3>
                <p className="text-xs text-emerald-800 mt-0.5">
                  Tokens: {alightingCurrent.map((p) => p.passenger_id).join(', ')}
                </p>
              </div>
            </div>
          )}

          {alightingNext.length > 0 && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50/90 p-4 text-amber-950 flex items-start gap-3 shadow-sm">
              <AlertCircle size={24} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-extrabold text-sm">
                  Next Stop Warning: {alightingNext.length} Passenger{alightingNext.length > 1 ? 's' : ''} Alighting at {nextStage?.name}
                </h3>
                <p className="text-xs text-amber-800 mt-0.5">
                  Prepare for passengers alighting at the upcoming stop. Tokens: {alightingNext.map((p) => p.passenger_id).join(', ')}
                </p>
              </div>
            </div>
          )}

          {/* PASSENGER DESTINATIONS BREAKDOWN */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <MapPin size={20} className="text-primary" />
                Alighting Stops & Passenger Groups
              </h2>
              <span className="text-xs text-slate-500 font-medium">
                Admin Route Sequence
              </span>
            </div>

            {stages.length === 0 && (
              <p className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
                No route stages configured for this vehicle yet.
              </p>
            )}

            {stages.length > 0 && (
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-900 text-white text-xs uppercase tracking-wider">
                    <tr>
                      <th className="px-5 py-3.5 font-bold">Stop #</th>
                      <th className="px-5 py-3.5 font-bold">Stage Name</th>
                      <th className="px-5 py-3.5 font-bold text-center">Status</th>
                      <th className="px-5 py-3.5 font-bold text-center">Passengers Alighting</th>
                      <th className="px-5 py-3.5 font-bold">Passenger Tokens</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {stages.map((stage) => {
                      const isCurrent = currentSequence === stage.sequence_number
                      const isPassed = currentSequence > stage.sequence_number
                      const passengersAtStage = (dashboard.passengers || []).filter(
                        (p) =>
                          p.destination_stage_id === stage.id ||
                          p.destination === stage.name
                      )

                      return (
                        <tr
                          key={stage.id}
                          className={`transition-colors ${
                            isCurrent
                              ? 'bg-primary/10 font-semibold'
                              : isPassed
                              ? 'bg-slate-50/70 text-slate-400'
                              : 'hover:bg-slate-50/50'
                          }`}
                        >
                          <td className="px-5 py-3.5 font-mono text-xs text-slate-500">
                            #{stage.sequence_number}
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="font-bold text-slate-900">
                              {stage.name}
                            </span>
                            {stage.sequence_number === 1 && (
                              <span className="ml-2 text-[10px] font-semibold text-slate-400 uppercase">
                                Origin
                              </span>
                            )}
                            {stage.sequence_number === stages.length && (
                              <span className="ml-2 text-[10px] font-semibold text-slate-400 uppercase">
                                Terminal
                              </span>
                            )}
                          </td>
                          <td className="px-5 py-3.5 text-center">
                            {isCurrent ? (
                              <span className="badge badge-primary badge-sm font-bold gap-1">
                                <Bus size={12} /> Current Stop
                              </span>
                            ) : isPassed ? (
                              <span className="badge badge-ghost badge-sm text-slate-400 gap-1">
                                <CheckCircle2 size={12} className="text-emerald-500" /> Passed
                              </span>
                            ) : (
                              <span className="badge badge-outline badge-sm text-slate-500">
                                Upcoming
                              </span>
                            )}
                          </td>
                          <td className="px-5 py-3.5 text-center">
                            {passengersAtStage.length > 0 ? (
                              <span className="badge badge-success font-bold text-xs">
                                {passengersAtStage.length} alighting
                              </span>
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            )}
                          </td>
                          <td className="px-5 py-3.5">
                            {passengersAtStage.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {passengersAtStage.map((p) => (
                                  <span
                                    key={p.id}
                                    className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-semibold text-slate-700 ring-1 ring-slate-200"
                                  >
                                    {p.passenger_id}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-xs text-slate-400">None</span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  )
}
