import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { tokenStore } from './api/client'

const user = { id: 'u1', name: 'Ana', email: 'ana@example.com', role: 'USER', is_active: true, created_at: '', updated_at: '' }
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const show = (path = '/') => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)

beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('authentication flow', () => {
  it('logs in and shows the user dashboard with an empty state', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
      const path = String(input)
      if (path.endsWith('/auth/login')) return json({ access_token: 'token', token_type: 'bearer' })
      if (path.endsWith('/auth/me')) return json(user)
      if (path.endsWith('/user/dashboard')) return json({ current_session: null, session_history: [], invoices: [] })
      throw Error(path)
    })
    show('/login')
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: user.email } })
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'password123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByText('Nenhuma recarga em andamento.')).toBeInTheDocument()
    expect(tokenStore.get()).toBe('token')
    expect(new Headers(fetch.mock.calls.find(([url]) => String(url).endsWith('/auth/me'))?.[1]?.headers).get('Authorization')).toBe('Bearer token')
  })

  it('restores a saved session and prevents a USER entering admin', async () => {
    tokenStore.set('saved')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json(user))
    show('/admin')
    expect(await screen.findByRole('heading', { name: 'Acesso não permitido' })).toBeInTheDocument()
  })

  it('clears an expired token and returns to login', async () => {
    tokenStore.set('expired')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'expired' }, 401))
    show('/user')
    expect(await screen.findByRole('heading', { name: 'Entrar' })).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
  })

  it('shows login errors without saving a token', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(json({ detail: 'Invalid email or password' }, 401))
    show('/login')
    fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: user.email } })
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'wrong-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha inválidos.')
    expect(tokenStore.get()).toBeNull()
  })

  it('shows and retries a dashboard loading error', async () => {
    tokenStore.set('saved')
    let attempts = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
      if (String(input).endsWith('/auth/me')) return json(user)
      attempts += 1
      return attempts === 1 ? json({ detail: 'error' }, 500) : json({ current_session: null, session_history: [], invoices: [] })
    })
    show('/user')
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível carregar o dashboard.')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(() => expect(screen.getByText('Nenhuma recarga em andamento.')).toBeInTheDocument())
  })
})
