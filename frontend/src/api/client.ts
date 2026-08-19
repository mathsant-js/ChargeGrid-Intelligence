const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export interface HealthResponse {
  status: 'ok'
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`, { signal })

  if (!response.ok) {
    throw new Error(`API indisponível (${response.status})`)
  }

  return response.json() as Promise<HealthResponse>
}
