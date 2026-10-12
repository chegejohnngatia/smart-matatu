import { Navigate, Route, Routes } from 'react-router-dom'
import Landing from './components/Landing'
import AdminLayout from './components/admin/AdminLayout'
import Dashboard from './pages/admin/Dashboard'
import ResourcePage from './pages/admin/ResourcePage'
import Passenger from './pages/Passenger'

function RolePlaceholder({ role }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white">
      <section className="max-w-md text-center">
        <h1 className="text-3xl font-bold">{role} portal</h1>
        <p className="mt-3 text-slate-400">
          This section has not been implemented yet.
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

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />

      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="matatus" element={<ResourcePage />} />
        <Route path="routes" element={<ResourcePage />} />
        <Route path="users" element={<ResourcePage />} />
        <Route path="trips" element={<ResourcePage />} />
        <Route path="requests" element={<ResourcePage />} />
      </Route>

      <Route path="/passenger" element={<Passenger />} />
      <Route path="/conductor" element={<RolePlaceholder role="Conductor" />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}