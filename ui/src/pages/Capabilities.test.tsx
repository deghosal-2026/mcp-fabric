import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CapabilitiesPage } from './Capabilities'

vi.mock('../api/client', () => ({
  fetchCapabilities: vi.fn(),
  createCapability: vi.fn(),
  deprecateCapability: vi.fn(),
}))

import { fetchCapabilities, createCapability, deprecateCapability } from '../api/client'

const mockCapabilities = {
  items: [
    { id: 'c1', name: 'code:search', domain: 'code', description: 'Search code', status: 'active' },
    { id: 'c2', name: 'knowledge:retrieve', domain: 'knowledge', description: 'Retrieve knowledge', status: 'deprecated' },
  ],
  pagination: { total: 2, has_more: false, per_page: 100 },
}

function renderWithProviders() {
  const testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={testQueryClient}>
      <ToastProvider>
        <BrowserRouter>
          <CapabilitiesPage />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(fetchCapabilities).mockResolvedValue(mockCapabilities)
  vi.mocked(createCapability).mockResolvedValue({ id: 'c3' } as any)
  vi.mocked(deprecateCapability).mockResolvedValue({ id: 'c1', status: 'deprecated' } as any)
})

describe('CapabilitiesPage', () => {
  it('renders capability table with name, domain, status', async () => {
    renderWithProviders()
    await waitFor(() => {
      expect(screen.getByText('code:search')).toBeInTheDocument()
      expect(screen.getByText('code')).toBeInTheDocument()
      expect(screen.getByText('knowledge:retrieve')).toBeInTheDocument()
      expect(screen.getByText('knowledge')).toBeInTheDocument()
    })
  })

  it('create modal submits with name, domain, description', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await user.click(screen.getByText('Create Capability'))
    const modalTitles = screen.getAllByText('Create Capability')
    expect(modalTitles.length).toBeGreaterThanOrEqual(1)

    const textboxes = screen.getAllByRole('textbox')
    await user.type(textboxes[1], 'deploy:rollback')
    await user.type(textboxes[2], 'deployment')
    await user.type(textboxes[3], 'Rollback deployments')

    await user.click(screen.getByText('Save'))

    await waitFor(() => {
      expect(createCapability).toHaveBeenCalledWith({
        name: 'deploy:rollback',
        domain: 'deployment',
        description: 'Rollback deployments',
      })
    })
  })

  it('deprecate confirm dialog opens and calls deprecateCapability with 14 grace days', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await waitFor(() => expect(screen.getByText('code:search')).toBeInTheDocument())

    const deprecateButtons = screen.getAllByText('Deprecate')
    await user.click(deprecateButtons[0])

    expect(screen.getByText(/Are you sure you want to deprecate/)).toBeInTheDocument()
    expect(screen.getByText(/14 days/)).toBeInTheDocument()

    const modalDeprecate = screen.getAllByText('Deprecate')
    await user.click(modalDeprecate[modalDeprecate.length - 1])

    await waitFor(() => {
      expect(deprecateCapability).toHaveBeenCalledWith('c1', 14)
    })
  })

  it('filter change updates query key', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await waitFor(() => expect(screen.getByText('code:search')).toBeInTheDocument())

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'code')

    await waitFor(() => {
      expect(fetchCapabilities).toHaveBeenLastCalledWith(
        expect.objectContaining({ domain: 'code', per_page: '100' }),
      )
    })
  })
})
