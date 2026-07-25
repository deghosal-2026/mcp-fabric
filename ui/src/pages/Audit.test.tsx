import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuditPage } from './Audit'

vi.mock('../api/client', () => ({
  fetchAuditEvents: vi.fn(),
  exportAudit: vi.fn(),
}))

import { fetchAuditEvents, exportAudit } from '../api/client'

const mockAudit = {
  items: [
    { id: 'e1', event_type: 'policy_change', actor_id: 'admin@co', actor_type: 'admin', target_type: 'policy', details: {}, created_at: '2026-07-24T10:00:00Z' },
    { id: 'e2', event_type: 'server_registered', actor_id: 'bot', actor_type: 'agent', target_type: 'server', details: {}, created_at: '2026-07-24T11:00:00Z' },
  ],
  pagination: { total: 2, has_more: false, per_page: 50 },
}

function renderWithProviders() {
  const testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={testQueryClient}>
      <ToastProvider>
        <BrowserRouter>
          <AuditPage />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(fetchAuditEvents).mockResolvedValue(mockAudit)
  vi.mocked(exportAudit).mockResolvedValue({ export_id: 'exp-123' })
})

describe('AuditPage', () => {
  it('renders audit event table', async () => {
    renderWithProviders()
    await waitFor(() => {
      expect(screen.getByText('policy_change')).toBeInTheDocument()
      expect(screen.getByText('server_registered')).toBeInTheDocument()
      expect(screen.getByText('admin@co')).toBeInTheDocument()
      expect(screen.getByText('bot')).toBeInTheDocument()
    })
  })

  it('Export button calls exportAudit', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await waitFor(() => expect(screen.getByText('policy_change')).toBeInTheDocument())

    await user.click(screen.getByText('Export'))

    await waitFor(() => {
      expect(exportAudit).toHaveBeenCalledTimes(1)
      expect(exportAudit).toHaveBeenCalledWith({})
    })
  })

  it('filter by event type updates query key', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await waitFor(() => expect(screen.getByText('policy_change')).toBeInTheDocument())

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'policy_change')

    await waitFor(() => {
      expect(fetchAuditEvents).toHaveBeenLastCalledWith(
        expect.objectContaining({ event_type: 'policy_change', per_page: '50' }),
      )
    })
  })
})
