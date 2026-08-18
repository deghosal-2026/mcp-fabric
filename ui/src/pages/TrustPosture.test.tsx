import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { TrustPosturePage } from './TrustPosture'
import { fetchServers, fetchAgentClasses, setTrustAssignment, fetchPackBreadth } from '../api/client'

vi.mock('../api/client', () => ({
  fetchServers: vi.fn(),
  fetchAgentClasses: vi.fn(),
  setTrustAssignment: vi.fn(),
  fetchPackBreadth: vi.fn(),
}))

const mockFetchServers = vi.mocked(fetchServers)
const mockFetchAgentClasses = vi.mocked(fetchAgentClasses)
const mockSetTrustAssignment = vi.mocked(setTrustAssignment)
const mockFetchPackBreadth = vi.mocked(fetchPackBreadth)

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

const mockServers = {
  items: [
    {
      id: 'srv-1',
      name: 'GitHub MCP',
      endpoint: 'https://github.mcp.example.com',
      owner_team: 'eng',
      labels: [],
      trust_level: 'trusted' as const,
      health_status: 'healthy' as const,
      team_namespace: 'eng',
      decommissioned_at: null,
      created_at: '2025-01-01T00:00:00Z',
    },
    {
      id: 'srv-2',
      name: 'AWS MCP',
      endpoint: 'https://aws.mcp.example.com',
      owner_team: 'platform',
      labels: [],
      trust_level: 'unreviewed' as const,
      health_status: 'healthy' as const,
      team_namespace: 'platform',
      decommissioned_at: null,
      created_at: '2025-01-02T00:00:00Z',
    },
  ],
  pagination: { total: 2, has_more: false, per_page: 200 },
}

const mockClasses = [
  { id: 'cls-1', name: 'developer-agent', description: 'Dev agent', team_namespace: 'eng' },
  { id: 'cls-2', name: 'data-agent', description: 'Data agent', team_namespace: 'data' },
]

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchServers.mockResolvedValue(mockServers as any)
  mockFetchAgentClasses.mockResolvedValue(mockClasses as any)
  mockSetTrustAssignment.mockResolvedValue({} as any)
  mockFetchPackBreadth.mockResolvedValue([])
})

describe('TrustPosturePage', () => {
  it('renders server cards', async () => {
    renderWithProviders(<TrustPosturePage />)
    await waitFor(() => {
      expect(screen.getByText('GitHub MCP')).toBeInTheDocument()
    })
    expect(screen.getByText('AWS MCP')).toBeInTheDocument()
    expect(screen.getByText('https://github.mcp.example.com')).toBeInTheDocument()
    expect(screen.getByText('https://aws.mcp.example.com')).toBeInTheDocument()
  })

  it('agent class selector shows fetched classes', async () => {
    renderWithProviders(<TrustPosturePage />)
    await waitFor(() => {
      expect(screen.getByText('developer-agent')).toBeInTheDocument()
    })
    expect(screen.getByText('data-agent')).toBeInTheDocument()
  })

  it('trust level change calls setTrustAssignment with selected class ID', async () => {
    renderWithProviders(<TrustPosturePage />)
    const comboboxes = await screen.findAllByRole('combobox')
    const classSelect = comboboxes[0]
    await userEvent.selectOptions(classSelect, 'cls-1')

    await userEvent.selectOptions(comboboxes[1], 'restricted')

    await waitFor(() => {
      expect(mockSetTrustAssignment).toHaveBeenCalledWith('cls-1', 'srv-1', 'restricted')
    })
  })

  it('no mutation when no class selected (empty string guard)', async () => {
    renderWithProviders(<TrustPosturePage />)
    await waitFor(() => {
      expect(screen.getByText('GitHub MCP')).toBeInTheDocument()
    })

    const comboboxes = screen.getAllByRole('combobox')
    await userEvent.selectOptions(comboboxes[1], 'restricted')

    await waitFor(() => {
      expect(mockSetTrustAssignment).not.toHaveBeenCalled()
    })
  })

  it('optimistic: dropdown shows new value via pendingChanges', async () => {
    let resolveMutation!: (value: unknown) => void
    mockSetTrustAssignment.mockReturnValue(
      new Promise(resolve => { resolveMutation = resolve })
    )

    renderWithProviders(<TrustPosturePage />)
    const comboboxes = await screen.findAllByRole('combobox')
    const classSelect = comboboxes[0]
    await userEvent.selectOptions(classSelect, 'cls-1')

    await userEvent.selectOptions(comboboxes[1], 'restricted')

    expect(comboboxes[1]).toHaveValue('restricted')

    resolveMutation({})
    await waitFor(() => {
      expect(mockSetTrustAssignment).toHaveBeenCalledWith('cls-1', 'srv-1', 'restricted')
    })
  })
})
