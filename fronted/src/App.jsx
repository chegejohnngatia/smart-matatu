import { Navigate, Route, Routes, useParams } from 'react-router-dom'

import Landing from './components/Landing'
import AdminLayout from './components/admin/AdminLayout'
import Dashboard from './pages/admin/Dashboard'
import ResourcePage from './pages/admin/ResourcePage'
import AdminDashboard from './components/AdminDashboard'
import ConductorLayout from './components/conductor/ConductorLayout'
import ConductorDashboard from './pages/conductor/ConductorDashboard'
import ConductorSectionPage from './pages/conductor/ConductorSectionPage'

import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Login from './pages/auth/Login'
import CreateUser from './pages/admin/CreateUser'

function PassengerPage() {
  const { matatuId } = useParams()

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white">
      <section className="max-w-lg text-center">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-600">
          <span className="text-2xl" aria-hidden="true">🚌</span>
        </div>
        <h1 className="text-3xl font-bold">Smart Matatu Passenger Service</h1>
        <p className="mt-3 text-slate-300">
          Access passenger services without creating an account or signing in.
        </p>
        {matatuId && (
          <p className="mt-4 rounded-xl bg-slate-900 p-4 text-slate-200">
            Matatu reference: <strong>{matatuId}</strong>
          </p>
        )}
        <p className="mt-4 text-sm text-slate-400">
          Passenger tracking and destination requests will be connected when
          the passenger interface and backend are integrated.
        </p>
        <a
          href="/"
          className="mt-6 inline-block rounded-xl bg-blue-600 px-5 py-3 font-semibold hover:bg-blue-500"
        >
          Return to home
        </a>
      </section>
    </main>
  )
}

function RoleHome() {
  const { currentUser } = useAuth()

  if (currentUser?.role === 'admin') {
    return <Navigate to="/admin/dashboard" replace />
  }

  if (currentUser?.role === 'conductor') {
    return <Navigate to="/conductor" replace />
  }

  return <Navigate to="/login" replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/home" element={<RoleHome />} />

      {/* Public passenger routes: no authentication required. */}
      <Route path="/passenger" element={<PassengerPage />} />
      <Route path="/passenger/:matatuId" element={<PassengerPage />} />

      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="matatus" element={<ResourcePage />} />
        <Route path="routes" element={<ResourcePage />} />
        <Route path="users" element={<ResourcePage />} />
        <Route path="create-user" element={<CreateUser />} />
        <Route path="trips" element={<ResourcePage />} />
        <Route path="requests" element={<ResourcePage />} />
      </Route>

      <Route
        path="/admin-prototype"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/conductor"
        element={
          <ProtectedRoute allowedRoles={['conductor']}>
            <ConductorLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<ConductorDashboard />} />
        <Route path="trip" element={<ConductorSectionPage />} />
        <Route path="requests" element={<ConductorSectionPage />} />
        <Route path="history" element={<ConductorSectionPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
