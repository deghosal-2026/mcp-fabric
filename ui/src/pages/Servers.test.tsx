import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ServersPage } from './Servers'

vi.mock('../api/client', () => ({
  fetchServers: vi.fn(),
  registerServer: vi.fn(),
}))

import { fetchServers, registerServer } from '../api/client'

const mockServers = {
  items: [
    { id: 's1', name: 'server-alpha', endpoint: 'http://a:3001', health_status: 'healthy', trust_level: 'trusted', owner_team: 'platform', labels: ['prod'], tools: [{ id: 't1', tool_name: 'search' }] },
    { id: 's2', name: 'server-beta', endpoint: 'http://b:3001', health_status: 'degraded', trust_level: 'unreviewed', owner_team: 'data', labels: ['dev'], tools: [] },
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
          <ServersPage />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(fetchServers).mockResolvedValue(mockServers)
  vi.mocked(registerServer).mockResolvedValue({ id: 's3', name: 'server-gamma', endpoint: 'http://c:3001', owner_team: 'security', labels: ['staging'] } as any)
})

describe('ServersPage', () => {
  it('renders server table with name and endpoint columns', async () => {
    renderWithProviders()
    await waitFor(() => {
      expect(screen.getByText('server-alpha')).toBeInTheDocument()
      expect(screen.getByText('http://a:3001')).toBeInTheDocument()
      expect(screen.getByText('server-beta')).toBeInTheDocument()
      expect(screen.getByText('http://b:3001')).toBeInTheDocument()
    })
  })

  it('register modal opens, form submits with correct data', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await user.click(screen.getByText('Register Server'))
    expect(screen.getByText('Register MCP Server')).toBeInTheDocument()

    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[1], 'server-gamma')
    await user.type(inputs[2], 'http://c:3001')
    await user.type(inputs[3], 'security')
    await user.type(inputs[4], 'staging,test')

    await user.click(screen.getByText('Save'))

    await waitFor(() => {
      expect(registerServer).toHaveBeenCalledWith({
        name: 'server-gamma',
        endpoint: 'http://c:3001',
        owner_team: 'security',
        labels: ['staging', 'test'],
      })
    })
  })

  it('labels split from comma-separated string to array', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await user.click(screen.getByText('Register Server'))

    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[1], 'server-gamma')
    await user.type(inputs[2], 'http://c:3001')
    await user.type(inputs[4], '  a , b , c  ')
    await user.click(screen.getByText('Save'))

    await waitFor(() => {
      expect(registerServer).toHaveBeenCalledWith(
        expect.objectContaining({ labels: ['a', 'b', 'c'] }),
      )
    })
  })

  it('filter change triggers query refetch', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await waitFor(() => expect(screen.getByText('server-alpha')).toBeInTheDocument())

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'healthy')

    await waitFor(() => {
      expect(fetchServers).toHaveBeenLastCalledWith(
        expect.objectContaining({ health_status: 'healthy', per_page: '50' }),
      )
    })
  })
})
