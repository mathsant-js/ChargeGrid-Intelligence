import { useState } from 'react'

import { StatusBadge } from '../components/StatusBadge'
import { useApiHealth } from '../hooks/useApiHealth'
import { AppShell } from '../layouts/AppShell'

const foundations = [
  ['API', 'FastAPI + OpenAPI'],
  ['Dados', 'PostgreSQL + Alembic'],
  ['Interface', 'React + TypeScript'],
  ['Ambiente', 'Docker Compose'],
]

export function FoundationPage() {
  const apiState = useApiHealth()
  const [chargingStarted, setChargingStarted] = useState(false)

  return (
    <AppShell>
      <section className="hero">
        <div className="hero__content">
          <p className="eyebrow">EV Challenge 2026</p>
          <h1>Energia de recarga transformada em decisões inteligentes.</h1>
          <p className="hero__copy">
            A fundação técnica está pronta para receber os primeiros fluxos de usuários,
            veículos, estações e sessões.
          </p>
          <StatusBadge state={apiState} />
        </div>

        <section className="charging-demo" aria-labelledby="charging-demo-title">
          <div className="charging-demo__intro">
            <p className="eyebrow">Demonstração acadêmica</p>
            <h2 id="charging-demo-title">Simule o início de uma recarga</h2>
            <p>
              Veja como o ChargeGrid apresenta uma sessão após validar o veículo e o
              carregador.
            </p>
          </div>

          {chargingStarted ? (
            <div className="charging-result" role="status" aria-live="polite">
              <div className="charging-result__header">
                <span className="charging-result__icon" aria-hidden="true">
                  ✓
                </span>
                <div>
                  <span>Recarga iniciada</span>
                  <strong>Status: Carregando</strong>
                </div>
              </div>
              <dl>
                <div>
                  <dt>Potência solicitada</dt>
                  <dd>11 kW</dd>
                </div>
                <div>
                  <dt>Carregador</dt>
                  <dd>CH-01</dd>
                </div>
              </dl>
            </div>
          ) : (
            <button
              className="charging-demo__button"
              type="button"
              onClick={() => setChargingStarted(true)}
            >
              Simular início da recarga
            </button>
          )}
        </section>

        <div className="grid" aria-label="Tecnologias configuradas">
          {foundations.map(([title, detail]) => (
            <article className="foundation-card" key={title}>
              <span>{title}</span>
              <strong>{detail}</strong>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  )
}
