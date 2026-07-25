import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { FilterBar } from './FilterBar'

describe('FilterBar', () => {
  it('renders dropdown for each filter group', () => {
    render(<FilterBar
      filters={[{ key: 'status', label: 'Status', options: [{ value: 'active', label: 'Active' }] }]}
      onFilter={vi.fn()}
    />)
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('selecting a value fires onFilter', async () => {
    const onFilter = vi.fn()
    render(<FilterBar
      filters={[{ key: 'status', label: 'Status', options: [{ value: 'active', label: 'Active' }] }]}
      onFilter={onFilter}
    />)
    const { default: userEvent } = await import('@testing-library/user-event')
    await userEvent.selectOptions(screen.getByRole('combobox'), 'active')
    expect(onFilter).toHaveBeenCalledWith({ status: 'active', q: '' })
  })

  it('renders search input when searchPlaceholder provided', () => {
    render(<FilterBar
      filters={[]}
      onFilter={vi.fn()}
      searchPlaceholder="Search servers..."
    />)
    expect(screen.getByPlaceholderText('Search servers...')).toBeInTheDocument()
  })

  it('clear all button appears when filter is active', async () => {
    const onFilter = vi.fn()
    render(<FilterBar
      filters={[{ key: 'status', label: 'Status', options: [{ value: 'active', label: 'Active' }] }]}
      onFilter={onFilter}
    />)
    const { default: userEvent } = await import('@testing-library/user-event')
    await userEvent.selectOptions(screen.getByRole('combobox'), 'active')
    expect(screen.getByText('Clear all')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Clear all'))
    expect(onFilter).toHaveBeenLastCalledWith({})
  })
})
