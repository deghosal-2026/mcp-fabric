import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Modal } from './Modal'

describe('Modal', () => {
  it('renders nothing when closed', () => {
    render(<Modal open={false} onClose={vi.fn()} title="Edit Server"><p>Content</p></Modal>)
    expect(screen.queryByText('Edit Server')).toBeNull()
  })

  it('renders content when open', () => {
    render(<Modal open={true} onClose={vi.fn()} title="Edit Server"><p>Form fields</p></Modal>)
    expect(screen.getByText('Edit Server')).toBeInTheDocument()
    expect(screen.getByText('Form fields')).toBeInTheDocument()
  })

  it('closes on Escape key', async () => {
    const onClose = vi.fn()
    render(<Modal open={true} onClose={onClose} title="Test"><p>Content</p></Modal>)
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('confirm button disabled when confirmDisabled is true', () => {
    render(<Modal open={true} onClose={vi.fn()} onConfirm={vi.fn()} confirmDisabled={true} confirmLabel="Save"><p>Content</p></Modal>)
    expect(screen.getByRole('button', { name: /save/i })).toBeDisabled()
  })

  it('confirm button enabled by default', () => {
    render(<Modal open={true} onClose={vi.fn()} onConfirm={vi.fn()} confirmLabel="Save"><p>Content</p></Modal>)
    expect(screen.getByRole('button', { name: /save/i })).not.toBeDisabled()
  })

  it('loading state shows Loading... text', () => {
    render(<Modal open={true} onClose={vi.fn()} onConfirm={vi.fn()} loading={true} confirmLabel="Save"><p>Content</p></Modal>)
    expect(screen.getByRole('button', { name: /loading/i })).toBeInTheDocument()
  })
})
