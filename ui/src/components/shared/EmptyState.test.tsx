import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders message text', () => {
    render(<EmptyState message="No servers found" />)
    expect(screen.getByText('No servers found')).toBeInTheDocument()
  })

  it('action button fires onAction callback', async () => {
    const onAction = vi.fn()
    render(<EmptyState message="No servers" actionLabel="Add Server" onAction={onAction} />)
    await userEvent.click(screen.getByRole('button', { name: /add server/i }))
    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('no action button when onAction omitted', () => {
    render(<EmptyState message="No results" />)
    expect(screen.queryByRole('button')).toBeNull()
  })
})
