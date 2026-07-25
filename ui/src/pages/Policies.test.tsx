import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { PoliciesPage } from './Policies'

vi.mock('../api/client', () => ({
  fetchPolicies: vi.fn(),
  deployPolicy: vi.fn(),
}))

import { fetchPolicies, deployPolicy } from '../api/client'

const mockPolicies = [
  { id: 'p1', version: '1.0.0', deployed_at: '2026-07-24T10:00:00Z' },
  { id: 'p2', version: '2.0.0', deployed_at: '2026-07-24T12:00:00Z' },
]

function renderWithProviders() {
  const testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={testQueryClient}>
      <ToastProvider>
        <BrowserRouter>
          <PoliciesPage />
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(fetchPolicies).mockResolvedValue(mockPolicies)
  vi.mocked(deployPolicy).mockResolvedValue({ version: '3.0.0' })
})

describe('PoliciesPage', () => {
  it('renders deployed policy list with version and date', async () => {
    renderWithProviders()
    await waitFor(() => {
      expect(screen.getByText('v1.0.0')).toBeInTheDocument()
      expect(screen.getByText('v2.0.0')).toBeInTheDocument()
    })
  })

  it('New Policy opens editor modal with textarea', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await user.click(screen.getByText('New Policy'))
    expect(screen.getByText('Edit Rego Policy')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/package fabric.policy/)).toBeInTheDocument()
  })

  it('Deploy submits and invalidates policies query', async () => {
    const user = userEvent.setup()
    renderWithProviders()

    await user.click(screen.getByText('New Policy'))

    const textarea = screen.getByPlaceholderText(/package fabric.policy/)
    await user.type(textarea, 'package fabric.policy\n\ndefault allow := false')

    await user.click(screen.getByText('Deploy'))

    await waitFor(() => {
      expect(deployPolicy).toHaveBeenCalledWith('package fabric.policy\n\ndefault allow := false')
    })

    await waitFor(() => {
      expect(fetchPolicies).toHaveBeenCalledTimes(2)
    })
  })
})
