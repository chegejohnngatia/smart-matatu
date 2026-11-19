import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Bus, Clock3, AlertCircle, Users, Navigation } from 'lucide-react'
import { getConductorDashboard } from '../../services/conductorApi'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'

function formatAgo(location, now) {
  if (!location?.last_updated_at) return ''

  const ageSeconds = Math.max(
    0,
    Math.floor((now - new Date(location.last_updated_at).getTime()) / 1000)
  )

  return `Updated ${ageSeconds}s ago`
}

function HistorySection() {
  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-primary/10 p-3 text-primary">
            <Clock3 size={24} />
          </span>
          <div>
            <h2 className="text-2xl font-bold">Trip History</h2>
            <p className="mt-1 text-sm text-slate-500">
              Completed journeys for your assigned vehicle.
            </p>
          </div>
        </div>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <div className="py-12 text-center">
          <Clock3 size={34} className="mx-auto text-slate-400" />
          <h3 className="mt-4 font-semibold">No trips recorded yet</h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
            Completed trips will appear here once journey records are kept for
            your vehicle.
          </p>
        </div>
      </section>
    </div>
  )
}

function TripSection() {
  const { currentUser } = useAuth()
  const matatuId = currentUser?.matatu?.id
  const [dashboard, setDashboard] = useState(null)
  const [location, setLocation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [now, setNow] = useState(() => Date.now())
  const requestInProgress = useRef(false)

  const loadTrip = useCallback(async (showLoading = false) => {
    if (!matatuId || requestInProgress.current) return

    requestInProgress.current = true

    try {
      if (showLoading) setLoading(true)

      const [dashboardData, statusData] = await Promise.all([
        getConductorDashboard(matatuId),
        api.getVehicleStatus(matatuId),
      ])

      setDashboard(dashboardData)
      setLocation(statusData.location || null)
      setError('')
    } catch (err) {
      setError(err.message || 'Could not load the current trip.')
    } finally {
      setLoading(false)
      requestInProgress.current = false
    }
  }, [matatuId])

  useEffect(() => {
    if (!matatuId) return

    loadTrip(true)

    const intervalId = setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadTrip()
      }
    }, 3000)

    const tickerId = setInterval(() => setNow(Date.now()), 1000)

    return () => {
      clearInterval(intervalId)
      clearInterval(tickerId)
    }
  }, [matatuId, loadTrip])

  if (loading) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 text-center text-sm text-slate-500 sm:p-6">
        Loading your current trip…
      </section>
    )
  }

  if (error) {
    return (
      <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-900">
        <AlertCircle size={20} className="mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-semibold">{error}</p>
          <button
            type="button"
            onClick={() => loadTrip(true)}
            className="mt-2 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-800 transition hover:bg-red-100"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const vehicle = dashboard?.vehicle
  const passengerCount = dashboard?.passenger_count ?? 0
  const gpsLive = Boolean(location && !location.stale)
  const gpsStatus = gpsLive
    ? 'Receiving GPS updates'
    : location
      ? 'GPS signal lost — showing the last reported position'
      : 'No GPS updates received yet'

  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-primary/10 p-3 text-primary">
            <Bus size={24} />
          </span>
          <div>
            <h2 className="text-2xl font-bold">Current Trip</h2>
            <p className="mt-1 text-sm text-slate-500">
              Your assigned vehicle, route and journey status.
            </p>
          </div>
        </div>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <div className="divide-y divide-slate-100">
          <div className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
            <span className="flex items-center gap-2 text-sm text-slate-500">
              <Bus size={16} /> Vehicle
            </span>
            <span className="text-sm font-semibold tabular-nums sm:text-right">
              {vehicle?.registration_number || '—'}
            </span>
          </div>

          <div className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
            <span className="flex items-center gap-2 text-sm text-slate-500">
              <Navigation size={16} /> Route
            </span>
            <span className="text-sm font-semibold sm:text-right">
              {vehicle?.route_name || '—'}
            </span>
          </div>

          <div className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
            <span className="flex items-center gap-2 text-sm text-slate-500">
              <Users size={16} /> Passengers onboard
            </span>
            <span className="text-sm font-semibold tabular-nums sm:text-right">
              {passengerCount}
            </span>
          </div>

          <div className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm text-slate-500">Connection</span>
            <span className="flex items-center gap-2 sm:text-right">
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
                  gpsLive
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-amber-100 text-amber-800'
                }`}
              >
                {gpsLive ? 'Live' : 'Offline'}
              </span>
              <span className="text-sm text-slate-500 tabular-nums">
                {formatAgo(location, now)}
              </span>
            </span>
          </div>

          <div className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm text-slate-500">GPS status</span>
            <span className="text-sm text-slate-700 sm:text-right">
              {gpsStatus}
            </span>
          </div>

          <div className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-sm text-slate-500">Speed</span>
            <span className="text-sm font-semibold tabular-nums sm:text-right">
              {location
                ? `${Number(location.speed || 0).toFixed(0)} km/h`
                : '—'}
            </span>
          </div>
        </div>
      </section>
    </div>
  )
}

export default function ConductorSectionPage() {
  const { pathname } = useLocation()

  return pathname === '/conductor/history' ? (
    <HistorySection />
  ) : (
    <TripSection />
  )
}
