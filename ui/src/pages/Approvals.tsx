import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApprovals, resolveApproval } from '../api/client'
import { Table } from '../components/shared/Table'
import { FilterBar } from '../components/shared/FilterBar'
import { Badge } from '../components/shared/Badge'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { ColumnDef } from '@tanstack/react-table'
import type { ApprovalRequest } from '../types'

const PER_PAGE = '50'

export function ApprovalsPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [offset, setOffset] = useState(0)
  const handleFilter = useCallback((f: Record<string, string>) => { setFilters(f); setOffset(0) }, [])
  const [reviewTarget, setReviewTarget] = useState<ApprovalRequest | null>(null)
  const [reviewNote, setReviewNote] = useState('')
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const approvals = useQuery({
    queryKey: ['approvals', filters],
    queryFn: () => fetchApprovals({ ...filters, offset: String(offset), per_page: PER_PAGE }),
    placeholderData: (prev) => prev,
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
            onFilter={handleFilter}
          />
        </div>

        <PageState query={approvals}>
          {data => (
            (() => {
              const items = data.items ?? (data as any).approvals ?? []
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
              {reviewTarget.request_params && typeof reviewTarget.request_params === 'object' && 'resources' in reviewTarget.request_params && (() => {
                const res = (reviewTarget.request_params as Record<string, unknown>).resources
                if (!res || typeof res !== 'object') return null
                const entries = Object.entries(res as Record<string, string>)
                return entries.length > 0 ? (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h4 className="text-sm font-medium text-yellow-800 mb-2">Resource Constraints</h4>
                    {entries.map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-sm py-1">
                        <span className="font-mono text-yellow-700">{key}</span>
                        <span className="font-mono text-yellow-900">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                ) : null
              })()}
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
