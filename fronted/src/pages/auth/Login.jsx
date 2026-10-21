import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, BusFront, ShieldCheck } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import './auth.css'

export default function Login() {
  const { currentUser, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')

  if (currentUser) {
    const home =
      currentUser.role === 'admin'
        ? '/admin/dashboard'
        : currentUser.role === 'conductor'
          ? '/conductor'
          : '/'

    return <Navigate to={home} replace />
  }

  function handleSubmit(event) {
    event.preventDefault()
    setError('')

    const result = login(email, password)

    if (!result.success) {
      setError(result.message)
      return
    }

    const destination = location.state?.from

    if (destination?.startsWith('/admin') && result.user.role !== 'admin') {
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

          <div className="auth-feature">
            <ShieldCheck size={21} />
            <span>Role-based access for authorized users</span>
          </div>
        </div>

        <p className="auth-footer">
          Smart Matatu · Development environment
        </p>
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
              placeholder="you@example.com"
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

            <button type="submit" className="auth-submit">
              Sign in
            </button>
          </form>

          <p className="auth-demo-note">
            Demo mode is active. Use the temporary test credentials
            provided in your development instructions.
          </p>
        </div>
      </section>
    </main>
  )
}
