import {
  Bus,
  Users,
  Route,
  MapPin,
  ArrowUpRight,
  ArrowDownRight,
  MoreHorizontal,
} from 'lucide-react'

const stats = [
  {
    title: 'Registered matatus',
    value: '128',
    change: '+8.2%',
    positive: true,
    description: 'compared with last month',
    icon: Bus,
    color: 'blue',
  },
  {
    title: 'Registered users',
    value: '2,450',
    change: '+12.5%',
    positive: true,
    description: 'compared with last month',
    icon: Users,
    color: 'violet',
  },
  {
    title: 'Active routes',
    value: '36',
    change: '+2',
    positive: true,
    description: 'routes added this month',
    icon: Route,
    color: 'emerald',
  },
  {
    title: 'Active trips',
    value: '74',
    change: '-3.1%',
    positive: false,
    description: 'compared with yesterday',
    icon: MapPin,
    color: 'amber',
  },
]

const recentTrips = [
  { vehicle: 'KDA 123A', route: 'Kisii – Nairobi', conductor: 'Demo User 1', status: 'In progress' },
  { vehicle: 'KDB 456B', route: 'Kisii – Oyugis', conductor: 'Demo User 2', status: 'Completed' },
  { vehicle: 'KDC 789C', route: 'Kisii – Homa Bay', conductor: 'Demo User 3', status: 'In progress' },
  { vehicle: 'KDD 234D', route: 'Kisii – Keroka', conductor: 'Demo User 4', status: 'Pending' },
]

const colorClasses = {
  blue: 'bg-blue-50 text-blue-600',
  violet: 'bg-violet-50 text-violet-600',
  emerald: 'bg-emerald-50 text-emerald-600',
  amber: 'bg-amber-50 text-amber-600',
}

function StatCard({ stat }) {
  const Icon = stat.icon
  const TrendIcon = stat.positive ? ArrowUpRight : ArrowDownRight

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${colorClasses[stat.color]}`}>
          <Icon size={22} />
        </div>
        <button
          type="button"
          aria-label={`More options for ${stat.title}`}
          className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"
        >
          <MoreHorizontal size={20} />
        </button>
      </div>

      <p className="mt-5 text-sm font-medium text-slate-500">{stat.title}</p>
      <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">{stat.value}</p>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`inline-flex items-center gap-1 font-semibold ${stat.positive ? 'text-emerald-600' : 'text-rose-600'}`}>
          <TrendIcon size={14} />
          {stat.change}
        </span>
        <span className="text-slate-400">{stat.description}</span>
      </div>
    </article>
  )
}

export default function Dashboard() {
  return (
    <div className="mx-auto max-w-7xl space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-blue-600">OVERVIEW</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
            Dashboard
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Monitor fleet activity and manage your transport platform.
          </p>
        </div>

        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          Demo data — not connected to backend
        </span>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.title} stat={stat} />
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-2 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-slate-900">Recent trips</h3>
              <p className="mt-1 text-sm text-slate-500">Example fleet activity</p>
            </div>
            <span className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600">
              Sample records
            </span>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
                  <th className="pb-3 pr-4 font-semibold">Vehicle</th>
                  <th className="pb-3 pr-4 font-semibold">Route</th>
                  <th className="pb-3 pr-4 font-semibold">Conductor</th>
                  <th className="pb-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentTrips.map((trip) => (
                  <tr key={trip.vehicle} className="border-b border-slate-50 last:border-0">
                    <td className="py-4 pr-4 font-semibold text-slate-800">{trip.vehicle}</td>
                    <td className="py-4 pr-4 text-slate-600">{trip.route}</td>
                    <td className="py-4 pr-4 text-slate-600">{trip.conductor}</td>
                    <td className="py-4">
                      <span
                        className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${
                          trip.status === 'Completed'
                            ? 'bg-emerald-50 text-emerald-700'
                            : trip.status === 'In progress'
                              ? 'bg-blue-50 text-blue-700'
                              : 'bg-amber-50 text-amber-700'
                        }`}
                      >
                        {trip.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h3 className="font-bold text-slate-900">Platform checklist</h3>
          <p className="mt-1 text-sm text-slate-500">Development milestones</p>

          <div className="mt-6 space-y-5">
            {[
              ['React frontend', 'Current workspace', true],
              ['Admin navigation', 'Routes and page structure', true],
              ['Backend integration', 'Connect real API endpoints', false],
              ['Authentication', 'Protect admin-only routes', false],
            ].map(([title, description, complete]) => (
              <div key={title} className="flex gap-3">
                <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${complete ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                  {complete ? '✓' : '•'}
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{title}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
