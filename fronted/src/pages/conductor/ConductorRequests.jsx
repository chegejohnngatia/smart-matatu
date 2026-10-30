
import { useCallback, useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, Clock, XCircle } from 'lucide-react'
import {
  getDestinationChangeRequests,
  decideDestinationChangeRequest,
} from '../../services/conductorApi'

export default function ConductorRequests() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [processingId, setProcessingId] = useState(null)

  const loadRequests = useCallback(async (showLoading = false) => {
    try {
      if (showLoading) setLoading(true)

      const data = await getDestinationChangeRequests()
      setRequests(data)
      setError('')
    } catch (err) {
      setError(err.message || 'Could not load destination-change requests.')
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRequests(true)

    const intervalId = setInterval(() => {
      loadRequests()
    }, 1000)

    return () => clearInterval(intervalId)
  }, [loadRequests])

  async function handleDecision(requestId, action) {
    const actionLabel = action === 'approve' ? 'approve' : 'reject'

    const confirmed = window.confirm(
      `Are you sure you want to ${actionLabel} this destination-change request?`
    )

    if (!confirmed) return

    setProcessingId(requestId)
    setError('')
    setNotice('')

    try {
      const result = await decideDestinationChangeRequest(requestId, action)

      setNotice(result.message || 'Request resolved successfully.')

      await loadRequests()
    } catch (err) {
      setError(err.message || 'Could not resolve this request.')
    } finally {
      setProcessingId(null)
    }
  }

  return (
    <main className="mx-auto w-full max-w-5xl p-5 sm:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Destination Change Requests
        </h1>
        <p className="mt-1 text-slate-600">
          Review passenger requests and confirm changes with them before deciding.
        </p>
      </header>

      {error && (
        <div
          role="alert"
          className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700"
        >
          <AlertCircle size={20} className="mt-0.5 shrink-0" />
          <div className="flex-1">
            <p>{error}</p>
            <button
              type="button"
              onClick={() => loadRequests(true)}
              className="mt-2 inline-flex items-center gap-2 font-medium underline"
            >
              <RefreshCw size={15} />
              Try again
            </button>
          </div>
        </div>
      )}

      {notice && (
        <div
          role="status"
          className="mb-5 flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800"
        >
          <CheckCircle2 size={20} className="mt-0.5 shrink-0" />
          <p>{notice}</p>
        </div>
      )}

      <section>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Pending requests
          </h2>

          
        </div>

        {loading ? (
          <p className="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">
            Loading requests...
          </p>
        ) : requests.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
            <Clock size={30} className="mx-auto mb-3 text-slate-400" />
            <h3 className="font-semibold text-slate-800">
              No pending requests
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              New destination-change requests will appear here automatically.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {requests.map((item) => {
              const isProcessing = processingId === item.request_id

              return (
                <article
                  key={item.request_id}
                  className="rounded-xl border border-slate-200 bg-white p-5"
                >
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm text-slate-500">Passenger</p>
                      <h3 className="text-lg font-bold text-slate-900">
                        {item.passenger_id}
                      </h3>
                    </div>

                    <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800">
                      Pending
                    </span>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-lg bg-slate-50 p-3">
                      <p className="text-sm text-slate-500">
                        Current destination
                      </p>
                      <p className="mt-1 font-medium text-slate-800">
                        {item.current_destination || 'Unknown destination'}
                      </p>
                    </div>

                    <div className="rounded-lg bg-emerald-50 p-3">
                      <p className="text-sm text-emerald-700">
                        Requested destination
                      </p>
                      <p className="mt-1 font-medium text-emerald-900">
                        {item.requested_destination || 'Unknown destination'}
                      </p>
                    </div>
                  </div>

                  {item.created_at && (
                    <p className="mt-3 text-xs text-slate-500">
                      Submitted: {item.created_at}
                    </p>
                  )}

                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() =>
                        handleDecision(item.request_id, 'approve')
                      }
                      disabled={processingId !== null}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <CheckCircle2 size={17} />
                      {isProcessing ? 'Processing...' : 'Approve'}
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        handleDecision(item.request_id, 'reject')
                      }
                      disabled={processingId !== null}
                      className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 bg-white px-4 py-2 font-medium text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <XCircle size={17} />
                      Reject
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>
    </main>
  )
}
