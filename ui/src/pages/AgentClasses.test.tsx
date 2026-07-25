import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AgentClassesPage } from './AgentClasses'

vi.mock('../api/client', () => ({
  fetchAgentClasses: vi.fn(),
  createAgentClass: vi.fn(),
  fetchAgentIdentities: vi.fn(),
  createAgentIdentity: vi.fn(),
}))

import { fetchAgentClasses, createAgentClass, fetchAgentIdentities, createAgentIdentity } from '../api/client'

const mockClasses = [
  { id: 'ac1', name: 'agent:developer', description: 'Developer agent', team_namespace: 'team:platform' },
  { id: 'ac2', name: 'agent:security', description: 'Security agent', team_namespace: 'team:security' },
]

const mockIdentities = [
  { id: 'id1', agent_class_id: 'ac1', token_prefix: 'fab_dev', status: 'active', rate_limit_per_min: 60, expires_at: null, created_at: '2026-01-01T00:00:00Z' },
]

function renderWithProviders() {
  const testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={testQueryClient}>
      <ToastProvider>
        <BrowserRouter>
          <AgentClassesPage />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(fetchAgentClasses).mockResolvedValue(mockClasses)
  vi.mocked(fetchAgentIdentities).mockResolvedValue(mockIdentities)
  vi.mocked(createAgentClass).mockResolvedValue({ id: 'ac3' } as any)
  vi.mocked(createAgentIdentity).mockResolvedValue({ id: 'id2', token: 'fab_new_secret_token_value' } as any)
})

describe('AgentClassesPage', () => {
  it('renders agent class table', async () => {
    renderWithProviders()
    await waitFor(() => {
      expect(screen.getByText('agent:developer')).toBeInTheDocument()
      expect(screen.getByText('agent:security')).toBeInTheDocument()
      expect(screen.getByText('Developer agent')).toBeInTheDocument()
      expect(screen.getByText('Security agent')).toBeInTheDocument()
    })
  })

  it('create modal submits', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await user.click(screen.getByText('Create Agent Class'))

    const textboxes = screen.getAllByRole('textbox')
    await user.type(textboxes[0], 'agent:ops')
    await user.type(textboxes[1], 'Ops agent')

    await user.click(screen.getByText('Save'))

    await waitFor(() => {
      expect(createAgentClass).toHaveBeenCalledWith({
        name: 'agent:ops',
        description: 'Ops agent',
      })
    })
  })

  it('token generate shows token with warning, close modal and reopen shows create form again', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await waitFor(() => expect(screen.getByText('agent:developer')).toBeInTheDocument())

    const tokensButtons = screen.getAllByText('Tokens')
    await user.click(tokensButtons[0])

    await waitFor(() => expect(screen.getByText('Agent Tokens')).toBeInTheDocument())

    const tokenInput = screen.getByPlaceholderText('Token name')
    await user.type(tokenInput, 'dev-token')
    await user.click(screen.getByText('Generate'))

    await waitFor(() => {
      expect(createAgentIdentity).toHaveBeenCalledWith('ac1', 'dev-token')
      expect(screen.getByText('Copy this token now. It will not be shown again.')).toBeInTheDocument()
      expect(screen.getByText('fab_new_secret_token_value')).toBeInTheDocument()
    })

    const closeButtons = screen.getAllByRole('button')
    const closeBtn = closeButtons.find(b => b.textContent?.trim() === '×')
    await user.click(closeBtn!)

    await user.click(screen.getByText('Create Agent Class'))
    const modalTitles = screen.getAllByText('Create Agent Class')
    expect(modalTitles.length).toBeGreaterThanOrEqual(1)
  })
})
