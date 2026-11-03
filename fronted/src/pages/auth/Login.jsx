
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, BusFront } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import './auth.css'

export default function Login() {
  const { currentUser, login, authLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Display a rotating dotted-circle while Flask session is being restored.
  if (authLoading) {
    return (
      <main className="auth-loading-screen">
        <div className="auth-loading-spinner" aria-label="Loading">
          {Array.from({ length: 12 }).map((_, index) => (
            <span
              key={index}
              style={{ '--dot-index': index }}
            />
          ))}
        </div>

        <style>{`
          .auth-loading-screen {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f8fafc;
          }

          .auth-loading-spinner {
            position: relative;
            width: 54px;
            height: 54px;
            animation: auth-spin 1.2s linear infinite;
          }

          .auth-loading-spinner span {
            position: absolute;
            top: 0;
            left: 50%;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #2563eb;
            transform: translateX(-50%) rotate(calc(var(--dot-index) * 30deg));
            transform-origin: 0 27px;
            opacity: calc(1 - var(--dot-index) * 0.065);
          }

          @keyframes auth-spin {
            to {
              transform: rotate(360deg);
            }
          }

          @media (prefers-reduced-motion: reduce) {
            .auth-loading-spinner {
              animation-duration: 3s;
            }
          }
        `}</style>
      </main>
    )
  }

  if (currentUser) {
    const home =
      currentUser.role === 'admin'
        ? '/admin/dashboard'
        : currentUser.role === 'conductor'
          ? '/conductor'
          : '/'

    return <Navigate to={home} replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const result = await login(email, password)

      if (!result.success) {
        setError(result.message)
        return
      }

      const destination = location.state?.from

      if (
        destination?.startsWith('/admin') &&
        result.user.role !== 'admin'
      ) {
        navigate('/conductor', { replace: true })
        return
      }

      if (
        destination?.startsWith('/conductor') &&
        result.user.role !== 'conductor'
      ) {
        navigate('/admin/dashboard', { replace: true })
        return
      }

      const home =
        result.user.role === 'admin'
          ? '/admin/dashboard'
          : result.user.role === 'conductor'
            ? '/conductor'
            : '/'

      navigate(home, { replace: true })
    } catch (error) {
      console.error('Login error:', error)
      setError('Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-brand-panel">
        <Link to="/" className="auth-brand">
          <span className="auth-brand-icon">
            <BusFront size={28} />
          </span>
          <span>Smart Matatu</span>
        </Link>

        <div className="auth-brand-content">
          <span className="auth-eyebrow">SMART TRANSIT MANAGEMENT</span>
          <h1>Every journey, managed smarter.</h1>
          <p>
            Manage your fleet, coordinate trips and help make public
            transport more efficient.
          </p>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-card">
          <Link to="/" className="auth-mobile-brand">
            <BusFront size={25} />
            Smart Matatu
          </Link>

          <span className="auth-eyebrow">WELCOME BACK</span>
          <h2>Sign in to your account</h2>
          <p className="auth-muted">
            Enter your account details to continue.
          </p>

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              placeholder="alex214@gmail.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />

            <label htmlFor="password">Password</label>
            <div className="auth-password-field">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />

              <button
                type="button"
                className="auth-password-toggle"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
              </button>
            </div>

            <button
              type="submit"
              className="auth-submit"
              disabled={submitting}
            >
              {submitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
