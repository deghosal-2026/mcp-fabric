import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Badge } from './Badge'

describe('Badge', () => {
  it('renders label text', () => {
    render(<Badge label="trusted" />)
    expect(screen.getByText('trusted')).toBeInTheDocument()
  })

  it('applies correct color class for known variant', () => {
    render(<Badge label="trusted" />)
    const span = screen.getByText('trusted')
    expect(span.className).toContain('bg-green-100')
    expect(span.className).toContain('text-green-800')
  })

  it('falls back to gray for unknown variant', () => {
    render(<Badge label="unknown-status" />)
    const span = screen.getByText('unknown-status')
    expect(span.className).toContain('bg-gray-100')
  })

  it('variant prop overrides label for color selection', () => {
    render(<Badge label="custom" variant="trusted" />)
    const span = screen.getByText('custom')
    expect(span.className).toContain('bg-green-100')
  })

  it('applies truncate class for long labels', () => {
    render(<Badge label="a very long label that should be truncated in the ui" />)
    const span = screen.getByText('a very long label that should be truncated in the ui')
    expect(span.className).toContain('truncate')
    expect(span.className).toContain('max-w-[200px]')
  })
})
