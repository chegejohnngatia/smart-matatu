
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Bus,
  Users,
  Map,
  Menu,
  Bell,
  ChevronRight,
  ChevronDown,
  UserPlus,
  LogOut,
  X,
  Home,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'

const navigation = [
  {
    label: 'Manage Conductor',
    icon: Users,
    id: 'conductor',
    children: [
      {
        label: 'Add Conductor',
        path: '/admin/create-user',
        icon: UserPlus,
      },
      {
        label: 'View Conductors',
        path: '/admin/users',
        icon: Users,
      },
    ],
  },
  {
    label: 'Manage Matatu',
    icon: Bus,
    id: 'matatu',
    children: [
      {
        label: 'View Matatus',
        path: '/admin/matatus',
        icon: Bus,
      },
    ],
  },
  {
    label: 'Manage Routes',
    icon: Map,
    id: 'routes',
    children: [
      {
        label: 'View Routes',
        path: '/admin/routes',
        icon: Map,
      },
    ],
  },
]

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [expandedSection, setExpandedSection] = useState(null)

  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const activeSection = navigation.find((section) =>
      section.children.some((child) =>
        location.pathname === child.path
      )
    )

    if (activeSection) {
      setExpandedSection(activeSection.id)
    }
  }, [location.pathname])

  function toggleSection(sectionId) {
    setExpandedSection((current) =>
      current === sectionId ? null : sectionId
    )
  }

  function handleHome() {
    setSidebarOpen(false)
    navigate('/')
  }

  async function handleLogout() {
    if (loggingOut) return

    setLoggingOut(true)

    try {
      const success = await logout()

      if (success) {
        navigate('/login', { replace: true })
      }
    } finally {
      setLoggingOut(false)
    }
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
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col overflow-y-auto bg-slate-950 text-white transition-transform duration-200 md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 shrink-0 items-center gap-3 border-b border-white/10 px-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600">
            <Bus size={23} />
          </div>

          <div>
            <p className="text-lg font-bold">
              Smart <span className="text-blue-400">Matatu</span>
            </p>
            <p className="text-xs text-slate-400">
              Management portal
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

        <div className="px-4 pt-4">
          <button
            type="button"
            onClick={handleHome}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
          >
            <Home size={19} />
            <span>Home</span>
          </button>
        </div>

        <div className="px-4 pt-4">
          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Workspace
          </p>

          <nav className="space-y-2">
            {navigation.map(({ id, label, icon: Icon, children }) => {
              const isExpanded = expandedSection === id
              const isActiveSection = children.some(
                (child) => location.pathname === child.path
              )

              return (
                <div key={id}>
                  <button
                    type="button"
                    onClick={() => toggleSection(id)}
                    aria-expanded={isExpanded}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                      isActiveSection
                        ? 'bg-blue-600/15 text-blue-300'
                        : 'text-slate-300 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    <Icon size={19} />
                    <span className="flex-1 text-left">{label}</span>

                    {isExpanded ? (
                      <ChevronDown size={17} />
                    ) : (
                      <ChevronRight size={17} />
                    )}
                  </button>

                  {isExpanded && (
                    <div className="ml-5 mt-1 space-y-1 border-l border-white/10 pl-3">
                      {children.map(
                        ({ label: childLabel, path, icon: ChildIcon }) => (
                          <NavLink
                            key={path}
                            to={path}
                            onClick={() => setSidebarOpen(false)}
                            className={({ isActive }) =>
                              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                                isActive
                                  ? 'bg-blue-600 text-white'
                                  : 'text-slate-400 hover:bg-white/10 hover:text-white'
                              }`
                            }
                          >
                            <ChildIcon size={17} />
                            <span>{childLabel}</span>
                          </NavLink>
                        )
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </nav>
        </div>

        <div className="mt-auto shrink-0 p-4">
          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            className="mt-4 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-300 hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LogOut size={18} />
            {loggingOut ? 'Signing out...' : 'Sign out'}
          </button>
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
              {currentUser?.name?.charAt(0)?.toUpperCase() || 'A'}
            </div>

            <div className="hidden sm:block">
              <p className="text-sm font-semibold">
                {currentUser?.name || 'Administrator'}
              </p>
              <p className="text-xs text-slate-500">
                {currentUser?.email || ''}
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
