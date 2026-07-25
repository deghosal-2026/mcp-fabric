import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { DashboardPage } from './Dashboard'

vi.mock('../api/client', () => ({
  fetchDashboard: vi.fn(),
  fetchServers: vi.fn(),
  fetchApprovals: vi.fn(),
  fetchAuditEvents: vi.fn(),
}))

import { fetchDashboard, fetchServers, fetchApprovals, fetchAuditEvents } from '../api/client'

const mockStats = {
  server_count: 42,
  healthy_servers: 38,
  pending_approvals: 5,
  degraded_servers: 3,
}

const mockServers = {
  items: [
    { id: 's1', name: 'server-alpha', endpoint: 'http://a:3001', health_status: 'healthy', trust_level: 'trusted', owner_team: 'platform' },
    { id: 's2', name: 'server-beta', endpoint: 'http://b:3001', health_status: 'degraded', trust_level: 'unreviewed', owner_team: 'data' },
  ],
  pagination: { total: 2, has_more: false, per_page: 5 },
}

const mockApprovals = {
  items: [
    { id: 'a1', capability_name: 'code:search', agent_name: 'agent-dev', status: 'pending' },
  ],
  pagination: { total: 1, has_more: false, per_page: 5 },
}

const mockAudit = {
  items: [
    { id: 'e1', event_type: 'policy_change', actor_id: 'admin@co', created_at: '2026-07-24T10:00:00Z', actor_type: 'admin', target_type: 'policy' },
  ],
  pagination: { total: 1, has_more: false, per_page: 5 },
}

function renderWithProviders() {
  const testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={testQueryClient}>
      <ToastProvider>
        <BrowserRouter>
          <DashboardPage />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(fetchDashboard).mockResolvedValue(mockStats)
  vi.mocked(fetchServers).mockResolvedValue(mockServers)
  vi.mocked(fetchApprovals).mockResolvedValue(mockApprovals)
  vi.mocked(fetchAuditEvents).mockResolvedValue(mockAudit)
})

describe('DashboardPage', () => {
  it('renders 4 stat cards with mock values', async () => {
    renderWithProviders()
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument()
      expect(screen.getByText('38')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
    })
  })

  it('renders 3 panel sections', async () => {
    renderWithProviders()
    await waitFor(() => {
      expect(screen.getByText('Recent Servers')).toBeInTheDocument()
      expect(screen.getByText('Pending Approvals')).toBeInTheDocument()
      expect(screen.getByText('Recent Audit Events')).toBeInTheDocument()
    })
  })

  it('shows loading state via PageState skeleton', () => {
    vi.mocked(fetchDashboard).mockImplementation(() => new Promise(() => {}))
    renderWithProviders()
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })
})
