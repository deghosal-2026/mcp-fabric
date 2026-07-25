import { create } from 'zustand'
import type { AuthUser } from '../types'

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  login: (token: string, user: AuthUser) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

function loadUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem('fabric_user')
    return raw ? JSON.parse(raw) : null
  } catch {
    localStorage.removeItem('fabric_user')
    return null
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('fabric_token'),
  user: loadUser(),

  login: (token: string, user: AuthUser) => {
    localStorage.setItem('fabric_token', token)
    localStorage.setItem('fabric_user', JSON.stringify(user))
    set({ token, user })
  },

  logout: () => {
    localStorage.removeItem('fabric_token')
    localStorage.removeItem('fabric_user')
    set({ token: null, user: null })
  },

  isAuthenticated: () => {
    return get().token !== null
  },
}))
