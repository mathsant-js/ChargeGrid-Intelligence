import { useEffect, useRef, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, ApiError, type Alert, type Charger, type ChargingSession, type Dashboard, type DemandPrediction, type EnergyReading, type Invoice, type SolarReading, type Station, type Sustainability } from '../api/client'
import { useAuth } from '../auth/context'
import { DashboardCard } from '../components/DashboardCard'
import { AppShell } from '../layouts/AppShell'
import { aggregateEnergyHistory } from './energyHistory'

type PredictionState = 'valid' | 'expired' | 'missing' | 'insufficient' | 'model-unavailable' | 'communication-error' | 'select-station'
type Data = { stations: Station[]; chargers: Charger[]; sessions: ChargingSession[]; invoices: Invoice[]; readings: EnergyReading[]; currentReadings: EnergyReading[]; solar: SolarReading[]; summary: Dashboard; sustainability: Sustainability; alerts: Alert[]; prediction: DemandPrediction | null; predictionState: PredictionState }
const number = (value: number) => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value)
const money = (value: string) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value))
const time = (value: string) => new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
const active = (session: ChargingSession) => session.status === 'CHARGING' || session.status === 'PAUSED'
const validPrediction = (prediction: DemandPrediction, stationId: string) => prediction.station_id === stationId && Number.isFinite(prediction.predicted_demand_kw) && prediction.predicted_demand_kw >= 0 && Number.isFinite(prediction.capacity_kw) && prediction.capacity_kw > 0 && ['LOW', 'MEDIUM', 'HIGH'].includes(prediction.risk_level)
const risk = { LOW: { label: 'Baixo', symbol: '●' }, MEDIUM: { label: 'Médio', symbol: '▲' }, HIGH: { label: 'Alto', symbol: '!' } } as const

