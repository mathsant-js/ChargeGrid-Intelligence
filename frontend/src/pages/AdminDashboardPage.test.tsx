import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from '../App'
import { tokenStore, type DemandPrediction } from '../api/client'

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const admin = { id: 'u1', name: 'Ana', email: 'ana@example.com', role: 'ADMIN', is_active: true, created_at: '', updated_at: '' }
const stations = [{ id: 's1', name: 'Estação Central', grid_limit_kw: 60, station_peak_solar_kw: 20, is_active: true }]
const session = { id: 'se1', user_id: 'u1', charger_id: 'c1', status: 'CHARGING', allocated_power_kw: 20, energy_consumed_kwh: 5, total_cost: '0', created_at: '', updated_at: '' }
const reading = { id: 'r1', session_id: 'se1', timestamp: '2026-09-17T12:00:00Z', allocated_power_kw: 20, solar_power_kw: 8, grid_power_kw: 12 }
const alert = { id: 'a1', station_id: 's1', title: 'Demanda elevada', message: 'Verifique a rede', severity: 'WARNING', type: 'HIGH_DEMAND', created_at: '2026-09-17T12:00:00Z', acknowledged_at: null }
const summary = { session_count: 1, completed_session_count: 0, energy_consumed_kwh: 5, billed_total: '0.00' }
const sustainability = { solar_energy_kwh: 2, avoided_co2_kg: 0.8 }
const prediction: DemandPrediction = { id: 'p1', station_id: 's1', generated_at: new Date().toISOString(), prediction_for: new Date(Date.now() + 3600000).toISOString(), predicted_demand_kw: 54, capacity_kw: 60, risk_level: 'HIGH', prediction_horizon_minutes: 60, model_version: 'rf-2026.09', recommendation: 'Monitore novas sessões.' }

type MockOptions = { prediction?: DemandPrediction | null; predictionFailure?: number | 'network'; runResult?: DemandPrediction; runFailure?: number | 'network'; stationList?: typeof stations }

function mockApi(options: MockOptions = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = new URL(String(input))
    if (url.pathname.endsWith('/auth/me')) return json(admin)
    if (url.pathname.endsWith('/stations')) return json(options.stationList ?? stations)
    if (url.pathname.endsWith('/chargers')) return json([{ id: 'c1', station_id: 's1', name: 'C1', status: 'CHARGING', is_active: true }])
    if (url.pathname.endsWith('/sessions')) return json([session])
    if (url.pathname.endsWith('/billing/invoices')) return json([])
    if (url.pathname.endsWith('/energy/history')) return json([reading])
    if (url.pathname.endsWith('/solar/history')) return json([{ id: 'sol1', station_id: 's1', timestamp: '2026-09-17T12:00:00Z', available_power_kw: 14 }])
    if (url.pathname.endsWith('/analytics/dashboard')) return json(summary)
    if (url.pathname.endsWith('/analytics/sustainability')) return json(sustainability)
    if (url.pathname.endsWith('/alerts')) return json([alert])
    if (url.pathname.endsWith('/predictions/demand/run') && init?.method === 'POST') {
      if (options.runFailure === 'network') throw new TypeError('offline')
      if (options.runFailure) return json({ detail: 'prediction failure' }, options.runFailure)
      return json(options.runResult ?? prediction, 201)
    }
    if (url.pathname.endsWith('/predictions/demand')) {
      if (options.predictionFailure === 'network') throw new TypeError('offline')
      if (options.predictionFailure) return json({ detail: 'prediction failure' }, options.predictionFailure)
      return options.prediction ? json(options.prediction) : json({ detail: 'Prediction not found' }, 404)
    }
    if (url.pathname.endsWith('/alerts/a1/acknowledge') && init?.method === 'PATCH') return json({ ...alert, acknowledged_at: new Date().toISOString() })
    throw Error(String(input))
  })
}

