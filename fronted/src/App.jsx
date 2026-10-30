
import { Navigate, Route, Routes } from 'react-router-dom'

import Landing from './components/Landing'
import AdminLayout from './components/admin/AdminLayout'
import Dashboard from './pages/admin/Dashboard'
import ResourcePage from './pages/admin/ResourcePage'
import AdminDashboard from './components/AdminDashboard'

import ConductorEmergencyAlerts from './pages/conductor/ConductorEmergencyAlerts'
import ConductorLayout from './components/conductor/ConductorLayout'
import ConductorDashboard from './pages/conductor/ConductorDashboard'
import ConductorBalances from './pages/conductor/ConductorBalances'
import ConductorRequests from './pages/conductor/ConductorRequests'

import Passenger from './pages/Passenger'

import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Login from './pages/auth/Login'
import CreateUser from './pages/admin/CreateUser'

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
      {/* Public pages */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/home" element={<RoleHome />} />

      {/* Passenger pages */}
      <Route path="/passenger" element={<Passenger />} />
      <Route path="/passenger/:matatuId" element={<Passenger />} />

      {/* Admin workspace */}
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

      {/* Existing admin prototype */}
      <Route
        path="/admin-prototype"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />

      {/* Conductor workspace */}
      <Route
        path="/conductor"
        element={
          <ProtectedRoute allowedRoles={['conductor']}>
            <ConductorLayout />
          </ProtectedRoute>
        }
      >
        {/* Default section: passenger destinations */}
        <Route index element={<ConductorDashboard />} />

        {/* Balance records */}
        <Route path="balances" element={<ConductorBalances />} />

        {/* Destination-change requests */}
        <Route path="requests" element={<ConductorRequests />} />

        {/* Emergency alerts */}
        <Route
          path="emergency-alerts"
          element={<ConductorEmergencyAlerts />}
        />
      </Route>

      {/* Fallback */}
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
