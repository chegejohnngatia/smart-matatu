
import { Navigate, Route, Routes } from 'react-router-dom'

import Landing from './components/Landing'
import AdminLayout from './components/admin/AdminLayout'
import ResourcePage from './pages/admin/ResourcePage'
import ConductorManagement from './pages/admin/ConductorManagement'
import ConductorEmergencyAlerts from './pages/conductor/ConductorEmergencyAlerts'
import ConductorLayout from './components/conductor/ConductorLayout'
import ConductorDashboard from './pages/conductor/ConductorDashboard'
import ConductorBalances from './pages/conductor/ConductorBalances'
import ConductorRequests from './pages/conductor/ConductorRequests'
import ConductorQRCode from './pages/conductor/ConductorQRCode'

import Passenger from './pages/Passenger'

import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Login from './pages/auth/Login'
import CreateUser from './pages/admin/CreateUser'

function RoleHome() {
  const { currentUser } = useAuth()

  if (currentUser?.role === 'admin') {
    return <Navigate to="/admin/create-user" replace />
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
        <Route index element={<Navigate to="create-user" replace />} />
        <Route path="matatus" element={<ResourcePage />} />
        <Route path="routes" element={<ResourcePage />} />
        <Route path="users" element={<ConductorManagement />} />
        <Route path="create-user" element={<CreateUser />} />
      </Route>

      {/* Conductor workspace */}
      <Route
        path="/conductor"
        element={
          <ProtectedRoute allowedRoles={['conductor']}>
            <ConductorLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<ConductorDashboard />} />
        <Route path="balances" element={<ConductorBalances />} />
        <Route path="requests" element={<ConductorRequests />} />
        <Route
          path="emergency-alerts"
          element={<ConductorEmergencyAlerts />}
        />
        <Route path="qr-code" element={<ConductorQRCode />} />
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
