
import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Bus,
  MapPin,
  Wallet,
  ArrowLeftRight,
  BellRing,
  QrCode,
  Menu,
  ChevronRight,
  X,
  LogOut,
  Home,
} from 'lucide-react'

const links = [
  {
    label: 'Destinations',
    path: '/conductor',
    icon: MapPin,
    end: true,
  },
  {
    label: 'Balances',
    path: '/conductor/balances',
    icon: Wallet,
  },
  {
    label: 'Destination Change Requests',
    path: '/conductor/requests',
    icon: ArrowLeftRight,
  },
  {
    label: 'Emergency Alerts',
    path: '/conductor/emergency-alerts',
    icon: BellRing,
  },
  {
    label: 'Generate QR Code',
    path: '/conductor/qr-code',
    icon: QrCode,
  },
]

export default function ConductorLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()

  function handleHome() {
    setSidebarOpen(false)
    navigate('/')
  }

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation overlay"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/50 md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-slate-950 text-white transition-transform md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 items-center gap-3 border-b border-white/10 px-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600">
            <Bus size={22} />
          </div>

          <div>
            <p className="text-lg font-bold">
              Smart <span className="text-emerald-400">Matatu</span>
            </p>
            <p className="text-xs text-slate-400">
              Conductor workspace
            </p>
          </div>

          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setSidebarOpen(false)}
            className="ml-auto rounded-lg p-1 hover:bg-white/10 md:hidden"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-3 pt-4">
          <button
            type="button"
            onClick={handleHome}
            className="flex w-full items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-600/15 px-3 py-3 text-sm font-semibold text-emerald-300 transition hover:bg-emerald-600 hover:text-white"
          >
            <Home size={19} />
            <span>Home</span>
          </button>
        </div>

        <nav className="space-y-1 px-3 pt-7">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
            My workspace
          </p>

          {links.map(({ label, path, icon: Icon, end }) => (
            <NavLink
              key={path}
              to={path}
              end={end}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                  isActive
                    ? 'bg-emerald-600 text-white'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon size={19} />
              <span className="flex-1">{label}</span>
              <ChevronRight size={15} className="opacity-50" />
            </NavLink>
          ))}
        </nav>

        <div className="px-3 pt-1">
          <button
            type="button"
            onClick={handleLogout}
            className="mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-red-500/10 hover:text-red-300"
          >
            <LogOut size={18} />
            Sign out
          </button>

          <p className="mt-3 text-center text-xs text-slate-500">
            Smart Matatu
          </p>
        </div>
      </aside>

      <div className="min-h-screen md:ml-64">
        <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Toggle navigation"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-lg p-2 transition hover:bg-slate-100 md:hidden"
            >
              <Menu size={22} />
            </button>

            <div>
              <p className="text-sm text-slate-500">Smart Matatu</p>
              <h1 className="text-lg font-bold">
                Conductor workspace
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 font-bold text-emerald-700">
              {(currentUser?.name || 'Conductor')
                .charAt(0)
                .toUpperCase()}
            </div>

            <div className="hidden sm:block">
              <p className="text-sm font-semibold">
                {currentUser?.name || 'Conductor'}
              </p>
              <p className="text-xs text-slate-500">
                {currentUser?.email || 'Conductor session'}
              </p>
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
