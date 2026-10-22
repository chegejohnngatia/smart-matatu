import { useLocation } from 'react-router-dom'
import { Bus, MapPin, Clock3, AlertCircle } from 'lucide-react'

const sections = {
  '/conductor/trip': {
    title: 'Current Trip',
    description: 'Review your assigned vehicle, route and journey status.',
    icon: Bus,
    items: [
      ['Vehicle', 'KDA 123A (example)'],
      ['Route', 'Kisii – Example Route'],
      ['Trip status', 'Scheduled (demo)'],
      ['Current stage', 'Not connected to GPS'],
      ['Next stage', 'Not available yet'],
    ],
  },
  '/conductor/requests': {
    title: 'Destination Requests',
    description: 'Example passenger requests for the active trip.',
    icon: MapPin,
    items: [
      ['REQ-001', 'Kisii University · 2 passengers · Pending'],
      ['REQ-002', 'Daraja Mbili · 1 passenger · Pending'],
      ['REQ-003', 'Kisii CBD · 3 passengers · Reviewed'],
      ['REQ-004', 'Suneka Stage · 1 passenger · Pending'],
    ],
  },
  '/conductor/history': {
    title: 'Trip History',
    description: 'Completed trips will be listed here when connected to the backend.',
    icon: Clock3,
    items: [],
  },
}

export default function ConductorSectionPage() {
  const { pathname } = useLocation()
  const section = sections[pathname] ?? sections['/conductor/trip']
  const Icon = section.icon

  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-emerald-100 p-3 text-emerald-700">
            <Icon size={24} />
          </span>
          <div>
            <h2 className="text-2xl font-bold">{section.title}</h2>
            <p className="mt-1 text-sm text-slate-500">{section.description}</p>
          </div>
        </div>
      </header>

      <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
        <AlertCircle size={20} className="mt-0.5 shrink-0" />
        <p className="text-sm">
          Demo interface only. These records are illustrative; no live trip or passenger data is being retrieved.
        </p>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        {section.items.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {section.items.map(([label, value]) => (
              <div key={label} className="flex flex-col gap-1 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                <span className="text-sm text-slate-500">{label}</span>
                <span className="text-sm font-semibold sm:text-right">{value}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-12 text-center">
            <Clock3 size={34} className="mx-auto text-slate-400" />
            <h3 className="mt-4 font-semibold">No trip history connected</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              Completed trips will appear here once the backend provides a trip-history endpoint.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}
