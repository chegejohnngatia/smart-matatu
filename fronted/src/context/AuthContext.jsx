import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

const DEMO_USERS = [
  {
    id: 'demo-admin',
    name: 'Demo Administrator',
    email: 'admin@smartmatatu.test',
    password: 'AdminDemo123!',
    role: 'admin',
  },
  {
    id: 'demo-conductor',
    name: 'Demo Conductor',
    email: 'conductor@smartmatatu.test',
    password: 'ConductorDemo123!',
    role: 'conductor',
  },
]

const USERS_KEY = 'smartMatatuDemoUsers'
const SESSION_KEY = 'smartMatatuDemoSession'

function getInitialUsers() {
  try {
    const stored = sessionStorage.getItem(USERS_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (Array.isArray(parsed)) return parsed
    }
  } catch {
    // Use demo accounts if browser storage is unavailable.
  }

  return DEMO_USERS
}

function getInitialSession() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY)) || null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [users, setUsers] = useState(getInitialUsers)
  const [currentUser, setCurrentUser] = useState(getInitialSession)

  function login(email, password) {
    const user = users.find(
      (item) =>
        item.email.toLowerCase() === email.trim().toLowerCase() &&
        item.password === password,
    )

    if (!user) {
      return { success: false, message: 'Invalid email or password.' }
    }

    const sessionUser = {
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
    }

    sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessionUser))
    setCurrentUser(sessionUser)

    return { success: true, user: sessionUser }
  }

  function logout() {
    sessionStorage.removeItem(SESSION_KEY)
    setCurrentUser(null)
  }

  function createUser({ name, email, password, role }) {
    if (!currentUser || currentUser.role !== 'admin') {
      return {
        success: false,
        message: 'Administrator access required.',
      }
    }

    if (role !== 'conductor') {
      return {
        success: false,
        message: 'Administrators can create conductor accounts only.',
      }
    }

    const normalizedEmail = email.trim().toLowerCase()

    if (
      users.some(
        (user) => user.email.trim().toLowerCase() === normalizedEmail,
      )
    ) {
      return {
        success: false,
        message: 'An account with this email already exists.',
      }
    }

    const updatedUsers = [
      ...users,
      {
        id: crypto.randomUUID(),
        name: name.trim(),
        email: email.trim(),
        password,
        role,
      },
    ]

    try {
      sessionStorage.setItem(USERS_KEY, JSON.stringify(updatedUsers))
    } catch {
      return {
        success: false,
        message: 'Could not save the demo account in this browser session.',
      }
    }

    setUsers(updatedUsers)

    return {
      success: true,
      message: 'Demo account created successfully.',
    }
  }

  return (
    <AuthContext.Provider
      value={{ currentUser, login, logout, createUser }}
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
