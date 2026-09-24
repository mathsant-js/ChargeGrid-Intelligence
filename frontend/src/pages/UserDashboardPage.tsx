import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { ApiError, api, type Charger, type Station, type UserDashboard, type UserSessionSummary, type Vehicle, type VehicleInput } from '../api/client'
import { useAuth } from '../auth/context'
import { DashboardCard } from '../components/DashboardCard'
import { AppShell } from '../layouts/AppShell'

const number = (value: number) => new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value)
const money = (value: string) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value))
const date = (value: string | null) => value ? new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
const duration = (seconds: number) => `${Math.floor(seconds / 3600)}h ${String(Math.floor(seconds % 3600 / 60)).padStart(2, '0')}min`
const statusLabel: Record<UserSessionSummary['status'], string> = { CREATED: 'Criada', CHARGING: 'Carregando', PAUSED: 'Pausada', COMPLETED: 'Concluída', CANCELLED: 'Cancelada' }
const emptyVehicle: VehicleInput = { name: '', brand: '', model: '', license_plate: '', max_charge_power_kw: 0 }

function errorMessage(error: unknown) {
  if (!(error instanceof ApiError)) return 'Não foi possível concluir a operação. Tente novamente.'
  const messages: Record<number, string> = {
    0: 'Não foi possível conectar à API.',
    401: 'Sua sessão expirou. Entre novamente.',
    403: 'Você não tem permissão para realizar esta operação.',
    404: 'O recurso selecionado não foi encontrado. Atualize os dados e tente novamente.',
    409: 'A operação entra em conflito com o estado atual. O veículo ou carregador pode já estar em uso.',
    422: 'Revise os campos informados e tente novamente.',
  }
  return messages[error.status] ?? error.message
}

