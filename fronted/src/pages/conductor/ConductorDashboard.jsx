import { Link } from 'react-router-dom'
import {
  Bus, MapPin, Clock3, Users, ArrowRight,
  Navigation, CheckCircle2, AlertCircle
} from 'lucide-react'

const stats = [
  { label: 'Assigned vehicle', value: 'KDA 123A', detail: 'Demo vehicle', icon: Bus },
  { label: 'Passengers onboard', value: '18', detail: 'Demo count', icon: Users },
  { label: 'Destination requests', value: '4', detail: 'Demo requests', icon: MapPin },
  { label: 'Estimated arrival', value: '—', detail: 'Waiting for live GPS', icon: Clock3 },
]

const requests = [
  { id: 'REQ-001', stage: 'Kisii University', passengers: 2, status: 'Pending' },
  { id: 'REQ-002', stage: 'Daraja Mbili', passengers: 1, status: 'Pending' },
  { id: 'REQ-003', stage: 'Kisii CBD', passengers: 3, status: 'Reviewed' },
]

export default function ConductorDashboard() {
  return (
    <div className="space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-medium text-emerald-700">CONDUCTOR OVERVIEW</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">Good day, Conductor</h2>
          <p className="mt-2 text-slate-500">Review your assigned trip and passenger requests.</p>
        </div>
        <Link
          to="/conductor/trip"
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 font-semibold text-white shadow-sm hover:bg-emerald-700"
        >
          View current trip <ArrowRight size={18} />
        </Link>
      </section>

      <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
        <AlertCircle size={21} className="mt-0.5 shrink-0" />
        <div>
          <p className="font-semibold">Demo data is being displayed</p>
          <p className="mt-1 text-sm text-amber-800">
            Vehicle, passenger and request figures below are examples, not live backend records.
            GPS-based distance and ETA are not connected yet.
          </p>
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(({ label, value, detail, icon: Icon }) => (
          <article key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-500">{label}</span>
              <span className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700">
                <Icon size={20} />
              </span>
            </div>
            <p className="mt-4 text-2xl font-bold">{value}</p>
            <p className="mt-1 text-xs text-slate-500">{detail}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 xl:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-bold">Current assignment</h3>
              <p className="mt-1 text-sm text-slate-500">Example trip information</p>
            </div>
            <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
              Scheduled · Demo
            </span>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Vehicle registration</p>
              <p className="mt-1 text-xl font-bold">KDA 123A</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Route</p>
              <p className="mt-1 text-xl font-bold">Kisii – Example Route</p>
            </div>
          </div>

          <div className="mt-5 flex items-start gap-3 rounded-xl border border-slate-200 p-4">
            <Navigation size={20} className="mt-1 text-emerald-600" />
            <div>
              <p className="font-semibold">Route progress</p>
              <p className="mt-1 text-sm text-slate-500">
                Live location and next-stage information will appear here after GPS integration.
              </p>
            </div>
          </div>

          <Link to="/conductor/trip" className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-emerald-700 hover:text-emerald-900">
            Open trip details <ArrowRight size={16} />
          </Link>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <h3 className="text-lg font-bold">Quick actions</h3>
          <p className="mt-1 text-sm text-slate-500">Navigate to your work areas.</p>
          <div className="mt-5 space-y-3">
            <Link to="/conductor/requests" className="flex items-center gap-3 rounded-xl border border-slate-200 p-4 hover:border-emerald-300 hover:bg-emerald-50/50">
              <MapPin className="text-emerald-700" size={21} />
              <span className="flex-1 text-sm font-semibold">Review destination requests</span>
              <ArrowRight size={16} />
            </Link>
            <Link to="/conductor/history" className="flex items-center gap-3 rounded-xl border border-slate-200 p-4 hover:border-emerald-300 hover:bg-emerald-50/50">
              <Clock3 className="text-emerald-700" size={21} />
              <span className="flex-1 text-sm font-semibold">View trip history</span>
              <ArrowRight size={16} />
            </Link>
          </div>
          <div className="mt-5 flex items-center gap-2 text-xs text-slate-500">
            <CheckCircle2 size={15} className="text-emerald-600" />
            Interface preview only
          </div>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold">Recent destination requests</h3>
            <p className="mt-1 text-sm text-slate-500">Illustrative passenger requests</p>
          </div>
          <Link to="/conductor/requests" className="text-sm font-semibold text-emerald-700 hover:text-emerald-900">
            View all
          </Link>
        </div>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-3 pr-4 font-medium">Request</th>
                <th className="pb-3 pr-4 font-medium">Destination stage</th>
                <th className="pb-3 pr-4 font-medium">Passengers</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id} className="border-b border-slate-100 last:border-0">
                  <td className="py-4 pr-4 font-semibold">{request.id}</td>
                  <td className="py-4 pr-4">{request.stage}</td>
                  <td className="py-4 pr-4">{request.passengers}</td>
                  <td className="py-4">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      request.status === 'Pending'
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-emerald-50 text-emerald-700'
                    }`}>
                      {request.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