function show() { tokenStore.set('token'); render(<MemoryRouter initialEntries={['/admin']}><App /></MemoryRouter>) }
beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('admin dashboard prediction', () => {
  it('preserves the informative state when there is no prediction yet', async () => {
    mockApi(); show()
    expect(await screen.findByText('Ainda não há previsão para esta estação.')).toBeInTheDocument()
    expect(screen.queryByText('54 kW')).not.toBeInTheDocument()
  })

  it.each([['LOW', 'Baixo'], ['MEDIUM', 'Médio'], ['HIGH', 'Alto']] as const)('shows a valid %s risk in Portuguese with a non-color indicator', async (level, label) => {
    mockApi({ prediction: { ...prediction, risk_level: level } }); show()
    expect(await screen.findByText('54 kW')).toBeInTheDocument()
    const badge = screen.getByLabelText(`Risco ${label}`)
    expect(badge).toHaveTextContent(label)
    expect(badge.querySelector('[aria-hidden="true"]')).not.toHaveTextContent('')
    expect(screen.getByText('Horário-alvo')).toBeInTheDocument()
    expect(screen.getByText('rf-2026.09')).toBeInTheDocument()
    expect(screen.getByText('Monitore novas sessões.')).toBeInTheDocument()
    expect(screen.getByText('A previsão apoia decisões operacionais e não executa controle energético.')).toBeInTheDocument()
  })

  it('identifies an expired prediction without presenting its values as current', async () => {
    mockApi({ prediction: { ...prediction, prediction_for: new Date(Date.now() - 60000).toISOString() } }); show()
    expect(await screen.findByText(/A previsão desta estação expirou/)).toBeInTheDocument()
    expect(screen.queryByText('54 kW')).not.toBeInTheDocument()
  })

  it.each([[422, 'Dados insuficientes para gerar uma previsão desta estação.'], [503, 'Modelo de previsão indisponível no momento.'], [500, 'Não foi possível comunicar com o serviço de previsão.']] as const)('reports run failure %s with its specific state', async (status, message) => {
    mockApi({ runFailure: status }); show()
    await screen.findByText('Ainda não há previsão para esta estação.')
    fireEvent.click(screen.getByRole('button', { name: 'Gerar nova previsão' }))
    expect(await screen.findByText(message)).toBeInTheDocument()
  })

  it('reports a network communication error while preserving the rest of the dashboard', async () => {
    mockApi({ predictionFailure: 'network' }); show()
    expect(await screen.findByText('Não foi possível comunicar com o serviço de previsão.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Histórico recente' })).toBeInTheDocument()
  })

  it('does not show a prediction returned for another station', async () => {
    mockApi({ prediction: { ...prediction, station_id: 's2' } }); show()
    expect(await screen.findByText('Ainda não há previsão para esta estação.')).toBeInTheDocument()
    expect(screen.queryByText('54 kW')).not.toBeInTheDocument()
  })

  it('requires a station filter when multiple stations exist and requests only the selected station', async () => {
    const fetch = mockApi({ stationList: [...stations, { ...stations[0], id: 's2', name: 'Estação Norte' }] }); show()
    expect(await screen.findByText('Selecione uma estação para consultar a previsão de demanda.')).toBeInTheDocument()
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/predictions/demand'))).toBe(false)
    fireEvent.change(screen.getByLabelText('Estação'), { target: { value: 's2' } })
    await screen.findByText('Ainda não há previsão para esta estação.')
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/predictions/demand?station_id=s2'))).toBe(true)
  })
})

describe('admin dashboard operations', () => {
  it('applies period filters and acknowledges alerts through the API', async () => {
    const fetch = mockApi({ prediction }); show()
    await screen.findByText('54 kW')
    fireEvent.change(screen.getByLabelText('Período'), { target: { value: '24h' } })
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).includes('/analytics/dashboard?') && String(url).includes('from='))).toBe(true))
    fireEvent.click(await screen.findByRole('button', { name: 'Reconhecer' }))
    expect(await screen.findByText('Reconhecido')).toBeInTheDocument()
  })

  it('offers retry on dashboard load failure and preserves an alert on acknowledgement failure', async () => {
    const fetch = mockApi(); let failed = false
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
