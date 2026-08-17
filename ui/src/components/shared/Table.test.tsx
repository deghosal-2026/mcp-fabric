import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Table } from './Table'
import type { LegacyColumnDef as ColumnDef } from '@tanstack/react-table/legacy'

interface TestItem { id: string; name: string; status: string }

const columns: ColumnDef<TestItem>[] = [
  { header: 'Name', accessorKey: 'name' },
  { header: 'Status', accessorKey: 'status' },
]

const data: TestItem[] = [
  { id: '1', name: 'Server A', status: 'healthy' },
  { id: '2', name: 'Server B', status: 'degraded' },
  { id: '3', name: 'Server C', status: 'unhealthy' },
]

describe('Table', () => {
  it('renders column headers', () => {
    render(<Table data={[]} columns={columns} />)
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
  })

  it('renders data rows', () => {
    render(<Table data={data} columns={columns} />)
    expect(screen.getByText('Server A')).toBeInTheDocument()
    expect(screen.getByText('Server B')).toBeInTheDocument()
    expect(screen.getByText('Server C')).toBeInTheDocument()
  })

  it('row click fires onRowClick', async () => {
    const onRowClick = vi.fn()
    render(<Table data={data} columns={columns} onRowClick={onRowClick} />)
    const { default: userEvent } = await import('@testing-library/user-event')
    await userEvent.click(screen.getByText('Server A'))
    expect(onRowClick).toHaveBeenCalledTimes(1)
  })

  it('pagination bar visible when pagination prop provided', () => {
    render(<Table data={data} columns={columns} pagination={{ total: 50, hasMore: true }} />)
    expect(screen.getByText('Total: 50')).toBeInTheDocument()
  })

  it('no pagination bar when pagination prop omitted', () => {
    render(<Table data={data} columns={columns} />)
    expect(screen.queryByText(/total:/i)).toBeNull()
  })

  it('empty data renders headers only', () => {
    const { container } = render(<Table data={[]} columns={columns} />)
    expect(screen.getByText('Name')).toBeInTheDocument()
    const tbody = container.querySelector('tbody')
    expect(tbody?.children.length).toBe(0)
  })

  it('next button shown when hasMore is true', () => {
    render(<Table data={data} columns={columns} pagination={{ total: 50, hasMore: true, onNext: vi.fn() }} />)
    expect(screen.getByText('Next')).toBeInTheDocument()
  })

  it('next button hidden when hasMore is false', () => {
    render(<Table data={data} columns={columns} pagination={{ total: 3, hasMore: false }} />)
    expect(screen.queryByText('Next')).toBeNull()
  })

  it('previous button renders when onPrev provided', () => {
    render(<Table data={data} columns={columns} pagination={{ total: 50, hasMore: true, onPrev: vi.fn() }} />)
    expect(screen.getByText('Previous')).toBeInTheDocument()
  })
})
