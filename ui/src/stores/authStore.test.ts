import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from './authStore'
import type { AuthUser } from '../types'

const mockUser: AuthUser = {
  id: 'u1',
  username: 'admin',
  role: 'admin',
  team_namespace: 'platform',
  mfa_enabled: false,
}

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState({ token: null, user: null })
})

describe('authStore', () => {
  it('starts with null token and user when localStorage empty', () => {
    const { token, user } = useAuthStore.getState()
    expect(token).toBeNull()
    expect(user).toBeNull()
  })

  it('reads token from localStorage on creation', async () => {
    localStorage.setItem('fabric_token', 'tok-abc')
    vi.resetModules()
    const { useAuthStore: fresh } = await import('./authStore')
    expect(fresh.getState().token).toBe('tok-abc')
  })

  it('reads valid JSON from localStorage for user', async () => {
    localStorage.setItem('fabric_user', JSON.stringify(mockUser))
    vi.resetModules()
    const { useAuthStore: fresh } = await import('./authStore')
    expect(fresh.getState().user).toEqual(mockUser)
  })

  it('handles corrupted JSON in localStorage', async () => {
    localStorage.setItem('fabric_user', 'not json')
    vi.resetModules()
    const { useAuthStore: fresh } = await import('./authStore')
    expect(fresh.getState().user).toBeNull()
    expect(localStorage.getItem('fabric_user')).toBeNull()
  })

  it('login sets token and user in store and localStorage', () => {
    useAuthStore.getState().login('tok-xyz', mockUser)

    const { token, user } = useAuthStore.getState()
    expect(token).toBe('tok-xyz')
    expect(user).toEqual(mockUser)
    expect(localStorage.getItem('fabric_token')).toBe('tok-xyz')
    expect(JSON.parse(localStorage.getItem('fabric_user')!)).toEqual(mockUser)
  })

  it('logout clears token and user from store and localStorage', () => {
    useAuthStore.getState().login('tok-xyz', mockUser)
    useAuthStore.getState().logout()

    const { token, user } = useAuthStore.getState()
    expect(token).toBeNull()
    expect(user).toBeNull()
    expect(localStorage.getItem('fabric_token')).toBeNull()
    expect(localStorage.getItem('fabric_user')).toBeNull()
  })

  it('isAuthenticated returns true when token present', () => {
    useAuthStore.getState().login('tok-xyz', mockUser)
    expect(useAuthStore.getState().isAuthenticated()).toBe(true)
  })

  it('isAuthenticated returns false when token null', () => {
    expect(useAuthStore.getState().isAuthenticated()).toBe(false)
  })

  it('after login then logout, isAuthenticated returns false', () => {
    useAuthStore.getState().login('tok-xyz', mockUser)
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().isAuthenticated()).toBe(false)
  })
})
