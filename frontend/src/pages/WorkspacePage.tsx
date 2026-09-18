import { useEffect, useState } from 'react'
import { api, ApiError, type ChargingSession, type Role } from '../api/client'
import { useAuth } from '../auth/context'
import { AppShell } from '../layouts/AppShell'

export function WorkspacePage({ role }: { role: Role }) {
  const { state, logout } = useAuth()
  const [sessions, setSessions] = useState<ChargingSession[] | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    api.sessions().then(items => { if (active) setSessions(items) }).catch(cause => {
      if (active) setError(cause instanceof ApiError && cause.status === 403 ? 'Acesso não permitido.' : 'Não foi possível carregar as sessões.')
    })
    return () => { active = false }
  }, [attempt])
  return <AppShell><section className="panel">
    <div className="panel__heading"><div><p className="eyebrow">{role === 'ADMIN' ? 'Administração' : 'Área do usuário'}</p><h1>Olá, {state.status === 'authenticated' ? state.user.name : ''}</h1></div><button onClick={logout}>Sair</button></div>
    <h2>Sessões de recarga</h2>
    {error ? <div role="alert"><p>{error}</p><button onClick={() => { setError(''); setSessions(null); setAttempt(value => value + 1) }}>Tentar novamente</button></div>
      : sessions === null ? <p role="status">Carregando sessões...</p>
        : sessions.length === 0 ? <p>Nenhuma sessão encontrada.</p>
          : <ul>{sessions.map(session => <li key={session.id}>{session.status} · {session.energy_consumed_kwh} kWh</li>)}</ul>}
  </section></AppShell>
}
