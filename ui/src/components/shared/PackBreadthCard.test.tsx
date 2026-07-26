import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PackBreadthCard } from './PackBreadthCard'

vi.mock('../../api/client', () => ({
  fetchPackBreadth: vi.fn(),
}))

import { fetchPackBreadth } from '../../api/client'

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('PackBreadthCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows empty state when no data', async () => {
    vi.mocked(fetchPackBreadth).mockResolvedValue([])
    render(<PackBreadthCard />, { wrapper: Wrapper })
    expect(await screen.findByText('No agent classes with pack assignments yet.')).toBeInTheDocument()
  })

  it('renders rows with catch rate and risk badge', async () => {
    vi.mocked(fetchPackBreadth).mockResolvedValue([
      { agent_class_id: 'c1', agent_class_name: 'agent:dev', pack_count: 2, resources_covered: 10, total_resources_in_domain: 512, catch_rate: 0.978 },
      { agent_class_id: 'c2', agent_class_name: 'agent:ops', pack_count: 1, resources_covered: 500, total_resources_in_domain: 512, catch_rate: 0.02 },
    ])
    render(<PackBreadthCard />, { wrapper: Wrapper })
    expect(await screen.findByText('agent:dev')).toBeInTheDocument()
    expect(screen.getByText('agent:ops')).toBeInTheDocument()
    expect(screen.getByText('97.8%')).toBeInTheDocument()
    expect(screen.getByText('2.0%')).toBeInTheDocument()
  })
})
