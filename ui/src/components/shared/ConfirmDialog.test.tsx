import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { ConfirmDialog } from './Modal'

describe('ConfirmDialog', () => {
  it('renders title and message', () => {
    render(<ConfirmDialog open={true} title="Delete Server" message="Are you sure?" onConfirm={vi.fn()} onClose={vi.fn()} />)
    expect(screen.getByText('Delete Server')).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
  })

  it('cancel fires onClose', async () => {
    const onClose = vi.fn()
    const onConfirm = vi.fn()
    render(<ConfirmDialog open={true} title="Delete" message="Sure?" onConfirm={onConfirm} onClose={onClose} />)
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('confirm fires onConfirm', async () => {
    const onClose = vi.fn()
    const onConfirm = vi.fn()
    render(<ConfirmDialog open={true} title="Delete" message="Sure?" onConfirm={onConfirm} onClose={onClose} />)
    await userEvent.click(screen.getByRole('button', { name: /delete/i }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(onClose).not.toHaveBeenCalled()
  })
})
