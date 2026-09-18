import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { App } from '../App'
import { tokenStore } from '../api/client'

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const user = { id: 'u1', name: 'Bia', email: 'bia@example.com', role: 'USER', is_active: true, created_at: '', updated_at: '' }
const current = { id: 's1', status: 'CHARGING', vehicle_name: 'Meu EV', charger_name: 'CH-01', started_at: '2026-09-17T12:00:00Z', ended_at: null, duration_seconds: 3660, allocated_power_kw: 11, energy_consumed_kwh: 10, solar_percentage: 40, estimated_cost: '9.20', invoice_total: null }

function show() { tokenStore.set('token'); render(<MemoryRouter initialEntries={['/user']}><App /></MemoryRouter>) }
beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })

it('shows the active estimate, completed invoice amount and histories', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => String(input).endsWith('/auth/me') ? json(user) : json({ current_session: current, session_history: [{ ...current, id: 's0', status: 'COMPLETED', estimated_cost: null, invoice_total: '8.75' }], invoices: [{ id: 'i0', session_id: 's0', status: 'CLOSED', closed_at: '2026-09-17T13:00:00Z', energy_kwh: '10', total: '8.75' }] }))
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
    calls++
    return calls === 1 ? firstDashboard : json({ current_session: null, session_history: [], invoices: [] })
  })
  show()
  expect(await screen.findByText('Carregando dashboard...')).toBeInTheDocument()
  await act(async () => { resolveFirstDashboard(json({}, 500)) })
  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o dashboard.')
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByText('Nenhuma recarga em andamento.')).toBeInTheDocument()
  expect(screen.getByText('Nenhuma sessão anterior.')).toBeInTheDocument()
  expect(screen.getByText('Nenhuma invoice disponível.')).toBeInTheDocument()
})