export function AdminDashboardPage() {
  const { state, logout } = useAuth()
  const [stationId, setStationId] = useState('')
  const [period, setPeriod] = useState('all')
  const [attempt, setAttempt] = useState(0)
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [pendingAlert, setPendingAlert] = useState<string | null>(null)
  const [runningPrediction, setRunningPrediction] = useState(false)
  const stationIdRef = useRef(stationId)
  stationIdRef.current = stationId

  useEffect(() => {
    let live = true
    const from = period === '24h' ? new Date(Date.now() - 86400000).toISOString() : period === '7d' ? new Date(Date.now() - 7 * 86400000).toISOString() : undefined
    const filters = { station_id: stationId || undefined, from }
    const readingsPromise = api.energyHistory(filters)
    Promise.all([api.stations(), api.chargers(), api.sessions(), api.invoices({ status: 'CLOSED' }), readingsPromise, from ? api.energyHistory({ station_id: stationId || undefined }) : readingsPromise, api.solarHistory({ station_id: stationId || undefined }), api.dashboard(filters), api.sustainability(filters), api.alerts(stationId || undefined)]).then(async ([stations, chargers, sessions, invoices, readings, currentReadings, solar, summary, sustainability, alerts]) => {
      const predictionStation = stationId || (stations.length === 1 ? stations[0].id : '')
      let prediction: DemandPrediction | null = null
      let predictionState: PredictionState = predictionStation ? 'missing' : 'select-station'
      if (predictionStation) {
        try {
          const received = await api.prediction(predictionStation)
          if (validPrediction(received, predictionStation)) {
            prediction = received
            predictionState = Date.parse(received.prediction_for) > Date.now() ? 'valid' : 'expired'
          }
        } catch (cause) { if (!(cause instanceof ApiError && cause.status === 404)) predictionState = 'communication-error' }
      }
      if (live) setData({ stations, chargers, sessions, invoices, readings, currentReadings, solar, summary, sustainability, alerts, prediction, predictionState })
    }).catch(() => { if (live) setError('Não foi possível carregar o dashboard.') })
    return () => { live = false }
  }, [stationId, period, attempt])

  async function acknowledge(id: string) {
    setPendingAlert(id)
    setActionError('')
    try {
      const updated = await api.acknowledgeAlert(id)
      setData(previous => previous && { ...previous, alerts: previous.alerts.map(alert => alert.id === id ? updated : alert) })
    } catch { setActionError('Não foi possível reconhecer o alerta. Tente novamente.') }
    finally { setPendingAlert(null) }
  }

  async function runPrediction() {
    if (!data) return
    const selectedStation = stationId || (data.stations.length === 1 ? data.stations[0].id : '')
    if (!selectedStation) return
    setRunningPrediction(true)
    try {
      const prediction = await api.runPrediction(selectedStation)
      if (stationIdRef.current !== stationId) return
      if (validPrediction(prediction, selectedStation)) setData(previous => previous && { ...previous, prediction, predictionState: Date.parse(prediction.prediction_for) > Date.now() ? 'valid' : 'expired' })
      else setData(previous => previous && { ...previous, prediction: null, predictionState: 'missing' })
    } catch (cause) {
      if (stationIdRef.current !== stationId) return
      const predictionState: PredictionState = cause instanceof ApiError && cause.status === 422 ? 'insufficient' : cause instanceof ApiError && cause.status === 503 ? 'model-unavailable' : 'communication-error'
      setData(previous => previous && { ...previous, prediction: null, predictionState })
    } finally { setRunningPrediction(false) }
  }

  const chargerMap = new Map(data?.chargers.map(charger => [charger.id, charger]) ?? [])
  const shownSessions = data?.sessions.filter(session => !stationId || chargerMap.get(session.charger_id)?.station_id === stationId) ?? []
  const currentSessions = shownSessions.filter(active)
  const activeIds = new Set(currentSessions.map(session => session.id))
  const latest = new Map<string, EnergyReading>()
  for (const reading of data?.currentReadings ?? []) if (activeIds.has(reading.session_id) && (!latest.has(reading.session_id) || Date.parse(reading.timestamp) > Date.parse(latest.get(reading.session_id)!.timestamp))) latest.set(reading.session_id, reading)
  const demand = currentSessions.reduce((total, session) => total + session.allocated_power_kw, 0)
  const grid = [...latest.values()].reduce((total, reading) => total + reading.grid_power_kw, 0)
  const solarUse = [...latest.values()].reduce((total, reading) => total + reading.solar_power_kw, 0)
  const limit = data?.stations.filter(station => !stationId || station.id === stationId).reduce((total, station) => total + station.grid_limit_kw, 0) ?? 0
  const currentSolar = new Map<string, SolarReading>()
  for (const reading of data?.solar ?? []) if (!currentSolar.has(reading.station_id) || Date.parse(reading.timestamp) > Date.parse(currentSolar.get(reading.station_id)!.timestamp)) currentSolar.set(reading.station_id, reading)
  const solarAvailable = [...currentSolar.values()].reduce((total, reading) => total + reading.available_power_kw, 0)
  const predictionStation = stationId || (data?.stations.length === 1 ? data.stations[0].id : '')
  const prediction = data?.prediction && validPrediction(data.prediction, predictionStation) ? data.prediction : null
  const predictionMessages: Record<Exclude<PredictionState, 'valid'>, string> = {
    expired: 'A previsão desta estação expirou. Gere uma nova previsão para consultar o próximo horário-alvo.',
    missing: 'Ainda não há previsão para esta estação.',
    insufficient: 'Dados insuficientes para gerar uma previsão desta estação.',
    'model-unavailable': 'Modelo de previsão indisponível no momento.',
    'communication-error': 'Não foi possível comunicar com o serviço de previsão.',
    'select-station': 'Selecione uma estação para consultar a previsão de demanda.',
  }
  const history = aggregateEnergyHistory(data?.readings ?? []).map(point => ({ ...point, label: time(point.timestamp) }))
  const periodStart = period === '24h' ? Date.now() - 86400000 : period === '7d' ? Date.now() - 7 * 86400000 : 0
  const shownSessionIds = new Set(shownSessions.map(session => session.id))
  const invoiceHistory = (data?.invoices ?? []).filter(invoice => shownSessionIds.has(invoice.session_id) && invoice.closed_at && Date.parse(invoice.closed_at) >= periodStart).map(invoice => ({ label: invoice.closed_at ? time(invoice.closed_at) : '—', total: Number(invoice.total) }))

  return <AppShell><div className="dashboard">
    <header className="dashboard-heading"><div><p className="eyebrow">Administração</p><h1>Dashboard do gestor</h1><p>Olá, {state.status === 'authenticated' ? state.user.name : ''}</p></div><button onClick={logout}>Sair</button></header>
    <div className="dashboard-filters"><label>Estação <select value={stationId} onChange={event => { setData(null); setError(''); setStationId(event.target.value) }}><option value="">Todas as estações</option>{data?.stations.map(station => <option key={station.id} value={station.id}>{station.name}</option>)}</select></label><label>Período <select value={period} onChange={event => { setData(null); setError(''); setPeriod(event.target.value) }}><option value="all">Todo o histórico</option><option value="24h">Últimas 24 horas</option><option value="7d">Últimos 7 dias</option></select></label><button onClick={() => { setData(null); setError(''); setAttempt(value => value + 1) }}>Atualizar</button></div>
    {error ? <div role="alert" className="dashboard-error"><p>{error}</p><button onClick={() => { setError(''); setAttempt(value => value + 1) }}>Tentar novamente</button></div> : !data ? <p role="status">Carregando dashboard...</p> : <>
      <section className="kpi-grid" aria-label="Indicadores"><DashboardCard label="Demanda atual" value={`${number(demand)} kW`} /><DashboardCard label="Limite da rede" value={`${number(limit)} kW`} /><DashboardCard label="Capacidade disponível" value={`${number(Math.max(0, limit - grid))} kW`} /><DashboardCard label="Solar disponível" value={`${number(solarAvailable)} kW`} /><DashboardCard label="Solar em uso" value={`${number(solarUse)} kW`} /><DashboardCard label="Rede em uso" value={`${number(grid)} kW`} /><DashboardCard label="Carregadores ativos" value={new Set(currentSessions.map(session => session.charger_id)).size} /><DashboardCard label="Sessões ativas" value={currentSessions.length} /><DashboardCard label="Faturamento" value={money(data.summary.billed_total)} /><DashboardCard label="Energia consumida" value={`${number(data.summary.energy_consumed_kwh)} kWh`} /><DashboardCard label="Energia renovável" value={`${number(data.sustainability.solar_energy_kwh)} kWh`} /><DashboardCard label="CO₂ evitado" value={`${number(data.sustainability.avoided_co2_kg)} kg`} /></section>
      <section className="prediction-panel" aria-labelledby="prediction-title">
        <div className="prediction-panel__heading"><div><p className="eyebrow">Previsão consultiva</p><h2 id="prediction-title">Demanda prevista</h2></div>{predictionStation && <button disabled={runningPrediction} onClick={runPrediction}>{runningPrediction ? 'Gerando...' : 'Gerar nova previsão'}</button>}</div>
        {data.predictionState === 'valid' && prediction ? <div className="prediction-grid"><div><span>Demanda</span><strong>{number(prediction.predicted_demand_kw)} kW</strong></div><div><span>Risco de pico</span><strong className={`risk-badge risk-badge--${prediction.risk_level.toLowerCase()}`} aria-label={`Risco ${risk[prediction.risk_level].label}`}><span aria-hidden="true">{risk[prediction.risk_level].symbol}</span> {risk[prediction.risk_level].label}</strong></div><div><span>Horário-alvo</span><strong>{time(prediction.prediction_for)}</strong></div><div><span>Versão do modelo</span><strong>{prediction.model_version}</strong></div><div className="prediction-recommendation"><span>Recomendação</span><strong>{prediction.recommendation}</strong></div></div> : <p className="empty-note" role="status">{predictionMessages[data.predictionState as Exclude<PredictionState, 'valid'>]}</p>}
        <p className="advisory-note">A previsão apoia decisões operacionais e não executa controle energético.</p>
      </section>
      <div className="chart-grid"><section className="chart-panel"><h2>Demanda ao longo do tempo</h2>{history.length ? <ResponsiveContainer width="100%" height={250}><AreaChart data={history}><CartesianGrid stroke="#315443" /><XAxis dataKey="label" hide /><YAxis /><Tooltip /><Area dataKey="demand" name="Demanda (kW)" stroke="#43e7a3" fill="#225b43" /></AreaChart></ResponsiveContainer> : <p>Sem histórico de demanda no período.</p>}</section><section className="chart-panel"><h2>Solar vs rede</h2>{history.length ? <ResponsiveContainer width="100%" height={250}><AreaChart data={history}><CartesianGrid stroke="#315443" /><XAxis dataKey="label" hide /><YAxis /><Tooltip /><Legend /><Area dataKey="solar" name="Solar (kW)" stackId="1" stroke="#f4c95d" fill="#a68124" /><Area dataKey="grid" name="Rede (kW)" stackId="1" stroke="#68b8e9" fill="#285b80" /></AreaChart></ResponsiveContainer> : <p>Sem dados de energia no período.</p>}</section><section className="chart-panel"><h2>Sessões</h2><p>{data.summary.session_count} iniciadas · {data.summary.completed_session_count} concluídas no período</p><ul className="session-list">{shownSessions.slice(-8).reverse().map(session => <li key={session.id}><span>{session.status}</span><span>{number(session.energy_consumed_kwh)} kWh</span></li>)}</ul>{!shownSessions.length && <p>Nenhuma sessão encontrada.</p>}</section><section className="chart-panel"><h2>Faturamento</h2>{invoiceHistory.length ? <ResponsiveContainer width="100%" height={250}><BarChart data={invoiceHistory}><CartesianGrid stroke="#315443" /><XAxis dataKey="label" hide /><YAxis /><Tooltip formatter={value => money(String(value))} /><Bar dataKey="total" name="Valor (R$)" fill="#43e7a3" /></BarChart></ResponsiveContainer> : <p>Sem faturamento no período.</p>}</section></div>
      <section className="chart-panel"><h2>Histórico recente</h2>{history.length ? <div className="table-wrap"><table><thead><tr><th>Data</th><th>Demanda</th><th>Solar</th><th>Rede</th></tr></thead><tbody>{(data.readings ?? []).slice(-10).reverse().map(reading => <tr key={reading.id}><td>{time(reading.timestamp)}</td><td>{number(reading.allocated_power_kw)} kW</td><td>{number(reading.solar_power_kw)} kW</td><td>{number(reading.grid_power_kw)} kW</td></tr>)}</tbody></table></div> : <p>Nenhum registro no período.</p>}</section>
      <section className="chart-panel"><h2>Alertas recentes</h2>{actionError && <p role="alert">{actionError}</p>}{data.alerts.length ? <ul className="alert-list">{data.alerts.slice(0, 10).map(alert => <li key={alert.id}><div><strong>{alert.title}</strong><p>{alert.message}</p><small>{time(alert.created_at)} · {alert.severity}</small></div>{alert.acknowledged_at ? <span>Reconhecido</span> : <button disabled={pendingAlert === alert.id} onClick={() => acknowledge(alert.id)}>Reconhecer</button>}</li>)}</ul> : <p>Nenhum alerta recente.</p>}</section>
    </>}
  </div></AppShell>
}
