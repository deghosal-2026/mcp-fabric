import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '../stores/authStore'
import type { AuthUser } from '../types'

const mockUser: AuthUser = {
  id: 'u1',
  username: 'admin',
  role: 'admin',
  team_namespace: 'platform',
  mfa_enabled: false,
}

beforeEach(() => {
  vi.restoreAllMocks()
  useAuthStore.setState({ token: null, user: null })
})

describe('fetcher', () => {
  it('attaches auth header when token exists', async () => {
    useAuthStore.setState({ token: 'tok-abc', user: mockUser })
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )

    const { fetcher } = await import('./client')
    await fetcher('/servers')

    const [, options] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(options.headers).toMatchObject({
      Authorization: 'Bearer tok-abc',
    })
  })

  it('omits auth header when token is null', async () => {
    useAuthStore.setState({ token: null, user: null })
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )

    const { fetcher } = await import('./client')
    await fetcher('/servers')

    const [, options] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const headers = options.headers as Record<string, string>
    expect(headers.Authorization).toBeUndefined()
  })

  it('sets Content-Type and Accept headers', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )

    const { fetcher } = await import('./client')
    await fetcher('/servers')

    const [, options] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const headers = options.headers as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
    expect(headers['Accept']).toBe('application/vnd.fabric.v1+json')
  })

  it('401 on /auth/ path does NOT logout or redirect', async () => {
    useAuthStore.setState({ token: 'tok-abc', user: mockUser })
    const logout = vi.spyOn(useAuthStore.getState(), 'logout')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 401 }),
    )
    const originalLocation = window.location
    const hrefSetter = vi.fn()
    vi.stubGlobal('window', {
      ...originalLocation,
      location: { ...originalLocation, set href(v: string) { hrefSetter(v) } },
    })

    const { fetcher } = await import('./client')
    await expect(fetcher('/auth/login')).rejects.toThrow()
    expect(logout).not.toHaveBeenCalled()
    expect(hrefSetter).not.toHaveBeenCalled()
  })

  it('401 on non-auth path calls logout and sets window.location.href', async () => {
    useAuthStore.setState({ token: 'tok-abc', user: mockUser })
    const logout = vi.spyOn(useAuthStore.getState(), 'logout')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 401 }),
    )
    const originalLocation = window.location
    const hrefSetter = vi.fn()
    vi.stubGlobal('window', {
      ...originalLocation,
      location: { ...originalLocation, set href(v: string) { hrefSetter(v) } },
    })

    const { fetcher } = await import('./client')
    await expect(fetcher('/servers')).rejects.toThrow('Unauthorized')
    expect(logout).toHaveBeenCalledTimes(1)
    expect(hrefSetter).toHaveBeenCalledWith('/login')
  })

  it('parses error message from response body on 4xx', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ message: 'Server not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const { fetcher } = await import('./client')
    await expect(fetcher('/servers/xyz')).rejects.toThrow('Server not found')
  })

  it('falls back to "Request failed: {status}" when body is empty', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 422 }),
    )

    const { fetcher } = await import('./client')
    await expect(fetcher('/servers')).rejects.toThrow('Request failed: 422')
  })

  it('handles malformed JSON in error body', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('not json', { status: 500 }),
    )

    const { fetcher } = await import('./client')
    await expect(fetcher('/servers')).rejects.toThrow('Request failed: 500')
  })
})

describe('buildQuery', () => {
  it('builds query string from params', async () => {
    const { buildQuery } = await import('./client')
    const result = buildQuery('/servers', { status: 'healthy', page: '1' })
    expect(result).toBe('/servers?status=healthy&page=1')
  })

  it('skips undefined values', async () => {
    const { buildQuery } = await import('./client')
    const result = buildQuery('/servers', { status: 'healthy', page: undefined })
    expect(result).toBe('/servers?status=healthy')
  })

  it('returns base unchanged when no params', async () => {
    const { buildQuery } = await import('./client')
    expect(buildQuery('/servers')).toBe('/servers')
    expect(buildQuery('/servers', undefined)).toBe('/servers')
  })
})

describe('queryClient defaults', () => {
  it('retry is 1, staleTime is 30000, refetchOnWindowFocus is false', async () => {
    const { queryClient } = await import('./client')
    const defaults = queryClient.getDefaultOptions().queries!
    expect(defaults.retry).toBe(1)
    expect(defaults.staleTime).toBe(30_000)
    expect(defaults.refetchOnWindowFocus).toBe(false)
  })
})
