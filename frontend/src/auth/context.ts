import { createContext, useContext } from 'react'
import type { User } from '../api/client'

export type AuthState = { status: 'loading' } | { status: 'anonymous' } | { status: 'authenticated'; user: User }
export interface AuthContextValue { state: AuthState; login: (email: string, password: string) => Promise<void>; logout: () => void }
export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider ausente')
  return value
}
