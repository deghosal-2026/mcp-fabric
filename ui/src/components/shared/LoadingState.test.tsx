import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { LoadingState } from './LoadingState'

describe('LoadingState', () => {
  it('renders default 3 skeleton rows', () => {
    render(<LoadingState />)
    const rows = screen.getByTestId('loading-state').children
    expect(rows).toHaveLength(3)
  })

  it('renders custom number of skeleton rows', () => {
    render(<LoadingState rows={5} />)
    const rows = screen.getByTestId('loading-state').children
    expect(rows).toHaveLength(5)
  })

  it('container has pulse animation class', () => {
    render(<LoadingState />)
    const container = screen.getByTestId('loading-state')
    expect(container.className).toContain('animate-pulse')
  })
})
