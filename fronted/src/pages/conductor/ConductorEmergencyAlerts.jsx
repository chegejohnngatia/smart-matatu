
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  BellRing,
  CheckCircle,
  Clock,
  ChevronDown,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import {
  getConductorEmergencyAlerts,
  acknowledgeEmergencyAlert,
} from '../../services/conductorApi'

function formatAlertTime(value) {
  if (!value) return 'Time unavailable'

  const normalized = value.includes('T')
    ? value
    : `${value.replace(' ', 'T')}Z`

  const date = new Date(normalized)

  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString()
}

function AlertCard({ alert, onAcknowledge, acknowledgingId }) {
  const isAcknowledging = acknowledgingId === alert.alert_id

  return (
    <article className="rounded-xl border-2 border-red-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-red-100 p-3 text-red-600">
            <BellRing size={22} />
          </div>

          <div>
            <h3 className="font-semibold text-red-700">
              Passenger needs attention
            </h3>

            <p className="mt-1 text-sm text-slate-600">
              Passenger: {alert.passenger_id}
            </p>

            <p className="text-sm text-slate-600">
              Journey ID: {alert.journey_id}
            </p>

            <p className="mt-3 whitespace-pre-wrap text-slate-800">
              {alert.message}
            </p>

            <p className="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <Clock size={14} />
              {formatAlertTime(alert.created_at)}
            </p>
          </div>
        </div>

        <button
          type="button"
          disabled={isAcknowledging}
          onClick={() => onAcknowledge(alert.alert_id)}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <CheckCircle size={16} />
          {isAcknowledging ? 'Processing...' : 'Acknowledge'}
        </button>
      </div>
    </article>
  )
}

