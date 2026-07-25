import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PageState } from './PageState'

describe('PageState', () => {
  const loadingQuery = { isLoading: true as const, data: undefined, error: null, refetch: vi.fn() }
  const errorQuery = { isLoading: false as const, data: undefined, error: new Error('API timeout'), refetch: vi.fn() }
  const nullQuery = { isLoading: false as const, data: null, error: null, refetch: vi.fn() }
  const populatedQuery = { isLoading: false as const, data: ['a', 'b'], error: null, refetch: vi.fn() }

  it('loading state shows skeleton', () => {
    render(<PageState query={loadingQuery}>{() => <div>content</div>}</PageState>)
    expect(screen.queryByText('content')).toBeNull()
  })

  it('error state shows message and retry', () => {
    render(<PageState query={errorQuery}>{() => <div>content</div>}</PageState>)
    expect(screen.getByText('Error')).toBeInTheDocument()
    expect(screen.getByText('API timeout')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('retry button calls refetch', async () => {
    const { rerender } = render(<PageState query={errorQuery}>{() => <div>content</div>}</PageState>)
    const { default: userEvent } = await import('@testing-library/user-event')
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(errorQuery.refetch).toHaveBeenCalledTimes(1)
    rerender(<PageState query={loadingQuery}>{() => <div>content</div>}</PageState>)
  })

  it('empty state when data is null', () => {
    render(<PageState query={nullQuery}>{() => <div>content</div>}</PageState>)
    expect(screen.getByText('No data available')).toBeInTheDocument()
  })

  it('renders children with populated data', () => {
    render(<PageState query={populatedQuery}>{data => <div>{data.join(',')}</div>}</PageState>)
    expect(screen.getByText('a,b')).toBeInTheDocument()
  })
})
