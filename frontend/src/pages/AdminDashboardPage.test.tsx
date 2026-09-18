import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../App'
import { tokenStore } from '../api/client'

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const admin = { id: 'u1', name: 'Ana', email: 'ana@example.com', role: 'ADMIN', is_active: true, created_at: '', updated_at: '' }
const station = { id: 's1', name: 'Estação Central', grid_limit_kw: 60, station_peak_solar_kw: 20, is_active: true }
const session = { id: 'se1', user_id: 'u1', charger_id: 'c1', status: 'CHARGING', allocated_power_kw: 20, energy_consumed_kwh: 5, total_cost: '0', created_at: '', updated_at: '' }
const reading = { id: 'r1', session_id: 'se1', timestamp: '2026-09-17T12:00:00Z', allocated_power_kw: 20, solar_power_kw: 8, grid_power_kw: 12 }
const alert = { id: 'a1', station_id: 's1', title: 'Demanda elevada', message: 'Verifique a rede', severity: 'WARNING', type: 'HIGH_DEMAND', created_at: '2026-09-17T12:00:00Z', acknowledged_at: null }
const summary = { session_count: 1, completed_session_count: 0, energy_consumed_kwh: 5, billed_total: '0.00' }
const sustainability = { solar_energy_kwh: 2, avoided_co2_kg: 0.8 }
const prediction = { id: 'p1', station_id: 's1', generated_at: new Date().toISOString(), prediction_for: new Date(Date.now() + 3600000).toISOString(), predicted_demand_kw: 54, capacity_kw: 60, risk_level: 'HIGH', prediction_horizon_minutes: 60, model_version: 'baseline' }

function mockApi(withPrediction = false) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = new URL(String(input))
    if (url.pathname.endsWith('/auth/me')) return json(admin)
    if (url.pathname.endsWith('/stations')) return json([station])
    if (url.pathname.endsWith('/chargers')) return json([{ id: 'c1', station_id: 's1', name: 'C1', status: 'CHARGING', is_active: true }])
    if (url.pathname.endsWith('/sessions')) return json([session])
    if (url.pathname.endsWith('/billing/invoices')) return json([])
    if (url.pathname.endsWith('/energy/history')) return json([reading])
    if (url.pathname.endsWith('/solar/history')) return json([{ id: 'sol1', station_id: 's1', timestamp: '2026-09-17T12:00:00Z', available_power_kw: 14 }])
    if (url.pathname.endsWith('/analytics/dashboard')) return json(summary)
    if (url.pathname.endsWith('/analytics/sustainability')) return json(sustainability)
    if (url.pathname.endsWith('/alerts')) return json([alert])
    if (url.pathname.endsWith('/predictions/demand')) return withPrediction ? json(prediction) : json({ detail: 'Prediction not found' }, 404)
    if (url.pathname.endsWith('/alerts/a1/acknowledge') && init?.method === 'PATCH') return json({ ...alert, acknowledged_at: new Date().toISOString() })
    throw Error(String(input))
  })
}

function show() { tokenStore.set('token'); render(<MemoryRouter initialEntries={['/admin']}><App /></MemoryRouter>) }
beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('admin dashboard', () => {
  it('renders live indicators, history and a clear missing ML state', async () => {
    mockApi()
    show()
    expect(await screen.findByRole('heading', { name: 'Dashboard do gestor' })).toBeInTheDocument()
    expect(await screen.findByText('Ainda não há dados válidos de ML para esta estação.')).toBeInTheDocument()
    expect(screen.getAllByText('20 kW').length).toBeGreaterThan(0)
    expect(screen.getByText('60 kW')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Histórico recente' })).toBeInTheDocument()
    expect(screen.queryByText('Risco de pico')).not.toBeInTheDocument()
  })

  it('shows a valid prediction and acknowledges alerts through the API', async () => {
    const fetch = mockApi(true)
    show()
    expect(await screen.findByText('Risco de pico')).toBeInTheDocument()
    expect(screen.getByText('54 kW')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reconhecer' }))
    expect(await screen.findByText('Reconhecido')).toBeInTheDocument()
    expect(fetch.mock.calls.some(([url, init]) => String(url).endsWith('/alerts/a1/acknowledge') && init?.method === 'PATCH')).toBe(true)
  })

  it('applies station and period filters', async () => {
    const fetch = mockApi()
    show()
    await screen.findByText('Ainda não há dados válidos de ML para esta estação.')
    fireEvent.change(screen.getByLabelText('Período'), { target: { value: '24h' } })
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes('/analytics/dashboard?') && String(url).includes('from='))).toBe(true))
    fireEvent.change(screen.getByLabelText('Estação'), { target: { value: 's1' } })
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes('/analytics/dashboard?') && String(url).includes('station_id=s1'))).toBe(true))
  })

  it('offers retry on load failure and preserves alert on acknowledgement failure', async () => {
    const fetch = mockApi()
    let failed = false
    const original = fetch.getMockImplementation()!
    fetch.mockImplementation(async (input, init) => {
      if (String(input).endsWith('/analytics/dashboard') && !failed) { failed = true; return json({}, 500) }
      if (String(input).endsWith('/alerts/a1/acknowledge')) return json({}, 500)
      return original(input, init)
    })
    show()
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o dashboard.')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(await screen.findByText('Demanda elevada')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reconhecer' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível reconhecer o alerta.')
    expect(screen.getByRole('button', { name: 'Reconhecer' })).toBeInTheDocument()
  })
})
