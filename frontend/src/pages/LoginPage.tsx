import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/context'
import { AppShell } from '../layouts/AppShell'

export function LoginPage() {
  const { state, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  if (state.status === 'authenticated') return <Navigate to={state.user.role === 'ADMIN' ? '/admin' : '/user'} replace />
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await login(email, password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from?.startsWith('/') && !from.startsWith('//') ? from : '/', { replace: true })
    } catch (cause) {
      setError(cause instanceof ApiError && cause.status === 401 ? 'E-mail ou senha inválidos.' : 'Não foi possível entrar. Tente novamente.')
    } finally { setBusy(false) }
  }
  return <AppShell><section className="panel"><h1>Entrar</h1><form onSubmit={submit}>
    <label>E-mail<input type="email" value={email} onChange={event => setEmail(event.target.value)} required autoComplete="username" /></label>
    <label>Senha<input type="password" value={password} onChange={event => setPassword(event.target.value)} required autoComplete="current-password" /></label>
    {error && <p role="alert">{error}</p>}
    <button disabled={busy} type="submit">{busy ? 'Entrando...' : 'Entrar'}</button>
  </form></section></AppShell>
}
