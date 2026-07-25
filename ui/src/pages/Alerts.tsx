import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAlerts, acknowledgeAlert } from '../api/client'
import { Table } from '../components/shared/Table'
import { FilterBar } from '../components/shared/FilterBar'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { ColumnDef } from '@tanstack/react-table'
import type { AlertEvent } from '../types'

export function AlertsPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const alerts = useQuery({
    queryKey: ['alerts', filters],
    queryFn: () => fetchAlerts({ ...filters, per_page: '50' }),
  })

  const acknowledge = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      addToast('success', 'Alert acknowledged')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const columns: ColumnDef<AlertEvent>[] = [
    { header: 'Message', accessorKey: 'message' },
    { header: 'Rule', accessorKey: 'rule_name' },
    {
      header: 'Fired',
      accessorKey: 'fired_at',
      cell: ({ getValue }) => new Date(getValue() as string).toLocaleString(),
    },
    {
      header: 'Acknowledged',
      cell: ({ row }) => row.original.acknowledged_at ? (
        <span className="text-green-600 text-sm">Yes</span>
      ) : (
        <button onClick={e => { e.stopPropagation(); acknowledge.mutate(row.original.id) }}
          className="text-sm text-blue-500 hover:underline">
          Acknowledge
        </button>
      ),
    },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Alerts</h1>

      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-4">
          <FilterBar
            filters={[
              { key: 'acknowledged', label: 'Status', options: [
                { value: 'false', label: 'Unacknowledged' },
                { value: 'true', label: 'Acknowledged' },
              ]},
            ]}
            onFilter={setFilters}
          />
        </div>

        <PageState query={alerts}>
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
