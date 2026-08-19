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
