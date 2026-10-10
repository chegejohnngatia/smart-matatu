import { useLocation } from 'react-router-dom'
import { Construction, Search } from 'lucide-react'

const pageDetails = {
  '/admin/matatus': {
    title: 'Matatu Management',
    description: 'Manage vehicle registration, fleet details, and vehicle status.',
    resource: 'matatus',
  },
  '/admin/routes': {
    title: 'Route Management',
    description: 'Manage transport routes, stages, and route information.',
    resource: 'routes',
  },
  '/admin/users': {
    title: 'User Management',
    description: 'Review passenger, conductor, and administrator accounts.',
    resource: 'users',
  },
  '/admin/trips': {
    title: 'Trip Management',
    description: 'Monitor trips, assignments, and trip statuses.',
    resource: 'trips',
  },
  '/admin/requests': {
    title: 'Destination Requests',
    description: 'Review passenger destination requests and their statuses.',
    resource: 'destination requests',
  },
}

export default function ResourcePage() {
  const { pathname } = useLocation()
  const page = pageDetails[pathname] ?? {
    title: 'Management',
    description: 'Manage Smart Matatu platform records.',
    resource: 'records',
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-blue-600">
          Administration
        </p>
        <h2 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
          {page.title}
        </h2>
        <p className="mt-2 text-sm text-slate-500">{page.description}</p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <div className="flex flex-col items-center py-12 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-50 text-amber-600">
            <Construction size={27} />
          </div>

          <h3 className="mt-5 text-lg font-bold">Backend integration pending</h3>
          <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">
            The {page.resource} management page is ready for implementation.
            The next step is to connect it to the existing backend API before
            displaying or changing real records.
          </p>

          <div className="mt-6 flex items-center gap-2 rounded-xl bg-slate-50 px-4 py-3 text-left text-sm text-slate-600">
            <Search size={18} className="shrink-0 text-slate-400" />
            <span>No live records loaded. No database changes have been made.</span>
          </div>
        </div>
      </div>
    </div>
  )
}
