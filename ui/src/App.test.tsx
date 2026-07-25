import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'

const mockUseAuthStore = vi.fn()

vi.mock('./stores/authStore', () => ({
  useAuthStore: (selector: unknown) => mockUseAuthStore(selector),
}))

vi.mock('./pages/Login', () => ({
  LoginPage: () => <div data-testid="page-login">Login</div>,
}))
vi.mock('./pages/Dashboard', () => ({
  DashboardPage: () => <div data-testid="page-dashboard">Dashboard</div>,
}))
vi.mock('./pages/Servers', () => ({
  ServersPage: () => <div data-testid="page-servers">Servers</div>,
}))
vi.mock('./pages/Capabilities', () => ({
  CapabilitiesPage: () => <div data-testid="page-capabilities">Capabilities</div>,
}))
vi.mock('./pages/AgentClasses', () => ({
  AgentClassesPage: () => <div data-testid="page-agent-classes">Agent Classes</div>,
}))
vi.mock('./pages/Policies', () => ({
  PoliciesPage: () => <div data-testid="page-policies">Policies</div>,
}))
vi.mock('./pages/Audit', () => ({
  AuditPage: () => <div data-testid="page-audit">Audit</div>,
}))
vi.mock('./pages/Approvals', () => ({
  ApprovalsPage: () => <div data-testid="page-approvals">Approvals</div>,
}))
vi.mock('./pages/Packs', () => ({
  PacksPage: () => <div data-testid="page-packs">Packs</div>,
}))
vi.mock('./pages/Alerts', () => ({
  AlertsPage: () => <div data-testid="page-alerts">Alerts</div>,
}))
vi.mock('./pages/AdminUsers', () => ({
  AdminUsersPage: () => <div data-testid="page-admin-users">Admin Users</div>,
}))
vi.mock('./pages/TrustPosture', () => ({
  TrustPosturePage: () => <div data-testid="page-trust">Trust Posture</div>,
}))

import { LoginPage } from './pages/Login'
import { DashboardPage } from './pages/Dashboard'
import { ServersPage } from './pages/Servers'
import { CapabilitiesPage } from './pages/Capabilities'
import { AgentClassesPage } from './pages/AgentClasses'
import { PoliciesPage } from './pages/Policies'
import { AuditPage } from './pages/Audit'
import { ApprovalsPage } from './pages/Approvals'
import { PacksPage } from './pages/Packs'
import { AlertsPage } from './pages/Alerts'
import { AdminUsersPage } from './pages/AdminUsers'
import { TrustPosturePage } from './pages/TrustPosture'

function MockLayout() {
  const token = mockUseAuthStore((s: { token: string | null }) => s.token)

  return token ? <Outlet /> : <Navigate to="/login" replace />
}

function TestApp({ initialEntries = ['/'] }: { initialEntries?: string[] }) {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<MockLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/servers" element={<ServersPage />} />
          <Route path="/capabilities" element={<CapabilitiesPage />} />
          <Route path="/agent-classes" element={<AgentClassesPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="/packs" element={<PacksPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/trust" element={<TrustPosturePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('App routing', () => {
  it('renders LoginPage when no token', () => {
    mockUseAuthStore.mockImplementation((selector: (s: unknown) => unknown) => {
      const state = { token: null, user: null }
      return selector(state)
    })

    render(<TestApp initialEntries={['/']} />)
    expect(screen.getByTestId('page-login')).toBeInTheDocument()
  })

  it('renders Layout when token exists', () => {
    mockUseAuthStore.mockImplementation((selector: (s: unknown) => unknown) => {
      const state = { token: 'tok-abc', user: { username: 'admin', role: 'admin' } }
      return selector(state)
    })

    render(<TestApp initialEntries={['/']} />)
    expect(screen.getByTestId('page-dashboard')).toBeInTheDocument()
  })

  describe('with token - route navigation', () => {
    beforeEach(() => {
      mockUseAuthStore.mockImplementation((selector: (s: unknown) => unknown) => {
        const state = { token: 'tok-abc', user: { username: 'admin', role: 'admin' } }
        return selector(state)
      })
    })

    it.each([
      ['/servers', 'page-servers'],
      ['/capabilities', 'page-capabilities'],
      ['/agent-classes', 'page-agent-classes'],
      ['/policies', 'page-policies'],
      ['/audit', 'page-audit'],
      ['/approvals', 'page-approvals'],
      ['/packs', 'page-packs'],
      ['/alerts', 'page-alerts'],
      ['/admin/users', 'page-admin-users'],
      ['/trust', 'page-trust'],
    ])('navigating to %s renders %s', (path, testId) => {
      render(<TestApp initialEntries={[path]} />)
      expect(screen.getByTestId(testId)).toBeInTheDocument()
    })
  })

  it('catch-all /* redirects to /', () => {
    mockUseAuthStore.mockImplementation((selector: (s: unknown) => unknown) => {
      const state = { token: 'tok-abc', user: { username: 'admin', role: 'admin' } }
      return selector(state)
    })

    render(<TestApp initialEntries={['/unknown']} />)
    expect(screen.getByTestId('page-dashboard')).toBeInTheDocument()
  })
})
