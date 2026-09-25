import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../App'
import { tokenStore } from '../api/client'
import './AdminOperationsPage'

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const admin = { id: 'a1', name: 'Admin', email: 'admin@example.com', role: 'ADMIN', is_active: true, created_at: '', updated_at: '' }
const user = { ...admin, id: 'u1', role: 'USER' }
const station = { id: 's1', name: 'Central', description: 'Matriz', grid_limit_kw: 60, station_peak_solar_kw: 20, is_active: true }
const charger = { id: 'c1', station_id: 's1', name: 'Carga 1', code: 'CG-01', max_power_kw: 22, status: 'AVAILABLE', is_active: true }
const tariff = { id: 't1', name: 'Padrão', price_per_kwh: '0.9200', currency: 'BRL', is_active: true, valid_from: '2026-09-01T00:00:00Z', valid_until: null, created_at: '' }
const configuration = { id: 'cfg1', simulation_speed: 60, grid_emission_factor_kg_per_kwh: 0.084, high_demand_threshold: 0.85, high_solar_availability_threshold: 0.8, medium_peak_threshold: 0.7, high_peak_threshold: 0.9, created_at: '', updated_at: '' }
const simulation = { state: 'STOPPED', current_instant: '2026-09-23T12:00:00Z', tick_duration_seconds: 60, simulation_speed: 60, last_tick: null }

function mockApi(role: 'ADMIN' | 'USER' = 'ADMIN') {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = new URL(String(input)); const method = init?.method ?? 'GET'
    if (url.pathname.endsWith('/auth/me')) return json(role === 'ADMIN' ? admin : user)
    if (url.pathname.endsWith('/stations')) return method === 'POST' ? json(station, 201) : json([station])
    if (url.pathname.endsWith('/chargers')) return json([charger])
    if (url.pathname.endsWith('/tariffs')) return json([tariff])
    if (url.pathname.endsWith('/system-configuration')) return method === 'PATCH' ? json(configuration) : json(configuration)
    if (url.pathname.endsWith('/simulation/status')) return json(simulation)
    if (url.pathname.endsWith('/simulation/reset')) return json(simulation)
    return json({ detail: 'unexpected' }, 500)
  })
}

function show() { tokenStore.set('token'); render(<MemoryRouter initialEntries={['/admin/operacao']}><App /></MemoryRouter>) }
beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('admin operations authorization and rendering', () => {
  it('prevents a regular user from opening the administration route', async () => {
    mockApi('USER'); show()
    expect(await screen.findByRole('heading', { name: 'Acesso não permitido' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Operação do MVP' })).not.toBeInTheDocument()
  })

  it('renders every minimum management area with loaded data', async () => {
    mockApi(); show()
    expect(await screen.findByRole('heading', { name: 'Estações' })).toBeInTheDocument()
    for (const name of ['Carregadores', 'Tarifas', 'Energia, risco e simulação']) expect(screen.getByRole('heading', { name })).toBeInTheDocument()
    expect(screen.getAllByText('Central').length).toBeGreaterThan(0)
    expect(screen.getByText('Carga 1 (CG-01)')).toBeInTheDocument()
    expect(screen.getByText('Padrão')).toBeInTheDocument()
    expect(screen.getByText(/classificação de risco permanece calculada pelo backend/i)).toBeInTheDocument()
  })

  it('validates risk threshold ordering before calling the API', async () => {
    const fetch = mockApi(); show(); await screen.findByRole('heading', { name: 'Estações' })
    fireEvent.change(screen.getByLabelText('Limiar de risco médio'), { target: { value: '0.95' } })
    fireEvent.change(screen.getByLabelText('Limiar de risco alto'), { target: { value: '0.9' } })
    fireEvent.click(screen.getByRole('button', { name: 'Atualizar parâmetros' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('O limiar médio deve ser menor que o limiar alto.')
    expect(fetch.mock.calls.filter(([url, init]) => String(url).endsWith('/system-configuration') && init?.method === 'PATCH')).toHaveLength(0)
  })

  it('requires confirmation before resetting the simulation clock', async () => {
    const fetch = mockApi(); const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false); show(); await screen.findByRole('heading', { name: 'Estações' })
    fireEvent.click(screen.getByRole('button', { name: 'Redefinir relógio' }))
    expect(confirm).toHaveBeenCalled()
    expect(fetch.mock.calls.some(([url]) => String(url).endsWith('/simulation/reset'))).toBe(false)
  })

  it('shows API validation and conflict messages near the form', async () => {
    const fetch = mockApi(); const original = fetch.getMockImplementation()!
    fetch.mockImplementation(async (input, init) => String(input).endsWith('/stations') && init?.method === 'POST' ? json({ detail: 'Station already exists' }, 409) : original(input, init))
    show(); await screen.findByRole('heading', { name: 'Estações' })
    const names = screen.getAllByLabelText('Nome'); fireEvent.change(names[0], { target: { value: 'Central' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cadastrar estação' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Conflito: Station already exists')
  })
})
