import { useEffect, useState } from 'react'
import { api, type UserDashboard, type UserSessionSummary } from '../api/client'
import { useAuth } from '../auth/context'
import { DashboardCard } from '../components/DashboardCard'
import { AppShell } from '../layouts/AppShell'

const number = (value: number) => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value)
const money = (value: string) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value))
const date = (value: string | null) => value ? new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
const duration = (seconds: number) => `${Math.floor(seconds / 3600)}h ${String(Math.floor(seconds % 3600 / 60)).padStart(2, '0')}min`
const statusLabel: Record<UserSessionSummary['status'], string> = { CREATED: 'Criada', CHARGING: 'Carregando', PAUSED: 'Pausada', COMPLETED: 'Concluída', CANCELLED: 'Cancelada' }

export function UserDashboardPage() {
  const { state, logout } = useAuth()
  const [data, setData] = useState<UserDashboard | null>(null)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let live = true
    api.userDashboard().then(result => { if (live) setData(result) }).catch(() => { if (live) setError(true) })
    return () => { live = false }
  }, [attempt])

  function reload() { setData(null); setError(false); setAttempt(value => value + 1) }
  const current = data?.current_session
  return <AppShell><div className="dashboard">
    <header className="dashboard-heading"><div><p className="eyebrow">Área do usuário</p><h1>Minha recarga</h1><p>Olá, {state.status === 'authenticated' ? state.user.name : ''}</p></div><div className="dashboard-actions"><button onClick={reload}>Atualizar</button><button onClick={logout}>Sair</button></div></header>
    {error ? <div className="dashboard-error" role="alert"><p>Não foi possível carregar o dashboard.</p><button onClick={reload}>Tentar novamente</button></div> : !data ? <p role="status">Carregando dashboard...</p> : <>
      <section className="chart-panel" aria-labelledby="current-session"><h2 id="current-session">Sessão atual</h2>{current ? <><p>{current.vehicle_name} · {current.charger_name} · {statusLabel[current.status]}</p><div className="kpi-grid"><DashboardCard label="Tempo real decorrido" value={duration(current.duration_seconds)} /><DashboardCard label="Potência atual" value={`${number(current.allocated_power_kw)} kW`} /><DashboardCard label="Energia consumida" value={`${number(current.energy_consumed_kwh)} kWh`} /><DashboardCard label="Participação solar" value={`${number(current.solar_percentage)}%`} /><DashboardCard label="Custo estimado" value={money(current.estimated_cost ?? '0')} detail="Estimativa com a tarifa capturada no início; o valor final será o da invoice." /></div></> : <p>Nenhuma recarga em andamento.</p>}</section>
      <section className="chart-panel"><h2>Histórico de sessões</h2>{data.session_history.length ? <div className="table-wrap"><table><thead><tr><th>Início</th><th>Veículo</th><th>Carregador</th><th>Status</th><th>Tempo real</th><th>Energia</th><th>Solar</th><th>Custo final</th></tr></thead><tbody>{data.session_history.map(session => <tr key={session.id}><td>{date(session.started_at)}</td><td>{session.vehicle_name}</td><td>{session.charger_name}</td><td>{statusLabel[session.status]}</td><td>{duration(session.duration_seconds)}</td><td>{number(session.energy_consumed_kwh)} kWh</td><td>{number(session.solar_percentage)}%</td><td>{session.invoice_total === null ? '—' : money(session.invoice_total)}</td></tr>)}</tbody></table></div> : <p>Nenhuma sessão anterior.</p>}</section>
      <section className="chart-panel"><h2>Invoices</h2>{data.invoices.length ? <div className="table-wrap"><table><thead><tr><th>Data</th><th>Sessão</th><th>Status</th><th>Energia</th><th>Valor final</th></tr></thead><tbody>{data.invoices.map(invoice => <tr key={invoice.id}><td>{date(invoice.closed_at ?? invoice.created_at)}</td><td>{invoice.session_id}</td><td>{invoice.status === 'CLOSED' ? 'Fechada' : invoice.status === 'OPEN' ? 'Aberta' : 'Cancelada'}</td><td>{number(Number(invoice.energy_kwh))} kWh</td><td>{invoice.status === 'CLOSED' ? money(invoice.total) : '—'}</td></tr>)}</tbody></table></div> : <p>Nenhuma invoice disponível.</p>}</section>
    </>}
  </div></AppShell>
}
