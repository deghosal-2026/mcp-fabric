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

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    return JSON.parse(atob(padded)) as Record<string, unknown>
  } catch {
    return null
  }
}

function deriveUserFromToken(token: string): AuthUser | null {
  const payload = parseJwtPayload(token)
  const role = payload?.role
  if (role !== 'admin' && role !== 'editor' && role !== 'viewer') return null

  return {
    id: typeof payload?.sub === 'string' ? payload.sub : 'unknown',
    username: typeof payload?.username === 'string' ? payload.username : 'admin',
    role,
    team_namespace: typeof payload?.team_namespace === 'string' ? payload.team_namespace : 'team:platform',
    mfa_enabled: Boolean(payload?.mfa_enabled),
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('fabric_token'),
  user: loadUser() ?? (localStorage.getItem('fabric_token') ? deriveUserFromToken(localStorage.getItem('fabric_token')!) : null),

  login: (token: string, user: AuthUser) => {
    const resolvedUser = user ?? deriveUserFromToken(token)
    localStorage.setItem('fabric_token', token)
    if (resolvedUser) {
      localStorage.setItem('fabric_user', JSON.stringify(resolvedUser))
    } else {
      localStorage.removeItem('fabric_user')
    }
    set({ token, user: resolvedUser })
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
