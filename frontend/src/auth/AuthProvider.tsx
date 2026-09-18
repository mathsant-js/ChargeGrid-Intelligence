import { useEffect, useState, type PropsWithChildren } from 'react'
import { api, tokenStore } from '../api/client'
import { AuthContext, type AuthState } from './context'

export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>({ status: tokenStore.get() ? 'loading' : 'anonymous' })

  useEffect(() => {
    let active = true
    if (tokenStore.get()) {
      api.me().then(user => { if (active) setState({ status: 'authenticated', user }) })
        .catch(() => { if (active) { tokenStore.clear(); setState({ status: 'anonymous' }) } })
    }
    const sync = () => { if (!tokenStore.get()) setState({ status: 'anonymous' }) }
    window.addEventListener('chargegrid:auth', sync)
    window.addEventListener('storage', sync)
    return () => { active = false; window.removeEventListener('chargegrid:auth', sync); window.removeEventListener('storage', sync) }
  }, [])

  async function login(email: string, password: string) {
    const token = await api.login(email, password)
    tokenStore.set(token.access_token)
    try { const user = await api.me(); setState({ status: 'authenticated', user }) }
    catch (error) { tokenStore.clear(); throw error }
  }
  function logout() { tokenStore.clear(); setState({ status: 'anonymous' }) }
  return <AuthContext.Provider value={{ state, login, logout }}>{children}</AuthContext.Provider>
}
