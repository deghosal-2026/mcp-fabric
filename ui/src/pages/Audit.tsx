import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAuditEvents, exportAudit } from '../api/client'
import { Table } from '../components/shared/Table'
import { FilterBar } from '../components/shared/FilterBar'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { ColumnDef } from '@tanstack/react-table'
import type { AuditEvent } from '../types'

export function AuditPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const { addToast } = useToast()

  const audit = useQuery({
    queryKey: ['audit', filters],
    queryFn: () => fetchAuditEvents({ ...filters, per_page: '50' }),
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
            onFilter={setFilters}
            searchPlaceholder="Search by actor ID..."
          />
        </div>

        <PageState query={audit}>
          {data => (
            <Table
              data={data.items}
              columns={columns}
              pagination={{
                total: data.pagination.total,
                hasMore: data.pagination.has_more,
                nextCursor: data.pagination.next_cursor,
              }}
            />
          )}
        </PageState>
      </div>
    </div>
  )
}
