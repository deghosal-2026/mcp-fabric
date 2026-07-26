import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PackBreadthWarning } from './PackBreadthWarning'

vi.mock('../../api/client', () => ({
  fetchPackSecurityMetrics: vi.fn(),
}))

import { fetchPackSecurityMetrics } from '../../api/client'

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('PackBreadthWarning', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows nothing on error', async () => {
    vi.mocked(fetchPackSecurityMetrics).mockRejectedValue(new Error('fail'))
    const { container } = render(<PackBreadthWarning packId="p1" />, { wrapper: Wrapper })
    await vi.waitFor(() => {
      expect(container.textContent).toBe('')
    })
  })

  it('shows badge with full tier label for 100% catch rate', async () => {
    vi.mocked(fetchPackSecurityMetrics).mockResolvedValue({
      id: 'p1',
      name: 'test',
      resource_count: 512,
      total_resources_in_domain: 512,
      implied_catch_rate: 1.0,
      warning_tier: 'full',
    })
    render(<PackBreadthWarning packId="p1" />, { wrapper: Wrapper })
    expect(await screen.findByText('Full coverage — all domain resources included')).toBeInTheDocument()
  })

  it('shows low badge for low catch rate', async () => {
    vi.mocked(fetchPackSecurityMetrics).mockResolvedValue({
      id: 'p2',
      name: 'test',
      resource_count: 500,
      total_resources_in_domain: 512,
      implied_catch_rate: 0.02,
      warning_tier: 'low',
    })
    render(<PackBreadthWarning packId="p2" />, { wrapper: Wrapper })
    expect(await screen.findByText('Low coverage — catch rate < 50%')).toBeInTheDocument()
  })

  it('shows banner variant with catch rate details', async () => {
    vi.mocked(fetchPackSecurityMetrics).mockResolvedValue({
      id: 'p3',
      name: 'test',
      resource_count: 64,
      total_resources_in_domain: 512,
      implied_catch_rate: 0.8766,
      warning_tier: 'moderate',
    })
    render(<PackBreadthWarning packId="p3" variant="banner" />, { wrapper: Wrapper })
    expect(await screen.findByText('Moderate coverage — catch rate ≥ 87%')).toBeInTheDocument()
    expect(screen.getByText(/87.7%/)).toBeInTheDocument()
    expect(screen.getByText(/64 of 512/)).toBeInTheDocument()
  })
})
