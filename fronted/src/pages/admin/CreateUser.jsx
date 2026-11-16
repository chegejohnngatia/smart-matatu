
import { useEffect, useRef, useState } from 'react'

import { useAuth } from '../../context/AuthContext'
import '../auth/auth.css'

export default function CreateUser() {
  const { csrfToken } = useAuth()
  const formRef = useRef(null)

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [matatuId, setMatatuId] = useState('')
  const [passportPhoto, setPassportPhoto] = useState(null)

  const [matatus, setMatatus] = useState([])
  const [loadingMatatus, setLoadingMatatus] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const [message, setMessage] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadMatatus() {
      try {
        const response = await fetch('/api/admin/matatus/available', {
          method: 'GET',
          credentials: 'include',
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.message || 'Unable to load matatus.')
        }

        if (!cancelled) {
          setMatatus(data.matatus || [])
        }
      } catch (error) {
        if (!cancelled) {
          setMessage(error.message || 'Unable to load matatus.')
          setSuccess(false)
        }
      } finally {
        if (!cancelled) {
          setLoadingMatatus(false)
        }
      }
    }

    loadMatatus()

    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    setMessage('')
    setSuccess(false)

    if (!csrfToken) {
      setMessage('Your session has expired. Please log in again.')
      return
    }

    if (password.length < 8 || password.length > 128) {
      setMessage('Password must be between 8 and 128 characters.')
      return
    }

    if (!matatuId) {
      setMessage('Please select a matatu.')
      return
    }

    if (!passportPhoto) {
      setMessage('Please select a passport photograph.')
      return
    }

    const formData = new FormData()
    formData.append('full_name', name.trim())
    formData.append('email', email.trim())
    formData.append('password', password)
    formData.append('matatu_id', matatuId)
    formData.append('passport_photo', passportPhoto)

    setSubmitting(true)

    try {
      const response = await fetch('/api/admin/conductors', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRF-Token': csrfToken,
        },
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.message || 'Unable to create conductor account.')
      }

      setMessage(data.message || 'Conductor account created successfully.')
      setSuccess(true)

      setName('')
      setEmail('')
      setPassword('')
      setMatatuId('')
      setPassportPhoto(null)
      formRef.current?.reset()
    } catch (error) {
      setMessage(error.message || 'Unable to connect to the server.')
      setSuccess(false)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-form-panel auth-create-panel">
        <div className="auth-form-card">
          <span className="auth-eyebrow">ADMINISTRATION</span>
          <h2>Create a conductor account</h2>
          <p className="auth-muted">
            Register an authorized conductor and assign a matatu.
          </p>

          {message && (
            <div
              className={success ? 'auth-success' : 'auth-error'}
              role="status"
            >
              {message}
            </div>
          )}

          <form
            ref={formRef}
            onSubmit={handleSubmit}
            className="auth-form"
          >
            <label htmlFor="fullName">Full name</label>
            <input
              id="fullName"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Enter full name"
              autoComplete="name"
              minLength={3}
              maxLength={100}
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

            <label htmlFor="matatu">Assign matatu</label>
            <select
              id="matatu"
              value={matatuId}
              onChange={(event) => setMatatuId(event.target.value)}
              disabled={loadingMatatus || matatus.length === 0}
              required
            >
              <option value="">
                {loadingMatatus
                  ? 'Loading matatus...'
                  : matatus.length === 0
                    ? 'No matatus available'
                    : 'Select a matatu'}
              </option>

              {matatus.map((matatu) => (
                <option key={matatu.id} value={matatu.id}>
                  {matatu.registration_number} â€” {matatu.route_name}
                </option>
              ))}
            </select>

            <label htmlFor="newPassword">Temporary password</label>
            <input
              id="newPassword"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              placeholder="At least 8 characters"
              required
            />

            <label htmlFor="passportPhoto">Passport photograph</label>
            <input
              id="passportPhoto"
              type="file"
              accept="image/jpeg,image/png"
              onChange={(event) =>
                setPassportPhoto(event.target.files?.[0] || null)
              }
              required
            />

            <button
              type="submit"
              className="auth-submit"
              disabled={submitting || loadingMatatus || matatus.length === 0}
            >
              {submitting ? 'Creating account...' : 'Create account'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
