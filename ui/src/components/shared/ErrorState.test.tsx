import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { ErrorState } from './ErrorState'

describe('ErrorState', () => {
  it('renders error message text', () => {
    render(<ErrorState message="Database connection failed" />)
    expect(screen.getByText('Database connection failed')).toBeInTheDocument()
  })

  it('retry button fires onRetry callback', async () => {
    const onRetry = vi.fn()
    render(<ErrorState message="Failed" onRetry={onRetry} />)
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('no retry button when onRetry omitted', () => {
    render(<ErrorState message="Failed" />)
    expect(screen.queryByRole('button')).toBeNull()
  })
})
