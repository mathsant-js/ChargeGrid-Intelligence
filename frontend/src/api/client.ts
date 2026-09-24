const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
const TOKEN_KEY = 'chargegrid.access_token'

export type Role = 'ADMIN' | 'USER'
export interface User { id: string; name: string; email: string; role: Role; is_active: boolean; created_at: string; updated_at: string }
export interface Vehicle { id: string; user_id: string; name: string; brand: string; model: string; license_plate: string; max_charge_power_kw: number; created_at: string; updated_at: string }
export interface VehicleInput { name: string; brand: string; model: string; license_plate: string; max_charge_power_kw: number }
export interface TokenResponse { access_token: string; token_type: 'bearer' }
export interface ChargingSession { id: string; user_id: string; vehicle_id: string; charger_id: string; status: 'CREATED' | 'CHARGING' | 'PAUSED' | 'COMPLETED' | 'CANCELLED'; started_at: string | null; ended_at: string | null; requested_power_kw: number; allocated_power_kw: number; energy_consumed_kwh: number; solar_energy_kwh: number; grid_energy_kwh: number; tariff_per_kwh: string; total_cost: string; created_at: string; updated_at: string }
export interface EnergyReading { id: string; session_id: string; timestamp: string; requested_power_kw: number; allocated_power_kw: number; solar_power_kw: number; grid_power_kw: number; interval_energy_kwh: number; solar_energy_kwh: number; grid_energy_kwh: number }
export interface Invoice { id: string; session_id: string; user_id: string; energy_kwh: string; tariff_per_kwh: string; subtotal: string; total: string; status: 'OPEN' | 'CLOSED' | 'CANCELLED'; created_at: string; closed_at: string | null }
export interface UserSessionSummary { id: string; status: ChargingSession['status']; vehicle_name: string; charger_name: string; started_at: string | null; ended_at: string | null; duration_seconds: number; allocated_power_kw: number; energy_consumed_kwh: number; solar_percentage: number; estimated_cost: string | null; invoice_total: string | null }
export interface UserDashboard { current_session: UserSessionSummary | null; session_history: UserSessionSummary[]; invoices: Invoice[] }
export interface Dashboard { station_id: string | null; user_id: string | null; session_count: number; completed_session_count: number; energy_consumed_kwh: number; solar_energy_kwh: number; grid_energy_kwh: number; billed_total: string; currency: string }
export interface Sustainability { station_id: string | null; user_id: string | null; energy_consumed_kwh: number; solar_energy_kwh: number; grid_energy_kwh: number; solar_percentage: number; avoided_co2_kg: number; grid_emission_factor_kg_per_kwh: number; estimated_solar_savings: string; currency: string }
export interface Filters { station_id?: string; user_id?: string; from?: string; to?: string }
export interface Station { id: string; name: string; grid_limit_kw: number; station_peak_solar_kw: number; is_active: boolean }
export interface Charger { id: string; station_id: string; name: string; code: string; max_power_kw: number; status: 'AVAILABLE' | 'CHARGING' | 'UNAVAILABLE'; is_active: boolean }
export interface SolarReading { id: string; station_id: string; timestamp: string; available_power_kw: number }
export interface DemandPrediction { id: string; station_id: string; generated_at: string; prediction_for: string; predicted_demand_kw: number; capacity_kw: number; risk_level: 'LOW' | 'MEDIUM' | 'HIGH'; prediction_horizon_minutes: number; model_version: string; recommendation: string }
export interface Alert { id: string; station_id: string; type: string; severity: 'INFO' | 'WARNING' | 'CRITICAL'; title: string; message: string; created_at: string; acknowledged_at: string | null }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = 'ApiError' }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => { localStorage.setItem(TOKEN_KEY, token); window.dispatchEvent(new Event('chargegrid:auth')) },
  clear: () => { localStorage.removeItem(TOKEN_KEY); window.dispatchEvent(new Event('chargegrid:auth')) },
}

function query(filters?: Filters): string {
  const params = new URLSearchParams()
  if (filters) Object.entries(filters).forEach(([key, value]) => { if (value !== undefined) params.set(key, value) })
  return params.size ? `?${params}` : ''
}

async function request<T>(path: string, options: RequestInit = {}, authenticated = true): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  const token = authenticated ? tokenStore.get() : null
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try { response = await fetch(`${API_URL}${path}`, { ...options, headers }) }
  catch { throw new ApiError(0, 'Não foi possível conectar à API.') }
  if (response.status === 401 && authenticated && token && tokenStore.get() === token) tokenStore.clear()
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string' ? body.detail : undefined
    throw new ApiError(response.status, response.status === 403 ? 'Acesso não permitido.' : detail ?? `Erro HTTP ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  login: (email: string, password: string) => request<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }, false),
  me: () => request<User>('/auth/me'),
  sessions: () => request<ChargingSession[]>('/sessions'),
  userDashboard: () => request<UserDashboard>('/user/dashboard'),
  vehicles: () => request<Vehicle[]>('/vehicles'),
  createVehicle: (vehicle: VehicleInput) => request<Vehicle>('/vehicles', { method: 'POST', body: JSON.stringify(vehicle) }),
  updateVehicle: (id: string, vehicle: VehicleInput) => request<Vehicle>(`/vehicles/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(vehicle) }),
  deleteVehicle: (id: string) => request<void>(`/vehicles/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  session: (id: string) => request<ChargingSession>(`/sessions/${encodeURIComponent(id)}`),
  startSession: (vehicle_id: string, charger_id: string) => request<ChargingSession>('/sessions/start', { method: 'POST', body: JSON.stringify({ vehicle_id, charger_id }) }),
  stopSession: (id: string) => request<ChargingSession>(`/sessions/${encodeURIComponent(id)}/stop`, { method: 'POST' }),
  currentEnergy: (station_id?: string) => request<EnergyReading | null>(`/energy/current${query({ station_id })}`),
  energyHistory: (filters?: Filters) => request<EnergyReading[]>(`/energy/history${query(filters)}`),
  invoices: (filters?: { user_id?: string; status?: string }) => request<Invoice[]>(`/billing/invoices${query(filters)}`),
  invoice: (id: string) => request<Invoice>(`/billing/invoices/${encodeURIComponent(id)}`),
  dashboard: (filters?: Filters) => request<Dashboard>(`/analytics/dashboard${query(filters)}`),
  sustainability: (filters?: Filters) => request<Sustainability>(`/analytics/sustainability${query(filters)}`),
  stations: () => request<Station[]>('/stations'),
  chargers: () => request<Charger[]>('/chargers'),
  solarHistory: (filters?: Filters) => request<SolarReading[]>(`/solar/history${query(filters)}`),
  prediction: (station_id: string) => request<DemandPrediction>(`/predictions/demand${query({ station_id })}`),
  runPrediction: (station_id: string) => request<DemandPrediction>('/predictions/demand/run', { method: 'POST', body: JSON.stringify({ station_id }) }),
  alerts: (station_id?: string) => request<Alert[]>(`/alerts${query({ station_id })}`),
  acknowledgeAlert: (id: string) => request<Alert>(`/alerts/${encodeURIComponent(id)}/acknowledge`, { method: 'PATCH' }),
}

export interface HealthResponse { status: 'ok' }
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>('/health', { signal }, false)
}
