import type { ApiState } from '../hooks/useApiHealth'

const labels: Record<ApiState, string> = {
  checking: 'Verificando API',
  online: 'API operacional',
  offline: 'API indisponível',
}

export function StatusBadge({ state }: { state: ApiState }) {
  return (
    <span className={`status status--${state}`} role="status">
      <span className="status__dot" aria-hidden="true" />
      {labels[state]}
    </span>
  )
}