export default function ConductorEmergencyAlerts() {
  // Retrieve the authenticated session's CSRF token.
  const { csrfToken } = useAuth()

  const [emergencyAlerts, setEmergencyAlerts] = useState({
    unresolved_count: 0,
    active_alerts: [],
    history: [],
  })

  const [loading, setLoading] = useState(true)
  const [alertError, setAlertError] = useState('')
  const [acknowledgingId, setAcknowledgingId] = useState(null)
  const [acknowledgementError, setAcknowledgementError] = useState('')
  const [acknowledgementMessage, setAcknowledgementMessage] = useState('')

  const [activeExpanded, setActiveExpanded] = useState(false)
  const [historyExpanded, setHistoryExpanded] = useState(false)

  const requestInProgress = useRef(false)

  const loadEmergencyAlerts = useCallback(async (showLoading = false) => {
    // Prevent overlapping requests.
    if (requestInProgress.current) return

    requestInProgress.current = true

    try {
      if (showLoading) setLoading(true)

      setAlertError('')

      const data = await getConductorEmergencyAlerts()
      setEmergencyAlerts(data)
    } catch (err) {
      setAlertError(err.message || 'Could not load emergency alerts.')
    } finally {
      setLoading(false)
      requestInProgress.current = false
    }
  }, [])

  useEffect(() => {
    loadEmergencyAlerts(true)

    const intervalId = setInterval(() => {
      loadEmergencyAlerts()
    }, 1000)

    return () => clearInterval(intervalId)
  }, [loadEmergencyAlerts])

  async function handleAcknowledge(alertId) {
    if (acknowledgingId !== null) return

    setAcknowledgingId(alertId)
    setAcknowledgementError('')
    setAcknowledgementMessage('')

    try {
      // Send the authenticated session's CSRF token.
      await acknowledgeEmergencyAlert(alertId, csrfToken)

      setAcknowledgementMessage('Alert acknowledged successfully.')

      await loadEmergencyAlerts()
    } catch (err) {
      setAcknowledgementError(
        err.message || 'Could not acknowledge this alert.'
      )
    } finally {
      setAcknowledgingId(null)
    }
  }

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header className="mb-8">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
            <BellRing className="text-red-600" size={25} />
            Emergency Alerts
          </h2>

          <p className="mt-2 text-slate-600">
            Important passenger issues that need your attention.
          </p>

          <p className="mt-1 text-xs text-emerald-700">
            <span className="mr-2 inline-block h-2 w-2 rounded-full bg-emerald-500" />
            Alerts update automatically.
          </p>
        </div>
      </header>

      <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-medium text-red-800">
          Alerts requiring your attention
        </p>

        <p className="mt-1 text-3xl font-bold text-red-700">
          {emergencyAlerts.unresolved_count}
        </p>

        <p className="mt-2 text-sm text-red-700">
          Acknowledging an alert records that you have seen it. It does not
          confirm a passenger's payment or mean a reported issue has been resolved.
        </p>
      </div>

      {acknowledgementMessage && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          <CheckCircle size={18} />
          {acknowledgementMessage}
        </div>
      )}

      {acknowledgementError && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle size={18} />
          {acknowledgementError}
        </div>
      )}

      {loading && (
        <p className="py-4 text-slate-600">
          Loading emergency alerts...
        </p>
      )}

      {!loading && alertError && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <p>{alertError}</p>
          </div>

          <p className="mt-2 text-sm">
            The system will keep trying to retrieve new alerts automatically.
          </p>
        </div>
      )}

      {!loading && (
        <>
          {/* Active alerts */}
          <section className="mb-6">
            <button
              type="button"
              onClick={() => setActiveExpanded((previous) => !previous)}
              aria-expanded={activeExpanded}
              className="mb-4 flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:bg-slate-50"
            >
              <span className="font-semibold text-slate-900">
                Active alerts
              </span>

              <span className="flex items-center gap-3">
                <span className="rounded-full bg-red-100 px-3 py-1 text-sm font-bold text-red-700">
                  {emergencyAlerts.unresolved_count}
                </span>

                <ChevronDown
                  size={20}
                  className={`transition-transform ${
                    activeExpanded ? 'rotate-180' : ''
                  }`}
                />
              </span>
            </button>

            {activeExpanded && (
              emergencyAlerts.active_alerts.length === 0 ? (
                <div className="rounded-xl border border-slate-200 bg-white p-6 text-slate-600">
                  <CheckCircle className="mb-2 text-emerald-600" size={24} />
                  There are no active alerts.
                </div>
              ) : (
                <div className="space-y-4">
                  {emergencyAlerts.active_alerts.map((alert) => (
                    <AlertCard
                      key={alert.alert_id}
                      alert={alert}
                      onAcknowledge={handleAcknowledge}
                      acknowledgingId={acknowledgingId}
                    />
                  ))}
                </div>
              )
            )}
          </section>

          {/* Acknowledged history */}
          <section>
            <button
              type="button"
              onClick={() => setHistoryExpanded((previous) => !previous)}
              aria-expanded={historyExpanded}
              className="mb-4 flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:bg-slate-50"
            >
              <span className="font-semibold text-slate-900">
                Acknowledged alerts
              </span>

              <span className="flex items-center gap-3">
                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-700">
                  {emergencyAlerts.history.length}
                </span>

                <ChevronDown
                  size={20}
                  className={`transition-transform ${
                    historyExpanded ? 'rotate-180' : ''
                  }`}
                />
              </span>
            </button>

            {historyExpanded && (
              emergencyAlerts.history.length === 0 ? (
                <p className="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">
                  No acknowledged alerts yet.
                </p>
              ) : (
                <div className="space-y-4">
                  {emergencyAlerts.history.map((alert) => (
                    <article
                      key={alert.alert_id}
                      className="rounded-xl border border-slate-200 bg-white p-5"
                    >
                      <div className="flex items-start gap-3">
                        <CheckCircle
                          className="mt-1 shrink-0 text-emerald-600"
                          size={21}
                        />

                        <div>
                          <h4 className="font-semibold text-slate-900">
                            Alert acknowledged
                          </h4>

                          <p className="mt-1 text-sm text-slate-600">
                            Passenger: {alert.passenger_id} | Journey ID: {alert.journey_id}
                          </p>

                          <p className="mt-3 whitespace-pre-wrap text-slate-800">
                            {alert.message}
                          </p>

                          <p className="mt-3 text-xs text-slate-500">
                            Created: {formatAlertTime(alert.created_at)}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            Acknowledged: {formatAlertTime(alert.acknowledged_at)}
                          </p>

                          <p className="mt-3 text-sm text-slate-600">
                            Acknowledging this alert does not confirm payment or establish that a reported issue was resolved.
                          </p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )
            )}
          </section>
        </>
      )}
    </section>
  )
}
