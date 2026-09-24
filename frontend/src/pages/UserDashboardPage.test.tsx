import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { App } from '../App'
import { tokenStore } from '../api/client'

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const user = { id: 'u1', name: 'Bia', email: 'bia@example.com', role: 'USER', is_active: true, created_at: '', updated_at: '' }
const current = { id: 's1', status: 'CHARGING', vehicle_name: 'Meu EV', charger_name: 'CH-01', started_at: '2026-09-17T12:00:00Z', ended_at: null, duration_seconds: 3660, allocated_power_kw: 11, energy_consumed_kwh: 10, solar_percentage: 40, estimated_cost: '9.20', invoice_total: null }
const dashboard = { current_session: null, session_history: [], invoices: [] }
const vehicle = { id: 'v1', user_id: 'u1', name: 'Meu EV', brand: 'Good', model: 'One', license_plate: 'EV-2026', max_charge_power_kw: 11, created_at: '', updated_at: '' }
const station = { id: 'st1', name: 'Estação Centro', grid_limit_kw: 50, station_peak_solar_kw: 20, is_active: true }
const charger = { id: 'c1', station_id: 'st1', name: 'CH-01', code: 'CH-01', max_power_kw: 22, status: 'AVAILABLE', is_active: true }

function apiResponse(input: RequestInfo | URL, dashboardData: unknown = dashboard) {
  const url = String(input)
  if (url.endsWith('/auth/me')) return json(user)
  if (url.endsWith('/user/dashboard')) return json(dashboardData)
  if (url.endsWith('/vehicles')) return json([vehicle])
  if (url.endsWith('/stations')) return json([station])
  if (url.endsWith('/chargers')) return json([charger])
  throw new Error(`Unexpected request: ${url}`)
}

function show() { tokenStore.set('token'); render(<MemoryRouter initialEntries={['/user']}><App /></MemoryRouter>) }
beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })

it('shows the active estimate, completed invoice amount and histories', async () => {
  const populated = { current_session: current, session_history: [{ ...current, id: 's0', status: 'COMPLETED', estimated_cost: null, invoice_total: '8.75' }], invoices: [{ id: 'i0', session_id: 's0', status: 'CLOSED', closed_at: '2026-09-17T13:00:00Z', energy_kwh: '10', total: '8.75' }] }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => apiResponse(input, populated))
  show()
  expect(await screen.findByText('Meu EV · CH-01 · Carregando')).toBeInTheDocument()
  expect(screen.getByText('Custo estimado')).toBeInTheDocument()
  expect(screen.getByText(/tarifa capturada no início/)).toBeInTheDocument()
  expect(screen.getAllByText('R$ 8,75')).toHaveLength(2)
  expect(screen.getAllByText('1h 01min')).toHaveLength(2)
})

it('shows loading, empty and retry states', async () => {
  let calls = 0
  let resolveFirstDashboard!: (response: Response) => void
  const firstDashboard = new Promise<Response>(resolve => { resolveFirstDashboard = resolve })
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    if (String(input).endsWith('/auth/me')) return json(user)
    if (String(input).endsWith('/user/dashboard')) { calls++; return calls === 1 ? firstDashboard : json(dashboard) }
    return apiResponse(input)
  })
  show()
  expect(await screen.findByText('Carregando dashboard...')).toBeInTheDocument()
  await act(async () => { resolveFirstDashboard(json({}, 500)) })
  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar os dados operacionais.')
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByText('Nenhuma recarga em andamento.')).toBeInTheDocument()
  expect(screen.getByText('Nenhuma sessão anterior.')).toBeInTheDocument()
  expect(screen.getByText('Nenhuma invoice disponível.')).toBeInTheDocument()
})

it('starts and stops a session using backend responses and prevents duplicate submissions', async () => {
  let active = false
  let startCalls = 0
  let stopCalls = 0
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input)
    if (url.endsWith('/sessions/start')) { startCalls++; active = true; return json({ id: 's1' }, 201) }
    if (url.endsWith('/sessions/s1/stop')) { stopCalls++; active = false; return json({ id: 's1' }) }
    if (url.endsWith('/user/dashboard')) return json(active ? { ...dashboard, current_session: current } : dashboard)
    return apiResponse(input)
  })
  show()
  const start = await screen.findByRole('button', { name: 'Iniciar sessão' })
  await waitFor(() => expect(start).toBeEnabled())
  fireEvent.click(start); fireEvent.click(start)
  expect(await screen.findByText('Sessão iniciada com sucesso.')).toBeInTheDocument()
  expect(startCalls).toBe(1)
  fireEvent.click(screen.getByRole('button', { name: 'Encerrar sessão atual' }))
  expect(screen.getByRole('alertdialog')).toHaveTextContent('Confirma o encerramento')
  const confirm = screen.getByRole('button', { name: 'Sim, encerrar sessão' })
  fireEvent.click(confirm); fireEvent.click(confirm)
  expect(await screen.findByText('Sessão encerrada e dashboard atualizado.')).toBeInTheDocument()
  expect(stopCalls).toBe(1)
})

it('shows expected conflict and validation messages', async () => {
  let status = 409
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    if (String(input).endsWith('/sessions/start')) return json({ detail: 'conflict' }, status)
    return apiResponse(input)
  })
  show()
  const start = await screen.findByRole('button', { name: 'Iniciar sessão' })
  await waitFor(() => expect(start).toBeEnabled())
  fireEvent.click(start)
  expect(await screen.findByRole('alert')).toHaveTextContent('conflito com o estado atual')
  status = 422
  fireEvent.click(start)
  expect(await screen.findByRole('alert')).toHaveTextContent('Revise os campos informados')
})
