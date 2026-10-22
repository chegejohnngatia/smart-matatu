import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute({ allowedRoles, children }) {
  const { currentUser } = useAuth()
  const location = useLocation()

  if (!currentUser) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    )
  }

  if (!allowedRoles.includes(currentUser.role)) {
    const home =
      currentUser.role === 'admin'
        ? '/admin/dashboard'
        : currentUser.role === 'conductor'
          ? '/conductor'
          : '/'

    return <Navigate to={home} replace />
  }

  return children
}
