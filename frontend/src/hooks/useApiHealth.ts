import { useEffect, useState } from 'react'

import { getHealth } from '../api/client'

export type ApiState = 'checking' | 'online' | 'offline'

export function useApiHealth(): ApiState {
  const [state, setState] = useState<ApiState>('checking')

  useEffect(() => {
    const controller = new AbortController()

    getHealth(controller.signal)
      .then(() => setState('online'))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState('offline')
      })

    return () => controller.abort()
  }, [])

  return state
}
