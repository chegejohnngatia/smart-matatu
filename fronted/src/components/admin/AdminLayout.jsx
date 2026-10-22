import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Bus,
  LayoutDashboard,
  Map,
  Users,
  Route,
  ClipboardList,
  Menu,
  Bell,
  ShieldCheck,
  ChevronRight,
  UserPlus,
  LogOut,
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'

const navigation = [
  { label: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Matatus', path: '/admin/matatus', icon: Bus },
  { label: 'Routes', path: '/admin/routes', icon: Map },
  { label: 'Users', path: '/admin/users', icon: Users },
  { label: 'Create User', path: '/admin/create-user', icon: UserPlus },
  { label: 'Trips', path: '/admin/trips', icon: Route },
  { label: 'Requests', path: '/admin/requests', icon: ClipboardList },
]

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/50 md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-950 text-white transition-transform duration-200 md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 items-center gap-3 border-b border-white/10 px-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600">
            <Bus size={23} />
          </div>
          <div>
            <p className="text-lg font-bold">
              Matatu <span className="text-blue-400">Smart</span>
            </p>
            <p className="text-xs text-slate-400">Management portal</p>
          </div>
        </div>

        <div className="px-4 pt-7">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Workspace
          </p>

          <nav className="space-y-1">
            {navigation.map(({ label, path, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-950/30'
                      : 'text-slate-300 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <Icon size={19} />
                <span>{label}</span>
                <ChevronRight size={15} className="ml-auto opacity-50" />
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="mt-auto p-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck size={18} className="text-emerald-400" />
              Admin access
            </div>
            <p className="text-xs leading-5 text-slate-400">
              Administrative controls for the Smart Matatu platform.
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-4 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-300 hover:bg-red-500/10 hover:text-red-300"
          >
            <LogOut size={18} />
            Sign out
          </button>
          <p className="mt-4 text-center text-xs text-slate-500">
            Smart Matatu · Development
          </p>
        </div>
      </aside>

      <div className="min-h-screen md:ml-64">
        <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Toggle navigation"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-lg p-2 hover:bg-slate-100 md:hidden"
            >
              <Menu size={22} />
            </button>
            <div>
              <p className="text-sm text-slate-500">Smart Matatu</p>
              <h1 className="text-lg font-bold">Admin workspace</h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Notifications"
              className="relative rounded-xl border border-slate-200 p-2.5 text-slate-600 hover:bg-slate-50"
            >
              <Bell size={19} />
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-blue-600" />
            </button>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 font-bold text-blue-700">
              A
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-semibold">{currentUser?.name || "Administrator"}</p>
              <p className="text-xs text-slate-500">{currentUser?.email || "Demo session"}</p>
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
