import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { FoundationPage } from './FoundationPage'

describe('FoundationPage', () => {
  afterEach(cleanup)

  it('shows the three pitch deliverables', () => {
    render(<MemoryRouter><FoundationPage /></MemoryRouter>)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Operação inteligente de recarga')
    expect(screen.getByText('Gerenciamento de demanda')).toBeInTheDocument()
    expect(screen.getByText('Cobrança em tempo real')).toBeInTheDocument()
    expect(screen.getByText('Recargas inteligentes')).toBeInTheDocument()
  })

  it('starts and finishes the accelerated simulation', () => {
    render(<MemoryRouter><FoundationPage /></MemoryRouter>)

    fireEvent.click(screen.getByRole('button', { name: /iniciar simulação/i }))
    expect(screen.getByText('Simulação em execução')).toBeInTheDocument()
    expect(screen.getAllByText('Carregando')).toHaveLength(4)

    fireEvent.click(screen.getByRole('button', { name: /finalizar e cobrar/i }))
    expect(screen.getByText('Invoice fechada')).toBeInTheDocument()
    expect(screen.getAllByText('Concluída')).toHaveLength(4)
  })
})
