
import { createContext, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null)

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null)
  const [csrfToken, setCsrfToken] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)

  // Restore the authenticated Flask session when React starts.
  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
          method: 'GET',
          credentials: 'include',
        })

        const data = await response.json()

        if (!response.ok) {
          if (!cancelled) {
            setCurrentUser(null)
            setCsrfToken(null)
          }
          return
        }

        if (!cancelled) {
          setCurrentUser({
            id: data.user.id,
            name: data.user.full_name,
            email: data.user.email,
            role: data.user.role,
            matatu: data.user.matatu || null,
          })
          setCsrfToken(data.csrf_token || null)
        }
      } catch (error) {
        console.error('Session restoration failed:', error)

        if (!cancelled) {
          setCurrentUser(null)
          setCsrfToken(null)
        }
      } finally {
        if (!cancelled) {
          setAuthLoading(false)
        }
      }
    }

    restoreSession()

    return () => {
      cancelled = true
    }
  }, [])

  // Authenticate using the Flask backend.
  async function login(email, password) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (!response.ok) {
        return {
          success: false,
          message: data.message || 'Login failed.',
        }
      }

      const sessionUser = {
        id: data.user.id,
        name: data.user.full_name,
        email: data.user.email,
        role: data.user.role,
        matatu: data.user.matatu || null,
      }

      setCurrentUser(sessionUser)
      setCsrfToken(data.csrf_token || null)

      return {
        success: true,
        user: sessionUser,
      }
    } catch (error) {
      console.error('Backend login failed:', error)

      return {
        success: false,
        message: 'Unable to connect to the server. Please try again.',
      }
    }
  }

  // End the authenticated Flask session.
  async function logout() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRF-Token': csrfToken || '',
        },
      })

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        console.error(
          'Backend logout failed:',
          data.message || response.status
        )
        return false
      }

      setCurrentUser(null)
      setCsrfToken(null)

      return true
    } catch (error) {
      console.error('Logout request failed:', error)
      return false
    }
  }

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        csrfToken,
        authLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}
