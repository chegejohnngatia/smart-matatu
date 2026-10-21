import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import '../auth/auth.css'

export default function CreateUser() {
  const { createUser } = useAuth()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('conductor')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [success, setSuccess] = useState(false)

  function handleSubmit(event) {
    event.preventDefault()
    setMessage('')
    setSuccess(false)

    if (password.length < 8) {
      setMessage('Use a password of at least 8 characters.')
      return
    }

    const result = createUser({ name, email, password, role })

    setMessage(result.message)
    setSuccess(result.success)

    if (result.success) {
      setName('')
      setEmail('')
      setPassword('')
      setRole('conductor')
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-form-panel auth-create-panel">
        <div className="auth-form-card">
          <span className="auth-eyebrow">ADMINISTRATION</span>
          <h2>Create a user account</h2>
          <p className="auth-muted">
            Create accounts for authorized conductors.
          </p>

          {message && (
            <div
              className={success ? 'auth-success' : 'auth-error'}
              role="status"
            >
              {message}
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            <label htmlFor="fullName">Full name</label>
            <input
              id="fullName"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Enter full name"
              autoComplete="name"
              required
            />

            <label htmlFor="newEmail">Email address</label>
            <input
              id="newEmail"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="user@example.com"
              autoComplete="email"
              required
            />

            <label htmlFor="newRole">Account role</label>
            <select
              id="newRole"
              value={role}
              onChange={(event) => setRole(event.target.value)}
              disabled
            >
              <option value="conductor">Conductor</option>
            </select>

            <label htmlFor="newPassword">Temporary password</label>
            <input
              id="newPassword"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              placeholder="At least 8 characters"
              required
            />

            <button type="submit" className="auth-submit">
              Create account
            </button>
          </form>

          <Link to="/admin/dashboard" className="auth-back-link">
            ← Return to administrator dashboard
          </Link>

          <p className="auth-demo-note">
            Temporary demo only. Accounts are stored in this browser's
            session storage and are not saved to the project database.
          </p>
        </div>
      </section>
    </main>
  )
}
