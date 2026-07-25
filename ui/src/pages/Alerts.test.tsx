import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { AlertsPage } from './Alerts'
import { fetchAlerts, acknowledgeAlert } from '../api/client'

vi.mock('../api/client', () => ({
  fetchAlerts: vi.fn(),
  acknowledgeAlert: vi.fn(),
}))

const mockFetchAlerts = vi.mocked(fetchAlerts)
const mockAcknowledgeAlert = vi.mocked(acknowledgeAlert)

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

const mockAlerts = {
  items: [
    {
      id: 'a-1',
      rule_id: 'r-1',
      message: 'High CPU usage detected',
      details: {},
      fired_at: '2025-01-15T10:00:00Z',
      acknowledged_at: null,
      acknowledged_by: null,
      rule_name: 'CPU Monitor',
    },
    {
      id: 'a-2',
      rule_id: 'r-2',
      message: 'Memory threshold exceeded',
      details: {},
      fired_at: '2025-01-15T09:00:00Z',
      acknowledged_at: '2025-01-15T09:30:00Z',
      acknowledged_by: 'usr-1',
      rule_name: 'Memory Monitor',
    },
  ],
  pagination: { total: 2, has_more: false, per_page: 50 },
}

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchAlerts.mockResolvedValue(mockAlerts as any)
})

describe('AlertsPage', () => {
  it('renders alert table with message and rule columns', async () => {
    renderWithProviders(<AlertsPage />)
    await waitFor(() => {
      expect(screen.getByText('High CPU usage detected')).toBeInTheDocument()
    })
    expect(screen.getByText('CPU Monitor')).toBeInTheDocument()
    expect(screen.getByText('Memory threshold exceeded')).toBeInTheDocument()
    expect(screen.getByText('Memory Monitor')).toBeInTheDocument()
  })

  it('acknowledge button calls acknowledgeAlert', async () => {
    mockAcknowledgeAlert.mockResolvedValue({} as any)
    renderWithProviders(<AlertsPage />)
    const ackButton = await screen.findByText('Acknowledge')
    await userEvent.click(ackButton)
    await waitFor(() => {
      expect(mockAcknowledgeAlert).toHaveBeenCalledWith('a-1')
    })
  })
})
