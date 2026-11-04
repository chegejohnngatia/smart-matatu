
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute({ allowedRoles, children }) {
  const { currentUser, authLoading } = useAuth()
  const location = useLocation()

  // Wait for Flask to restore and verify the session.
  if (authLoading) {
    return null
  }

  // Redirect unauthenticated users to login.
  if (!currentUser) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    )
  }

  // Prevent users from accessing pages outside their role.
  if (!allowedRoles.includes(currentUser.role)) {
   const home =
  currentUser.role === 'admin'
    ? '/admin/create-user'
    : currentUser.role === 'conductor'
      ? '/conductor'
      : '/'

    return <Navigate to={home} replace />
  }

  return children
}
