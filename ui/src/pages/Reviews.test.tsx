import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { ReviewsPage } from './Reviews'
import {
  fetchStaleMappings,
  fetchQueueSummary,
  bulkRetireMappings,
  fetchServer,
  fetchCapability,
} from '../api/client'

vi.mock('../api/client', () => ({
  fetchStaleMappings: vi.fn(),
  fetchQueueSummary: vi.fn(),
  bulkRetireMappings: vi.fn(),
  fetchServer: vi.fn(),
  fetchCapability: vi.fn(),
  queryClient: { invalidateQueries: vi.fn() },
}))

const mockFetchStale = vi.mocked(fetchStaleMappings)
const mockFetchSummary = vi.mocked(fetchQueueSummary)
const mockBulkRetire = vi.mocked(bulkRetireMappings)
const mockFetchServer = vi.mocked(fetchServer)
const mockFetchCapability = vi.mocked(fetchCapability)

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

const mockMappings = [
  {
    id: 'm-1',
    capability_id: 'cap-1',
    server_id: 'srv-1',
    tool_name: 'search',
    is_primary: true,
    routing_weight: 1.0,
    tool_schema_digest: 'abc123def456',
    status: 'stale',
    failure_class: 'drifted',
    pending_since: '2026-08-16T10:00:00Z',
  },
  {
    id: 'm-2',
    capability_id: 'cap-2',
    server_id: 'srv-2',
    tool_name: 'read',
    is_primary: true,
    routing_weight: 1.0,
    tool_schema_digest: 'xyz789',
    status: 'stale',
    failure_class: 'unreachable',
    pending_since: '2026-08-16T09:00:00Z',
  },
]

const mockSummary = {
  total: 2,
  critical: 1,
  unreachable: 1,
  by_failure_class: { drifted: 1, unreachable: 1 },
}

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchStale.mockResolvedValue(mockMappings as any)
  mockFetchSummary.mockResolvedValue(mockSummary as any)
  mockFetchServer.mockResolvedValue({ name: 'Server A' } as any)
  mockFetchCapability.mockResolvedValue({ name: 'code:search' } as any)
})

describe('ReviewsPage', () => {
  it('renders queue summary with critical vs unreachable tallies', async () => {
    renderWithProviders(<ReviewsPage />)
    await waitFor(() => {
      expect(screen.getByText('Total')).toBeInTheDocument()
    })
    expect(screen.getByText('Critical')).toBeInTheDocument()
    // Summary label "Unreachable" + a failure badge "Unreachable" both render.
    expect(screen.getAllByText('Unreachable').length).toBeGreaterThanOrEqual(1)
    // Total=2
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders failure class badges for each mapping', async () => {
    renderWithProviders(<ReviewsPage />)
    await screen.findByText('Drifted')
    expect(screen.getByText('Unreachable')).toBeInTheDocument()
  })

  it('shows bulk-retire button when unreachable items exist', async () => {
    renderWithProviders(<ReviewsPage />)
    const btn = await screen.findByText(/Retire all unreachable/)
    expect(btn).toBeInTheDocument()
  })

  it('calls bulkRetireMappings when retire-all-unreachable clicked', async () => {
    mockBulkRetire.mockResolvedValue({ retired: 1, failure_class: 'unreachable' } as any)
    renderWithProviders(<ReviewsPage />)
    const btn = await screen.findByText(/Retire all unreachable/)
    await userEvent.click(btn)
    await waitFor(() => {
      expect(mockBulkRetire).toHaveBeenCalledWith({ failure_class: 'unreachable' })
    })
  })

  it('filter select calls fetchStaleMappings with failure_class', async () => {
    renderWithProviders(<ReviewsPage />)
    await screen.findByText('Drifted')
    // Initial load with no filter
    expect(mockFetchStale).toHaveBeenCalledWith(undefined)
    // Select "drifted" filter
    const select = screen.getByLabelText('Filter:')
    await userEvent.selectOptions(select, 'drifted')
    await waitFor(() => {
      expect(mockFetchStale).toHaveBeenCalledWith('drifted')
    })
  })
})
