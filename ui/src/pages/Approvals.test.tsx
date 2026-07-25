import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { ApprovalsPage } from './Approvals'
import { fetchApprovals, resolveApproval } from '../api/client'
import type { ApprovalRequest } from '../types'

vi.mock('../api/client', () => ({
  fetchApprovals: vi.fn(),
  resolveApproval: vi.fn(),
}))

const mockFetchApprovals = vi.mocked(fetchApprovals)
const mockResolveApproval = vi.mocked(resolveApproval)

function renderWithProviders(ui: React.ReactElement) {
  const testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={testQueryClient}>
      <ToastProvider>
        <BrowserRouter>{ui}</BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}

const mockApprovals: ApprovalRequest[] = [
  {
    id: 'ap-1',
    agent_identity_id: 'ai-1',
    capability_id: 'cap-1',
    server_id: 'srv-1',
    request_params: {},
    status: 'pending',
    approver_id: null,
    requested_at: '2025-01-15T10:00:00Z',
    resolved_at: null,
    agent_name: 'agent-alpha',
    capability_name: 'code-review',
    server_name: 'github-mcp',
  },
  {
    id: 'ap-2',
    agent_identity_id: 'ai-2',
    capability_id: 'cap-2',
    server_id: 'srv-2',
    request_params: {},
    status: 'approved',
    approver_id: 'usr-1',
    requested_at: '2025-01-14T08:00:00Z',
    resolved_at: '2025-01-14T09:00:00Z',
    agent_name: 'agent-beta',
    capability_name: 'deploy',
    server_name: 'aws-mcp',
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchApprovals.mockResolvedValue({
    items: mockApprovals,
    pagination: { total: 2, has_more: false, per_page: 50 },
  })
})

describe('ApprovalsPage', () => {
  it('renders approval table with agent, capability, status columns', async () => {
    renderWithProviders(<ApprovalsPage />)
    await waitFor(() => {
      expect(screen.getByText('agent-alpha')).toBeInTheDocument()
    })
    expect(screen.getByText('code-review')).toBeInTheDocument()
    expect(screen.getByText('pending')).toBeInTheDocument()
    expect(screen.getByText('agent-beta')).toBeInTheDocument()
    expect(screen.getByText('deploy')).toBeInTheDocument()
    expect(screen.getByText('approved')).toBeInTheDocument()
  })

  it('review side panel shows request details (agent, capability, server)', async () => {
    renderWithProviders(<ApprovalsPage />)
    const reviewButtons = await screen.findAllByText('Review')
    await userEvent.click(reviewButtons[0])
    expect(screen.getByText('Review Approval Request')).toBeInTheDocument()
    expect(screen.getAllByText('agent-alpha').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('code-review').length).toBe(2)
    expect(screen.getByText('github-mcp')).toBeInTheDocument()
  })

  it('approve button calls resolveApproval(id, "approved")', async () => {
    mockResolveApproval.mockResolvedValue({} as any)
    renderWithProviders(<ApprovalsPage />)
    const reviewButtons = await screen.findAllByText('Review')
    await userEvent.click(reviewButtons[0])
    await userEvent.click(screen.getByText('Approve'))
    await waitFor(() => {
      expect(mockResolveApproval).toHaveBeenCalledWith('ap-1', 'approved', '')
    })
  })

  it('deny button calls resolveApproval(id, "denied")', async () => {
    mockResolveApproval.mockResolvedValue({} as any)
    renderWithProviders(<ApprovalsPage />)
    const reviewButtons = await screen.findAllByText('Review')
    await userEvent.click(reviewButtons[0])
    await userEvent.click(screen.getByText('Deny'))
    await waitFor(() => {
      expect(mockResolveApproval).toHaveBeenCalledWith('ap-1', 'denied', '')
    })
  })
})
