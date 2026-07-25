import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApprovals, resolveApproval } from '../api/client'
import { Table } from '../components/shared/Table'
import { FilterBar } from '../components/shared/FilterBar'
import { Badge } from '../components/shared/Badge'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { ColumnDef } from '@tanstack/react-table'
import type { ApprovalRequest } from '../types'

export function ApprovalsPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [reviewTarget, setReviewTarget] = useState<ApprovalRequest | null>(null)
  const [reviewNote, setReviewNote] = useState('')
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const approvals = useQuery({
    queryKey: ['approvals', filters],
    queryFn: () => fetchApprovals({ ...filters, per_page: '50' }),
  })

  const approve = useMutation({
    mutationFn: () => resolveApproval(reviewTarget!.id, 'approved', reviewNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
      setReviewTarget(null)
      setReviewNote('')
      addToast('success', 'Request approved')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const deny = useMutation({
    mutationFn: () => resolveApproval(reviewTarget!.id, 'denied', reviewNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
      setReviewTarget(null)
      setReviewNote('')
      addToast('success', 'Request denied')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const columns: ColumnDef<ApprovalRequest>[] = [
    { header: 'Agent', accessorKey: 'agent_name' },
    { header: 'Capability', accessorKey: 'capability_name' },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: ({ getValue }) => <Badge label={getValue() as string} />,
    },
    {
      header: 'Requested',
      accessorKey: 'requested_at',
      cell: ({ getValue }) => new Date(getValue() as string).toLocaleString(),
    },
    {
      header: 'Actions',
      cell: ({ row }) => (
        row.original.status === 'pending' ? (
          <button onClick={e => { e.stopPropagation(); setReviewTarget(row.original) }}
            className="text-sm text-blue-500 hover:underline">Review</button>
        ) : null
      ),
    },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Approvals</h1>

      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-4">
          <FilterBar
            filters={[
              { key: 'status', label: 'Status', options: [
                { value: 'pending', label: 'Pending' },
                { value: 'approved', label: 'Approved' },
                { value: 'denied', label: 'Denied' },
              ]},
            ]}
            onFilter={setFilters}
          />
        </div>

        <PageState query={approvals}>
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

      {reviewTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold">Review Approval Request</h2>
            </div>
            <div className="p-6 space-y-3">
              <div className="text-sm"><span className="font-medium">Agent:</span> {reviewTarget.agent_name || reviewTarget.agent_identity_id}</div>
              <div className="text-sm"><span className="font-medium">Capability:</span> {reviewTarget.capability_name || reviewTarget.capability_id}</div>
              <div className="text-sm"><span className="font-medium">Server:</span> {reviewTarget.server_name || reviewTarget.server_id}</div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Note / Reason</label>
                <textarea value={reviewNote} onChange={e => setReviewNote(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg" rows={3} />
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t bg-gray-50 rounded-b-xl">
              <button onClick={() => { setReviewTarget(null); setReviewNote('') }}
                className="px-4 py-2 text-sm border rounded-lg">Close</button>
              <button onClick={() => deny.mutate()} disabled={deny.isPending}
                className="px-4 py-2 text-sm text-white bg-red-500 rounded-lg hover:bg-red-600 disabled:opacity-50">
                Deny
              </button>
              <button onClick={() => approve.mutate()} disabled={approve.isPending}
                className="px-4 py-2 text-sm text-white bg-green-500 rounded-lg hover:bg-green-600 disabled:opacity-50">
                Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
