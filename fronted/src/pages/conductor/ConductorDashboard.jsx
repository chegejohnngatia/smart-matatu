
import { useEffect, useState } from 'react'
import { AlertCircle, RefreshCw, Bus, MapPin } from 'lucide-react'
import { getConductorDashboard } from '../../services/conductorApi'

export default function ConductorDashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadDashboard(showLoading = false) {
    try {
      if (showLoading) setLoading(true)

      setError('')
      const data = await getConductorDashboard()
      setDashboard(data)
    } catch (err) {
      setError(err.message || 'Could not load destinations.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard(true)

    const dashboardIntervalId = setInterval(() => {
      loadDashboard()
    }, 1000)

    return () => {
      clearInterval(dashboardIntervalId)
    }
  }, [])

  const stageGroups = Object.values(
    (dashboard?.passengers || []).reduce((groups, passenger) => {
      const key = passenger.destination_stage_id ?? passenger.destination

      if (!groups[key]) {
        groups[key] = {
          stageId: key,
          stage: passenger.destination,
          sequence: passenger.stage_sequence,
          passengerIds: [],
        }
      }

      groups[key].passengerIds.push(passenger.passenger_id)
      return groups
    }, {})
  ).sort((a, b) => {
    if (a.sequence == null) return 1
    if (b.sequence == null) return -1
    return a.sequence - b.sequence
  })

  return (
    <main className="mx-auto w-full max-w-5xl p-5 sm:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Passenger Destinations
        </h1>

        <p className="mt-1 text-slate-600">
          Your assigned matatu and the stages where passengers will alight.
        </p>
      </header>

      {loading && (
        <p className="text-slate-600">Loading destinations...</p>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <p>{error}</p>
          </div>

          <button
            type="button"
            onClick={() => loadDashboard(true)}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700"
          >
            <RefreshCw size={16} />
            Try again
          </button>
        </div>
      )}

      {!loading && !error && dashboard && (
        <>
          <section className="mb-8 rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-start gap-3">
              <Bus className="mt-1 text-emerald-600" size={25} />

              <div>
                <h2 className="font-semibold text-slate-800">
                  Assigned Matatu
                </h2>

                <p className="mt-1 text-xl font-bold text-slate-900">
                  {dashboard.vehicle.registration_number}
                </p>

                <p className="mt-1 text-slate-600">
                  Route: {dashboard.vehicle.route_name}
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-900">
              <MapPin size={21} className="text-emerald-600" />
              Passenger Destinations
            </h2>

            {stageGroups.length === 0 ? (
              <p className="rounded-xl border border-slate-200 bg-white p-5 text-slate-600">
                No passenger destinations have been recorded yet.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table className="w-full text-left">
                  <thead className="bg-slate-900 text-white">
                    <tr>
                      <th className="px-5 py-3 font-semibold">
                        Stage
                      </th>

                      <th className="px-5 py-3 font-semibold">
                        Passengers alighting
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {stageGroups.map((group, index) => (
                      <tr
                        key={group.stageId}
                        className={
                          index % 2 === 0
                            ? 'bg-white'
                            : 'bg-slate-50'
                        }
                      >
                        <td className="border-b border-slate-100 px-5 py-4 font-medium text-slate-800">
                          {group.stage}
                        </td>

                        <td className="border-b border-slate-100 px-5 py-4 text-slate-700">
                          <div className="flex flex-wrap gap-2">
                            {group.passengerIds.map((id, passengerIndex) => (
                              <span
                                key={`${id}-${passengerIndex}`}
                                className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-800"
                              >
                                {id}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
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
