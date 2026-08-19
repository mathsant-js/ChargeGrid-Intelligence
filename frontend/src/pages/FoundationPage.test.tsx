import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FoundationPage } from './FoundationPage'

describe('FoundationPage', () => {
  afterEach(() => vi.restoreAllMocks())

  it('shows the configured foundation and the healthy API state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
    )

    render(
      <MemoryRouter>
        <FoundationPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Energia de recarga transformada em decisões inteligentes.',
    )
    expect(await screen.findByText('API operacional')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL + Alembic')).toBeInTheDocument()
  })

  it('shows an unavailable state when the API request fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'))

    render(
      <MemoryRouter>
        <FoundationPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('API indisponível')).toBeInTheDocument()
  })
})