export function UserDashboardPage() {
  const { state, logout } = useAuth()
  const [data, setData] = useState<UserDashboard | null>(null)
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [stations, setStations] = useState<Station[]>([])
  const [chargers, setChargers] = useState<Charger[]>([])
  const [error, setError] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [editing, setEditing] = useState<string | null>(null)
  const [vehicleForm, setVehicleForm] = useState<VehicleInput>(emptyVehicle)
  const [selectedVehicle, setSelectedVehicle] = useState('')
  const [selectedStation, setSelectedStation] = useState('')
  const [selectedCharger, setSelectedCharger] = useState('')
  const [confirmStop, setConfirmStop] = useState(false)

  const load = useCallback(async () => {
    setError(false)
    try {
      const [dashboard, ownVehicles, allStations, allChargers] = await Promise.all([api.userDashboard(), api.vehicles(), api.stations(), api.chargers()])
      setData(dashboard); setVehicles(ownVehicles); setStations(allStations); setChargers(allChargers)
      setSelectedVehicle(value => ownVehicles.some(item => item.id === value) ? value : ownVehicles[0]?.id ?? '')
      setSelectedStation(value => allStations.some(item => item.id === value && item.is_active) ? value : allStations.find(item => item.is_active)?.id ?? '')
    } catch { setError(true) }
  }, [])

  useEffect(() => { void load() }, [load])

  const availableChargers = useMemo(() => chargers.filter(charger => charger.station_id === selectedStation && charger.is_active && charger.status === 'AVAILABLE'), [chargers, selectedStation])
  useEffect(() => { setSelectedCharger(value => availableChargers.some(item => item.id === value) ? value : availableChargers[0]?.id ?? '') }, [availableChargers])

  async function run(key: string, action: () => Promise<unknown>, success: string) {
    if (busy) return false
    setBusy(key); setNotice(null)
    try { await action(); setNotice({ kind: 'success', text: success }); await load(); return true }
    catch (cause) { setNotice({ kind: 'error', text: errorMessage(cause) }); return false }
    finally { setBusy(null) }
  }

  function submitVehicle(event: FormEvent) {
    event.preventDefault()
    const action = editing ? api.updateVehicle(editing, vehicleForm) : api.createVehicle(vehicleForm)
    void run('vehicle', () => action, editing ? 'Veículo atualizado com sucesso.' : 'Veículo cadastrado com sucesso.').then(success => {
      if (success) { setEditing(null); setVehicleForm(emptyVehicle) }
    })
  }

  function editVehicle(vehicle: Vehicle) {
    setEditing(vehicle.id)
    setVehicleForm({ name: vehicle.name, brand: vehicle.brand, model: vehicle.model, license_plate: vehicle.license_plate, max_charge_power_kw: vehicle.max_charge_power_kw })
  }

  function reload() { setData(null); setNotice(null); void load() }

  const current = data?.current_session
  return <AppShell><div className="dashboard">
    <header className="dashboard-heading"><div><p className="eyebrow">Área do usuário</p><h1>Minha recarga</h1><p>Olá, {state.status === 'authenticated' ? state.user.name : ''}</p></div><div className="dashboard-actions"><button onClick={reload}>Atualizar</button><button onClick={logout}>Sair</button></div></header>
    {notice && <p className={`operation-notice operation-notice--${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.text}</p>}
    {error ? <div className="dashboard-error" role="alert"><p>Não foi possível carregar os dados operacionais.</p><button onClick={reload}>Tentar novamente</button></div> : !data ? <p role="status">Carregando dashboard...</p> : <>
      <section className="chart-panel" aria-labelledby="vehicles-title"><div className="section-heading"><div><p className="eyebrow">Garagem</p><h2 id="vehicles-title">Meus veículos</h2></div></div>
        {vehicles.length ? <ul className="vehicle-list">{vehicles.map(vehicle => <li key={vehicle.id}><div><strong>{vehicle.name}</strong><span>{vehicle.brand} {vehicle.model} · {vehicle.license_plate} · {number(vehicle.max_charge_power_kw)} kW</span></div><div className="row-actions"><button type="button" onClick={() => editVehicle(vehicle)} disabled={Boolean(busy)}>Editar</button><button type="button" className="danger-button" onClick={() => void run(`delete-${vehicle.id}`, () => api.deleteVehicle(vehicle.id), 'Veículo excluído com sucesso.')} disabled={Boolean(busy)}>Excluir</button></div></li>)}</ul> : <p>Nenhum veículo cadastrado.</p>}
        <form className="vehicle-form" onSubmit={submitVehicle} aria-label={editing ? 'Editar veículo' : 'Cadastrar veículo'}><h3>{editing ? 'Editar veículo' : 'Cadastrar veículo'}</h3><div className="form-grid">
          <label>Nome<input required maxLength={120} value={vehicleForm.name} onChange={e => setVehicleForm({ ...vehicleForm, name: e.target.value })} /></label>
          <label>Marca<input required maxLength={120} value={vehicleForm.brand} onChange={e => setVehicleForm({ ...vehicleForm, brand: e.target.value })} /></label>
          <label>Modelo<input required maxLength={120} value={vehicleForm.model} onChange={e => setVehicleForm({ ...vehicleForm, model: e.target.value })} /></label>
          <label>Placa<input required maxLength={20} value={vehicleForm.license_plate} onChange={e => setVehicleForm({ ...vehicleForm, license_plate: e.target.value })} /></label>
          <label>Potência máxima de recarga (kW)<input required type="number" min="0.1" step="0.1" value={vehicleForm.max_charge_power_kw || ''} onChange={e => setVehicleForm({ ...vehicleForm, max_charge_power_kw: Number(e.target.value) })} /></label>
        </div><div className="row-actions"><button disabled={Boolean(busy)}>{busy === 'vehicle' ? 'Salvando...' : editing ? 'Salvar alterações' : 'Cadastrar veículo'}</button>{editing && <button type="button" className="secondary-button" onClick={() => { setEditing(null); setVehicleForm(emptyVehicle) }}>Cancelar edição</button>}</div></form>
      </section>
      <section className="chart-panel" aria-labelledby="start-title"><p className="eyebrow">Operação</p><h2 id="start-title">Iniciar recarga</h2>{current ? <p>Encerre a sessão atual antes de iniciar outra.</p> : <form className="session-form" onSubmit={event => { event.preventDefault(); void run('start', () => api.startSession(selectedVehicle, selectedCharger), 'Sessão iniciada com sucesso.') }}>
        <label>Veículo<select aria-label="Veículo" required value={selectedVehicle} onChange={e => setSelectedVehicle(e.target.value)}><option value="">Selecione</option>{vehicles.map(vehicle => <option key={vehicle.id} value={vehicle.id}>{vehicle.name} · {vehicle.license_plate}</option>)}</select></label>
        <label>Estação<select aria-label="Estação" required value={selectedStation} onChange={e => setSelectedStation(e.target.value)}><option value="">Selecione</option>{stations.filter(station => station.is_active).map(station => <option key={station.id} value={station.id}>{station.name}</option>)}</select></label>
        <label>Carregador disponível<select aria-label="Carregador disponível" required value={selectedCharger} onChange={e => setSelectedCharger(e.target.value)}><option value="">Selecione</option>{availableChargers.map(charger => <option key={charger.id} value={charger.id}>{charger.name} · {number(charger.max_power_kw)} kW</option>)}</select>{selectedStation && !availableChargers.length && <span className="field-help">Nenhum carregador disponível nesta estação.</span>}</label>
        <button disabled={Boolean(busy) || !selectedVehicle || !selectedCharger}>{busy === 'start' ? 'Iniciando...' : 'Iniciar sessão'}</button>
      </form>}</section>
      <section className="chart-panel" aria-labelledby="current-session"><h2 id="current-session">Sessão atual</h2>{current ? <><p>{current.vehicle_name} · {current.charger_name} · {statusLabel[current.status]}</p><div className="kpi-grid"><DashboardCard label="Tempo real decorrido" value={duration(current.duration_seconds)} /><DashboardCard label="Potência atual" value={`${number(current.allocated_power_kw)} kW`} /><DashboardCard label="Energia consumida" value={`${number(current.energy_consumed_kwh)} kWh`} /><DashboardCard label="Participação solar" value={`${number(current.solar_percentage)}%`} /><DashboardCard label="Custo estimado" value={money(current.estimated_cost ?? '0')} detail="Estimativa com a tarifa capturada no início; o valor final será o da invoice." /></div></> : <p>Nenhuma recarga em andamento.</p>}</section>
      {current && <section className="chart-panel stop-panel" aria-labelledby="stop-title"><h2 id="stop-title">Encerrar recarga</h2>{confirmStop ? <div role="alertdialog" aria-labelledby="stop-confirm-title"><p id="stop-confirm-title">Confirma o encerramento da sessão atual?</p><div className="row-actions"><button className="danger-button" disabled={Boolean(busy)} onClick={() => void run('stop', () => api.stopSession(current.id), 'Sessão encerrada e dashboard atualizado.').then(() => setConfirmStop(false))}>{busy === 'stop' ? 'Encerrando...' : 'Sim, encerrar sessão'}</button><button className="secondary-button" disabled={Boolean(busy)} onClick={() => setConfirmStop(false)}>Cancelar</button></div></div> : <button className="danger-button" onClick={() => setConfirmStop(true)}>Encerrar sessão atual</button>}</section>}
      <section className="chart-panel"><h2>Histórico de sessões</h2>{data.session_history.length ? <div className="table-wrap"><table><thead><tr><th>Início</th><th>Veículo</th><th>Carregador</th><th>Status</th><th>Tempo real</th><th>Energia</th><th>Solar</th><th>Custo final</th></tr></thead><tbody>{data.session_history.map(session => <tr key={session.id}><td>{date(session.started_at)}</td><td>{session.vehicle_name}</td><td>{session.charger_name}</td><td>{statusLabel[session.status]}</td><td>{duration(session.duration_seconds)}</td><td>{number(session.energy_consumed_kwh)} kWh</td><td>{number(session.solar_percentage)}%</td><td>{session.invoice_total === null ? '—' : money(session.invoice_total)}</td></tr>)}</tbody></table></div> : <p>Nenhuma sessão anterior.</p>}</section>
      <section className="chart-panel"><h2>Invoices</h2>{data.invoices.length ? <div className="table-wrap"><table><thead><tr><th>Data</th><th>Sessão</th><th>Status</th><th>Energia</th><th>Valor final</th></tr></thead><tbody>{data.invoices.map(invoice => <tr key={invoice.id}><td>{date(invoice.closed_at ?? invoice.created_at)}</td><td>{invoice.session_id}</td><td>{invoice.status === 'CLOSED' ? 'Fechada' : invoice.status === 'OPEN' ? 'Aberta' : 'Cancelada'}</td><td>{number(Number(invoice.energy_kwh))} kWh</td><td>{invoice.status === 'CLOSED' ? money(invoice.total) : '—'}</td></tr>)}</tbody></table></div> : <p>Nenhuma invoice disponível.</p>}</section>
    </>}
  </div></AppShell>
}
