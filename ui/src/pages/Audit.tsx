import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAuditEvents, exportAudit } from '../api/client'
import { Table } from '../components/shared/Table'
import { FilterBar } from '../components/shared/FilterBar'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { LegacyColumnDef as ColumnDef } from '@tanstack/react-table/legacy'
import type { AuditEvent } from '../types'

const PER_PAGE = '50'

export function AuditPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [offset, setOffset] = useState(0)
  const handleFilter = useCallback((f: Record<string, string>) => { setFilters(f); setOffset(0) }, [])
  const { addToast } = useToast()

  const audit = useQuery({
    queryKey: ['audit', filters],
    queryFn: () => fetchAuditEvents({ ...filters, offset: String(offset), per_page: PER_PAGE }),
    placeholderData: (prev) => prev,
  })

  const handleExport = async () => {
    try {
      const res = await exportAudit(filters)
      addToast('success', `Export started: ${res.export_id}`)
    } catch (err) {
      addToast('error', err instanceof Error ? err.message : 'Export failed')
    }
  }

  const columns: ColumnDef<AuditEvent>[] = [
    {
      header: 'Time',
      accessorKey: 'created_at',
      cell: ({ getValue }) => new Date(getValue() as string).toLocaleString(),
    },
    { header: 'Type', accessorKey: 'event_type' },
    { header: 'Actor', accessorKey: 'actor_id' },
    { header: 'Target', accessorKey: 'target_type' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <button onClick={handleExport} className="px-4 py-2 border rounded-lg hover:bg-gray-100 text-sm">
          Export
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-4">
          <FilterBar
            filters={[
              { key: 'event_type', label: 'Event Type', options: [
                { value: 'capability_request', label: 'Capability Request' },
                { value: 'policy_change', label: 'Policy Change' },
                { value: 'server_registered', label: 'Server Registered' },
                { value: 'server_decommissioned', label: 'Server Decommissioned' },
              ]},
              { key: 'actor_type', label: 'Actor', options: [
                { value: 'agent', label: 'Agent' },
                { value: 'admin', label: 'Admin' },
              ]},
            ]}
            onFilter={handleFilter}
            searchPlaceholder="Search by actor ID..."
          />
        </div>

        <PageState query={audit}>
          {data => (
            (() => {
              const items = data.items ?? (data as any).events ?? []
              const pagination = data.pagination ?? { total: items.length, has_more: false, next_cursor: undefined }
              return (
            <Table
              data={items}
              columns={columns}
              pagination={{
                total: pagination.total,
                hasMore: pagination.has_more,
                nextCursor: pagination.next_cursor,
                onNext: pagination.has_more ? () => setOffset(o => o + Number(PER_PAGE)) : undefined,
                onPrev: offset > 0 ? () => setOffset(o => Math.max(0, o - Number(PER_PAGE))) : undefined,
              }}
            />
              )
            })()
          )}
        </PageState>
      </div>
    </div>
  )
}
