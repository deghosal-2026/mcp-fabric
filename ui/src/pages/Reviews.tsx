import { useQuery, useMutation, useQueries } from '@tanstack/react-query'
import {
  fetchStaleMappings,
  fetchQueueSummary,
  bulkRetireMappings,
  reviewMapping,
  queryClient,
  fetchServer,
  fetchCapability,
} from '../api/client'
import { PageState } from '../components/shared/PageState'
import { Table } from '../components/shared/Table'
import type { CapabilityMapping, ReviewQueueSummary } from '../types'
import { useMemo, useState } from 'react'
import { useToast } from '../components/shared/Toast'

// Failure-class metadata for visual treatment + filter labels (#447).
// Critical classes (drifted, schema_mismatch) are hands-on: review + re-approve.
// Unreachable classes (unreachable, timeout) are hands-off: retire-or-wait.
const FAILURE_CLASS_META: Record<
  string,
  { label: string; critical: boolean; badge: string }
> = {
  drifted: { label: 'Drifted', critical: true, badge: 'bg-amber-100 text-amber-800' },
  schema_mismatch: {
    label: 'Schema Mismatch',
    critical: true,
    badge: 'bg-orange-100 text-orange-800',
  },
  unreachable: {
    label: 'Unreachable',
    critical: false,
    badge: 'bg-slate-100 text-slate-600',
  },
  timeout: { label: 'Timeout', critical: false, badge: 'bg-slate-100 text-slate-600' },
}

const FILTER_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'drifted', label: 'Drifted' },
  { value: 'schema_mismatch', label: 'Schema Mismatch' },
  { value: 'unreachable', label: 'Unreachable' },
  { value: 'timeout', label: 'Timeout' },
]

export function ReviewsPage() {
  const [filter, setFilter] = useState('')
  const { addToast } = useToast()

  // Fetch stale mappings with optional failure_class filter (#447).
  const query = useQuery({
    queryKey: ['stale-mappings', filter],
    queryFn: () => fetchStaleMappings(filter || undefined),
  })

  // Live queue summary (#447) — separates critical from unreachable tallies.
  const summaryQuery = useQuery({
    queryKey: ['queue-summary'],
    queryFn: fetchQueueSummary,
  })

  // Mutation: POST a review decision (approve/reject) for a single mapping.
  const reviewMutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'approved' | 'rejected' }) =>
      reviewMapping(id, decision),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['stale-mappings'] })
      queryClient.invalidateQueries({ queryKey: ['queue-summary'] })
      addToast('success', `Mapping ${vars.decision}`)
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  // Mutation: bulk-retire a whole failure_class without per-item review (#447).
  const bulkRetireMutation = useMutation({
    mutationFn: (failureClass: string) =>
      bulkRetireMappings({ failure_class: failureClass }),
    onSuccess: (data, failureClass) => {
      queryClient.invalidateQueries({ queryKey: ['stale-mappings'] })
      queryClient.invalidateQueries({ queryKey: ['queue-summary'] })
      addToast('success', `Retired ${data.retired} ${failureClass} item(s)`)
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const mappings = (query.data || []) as CapabilityMapping[]
  const summary = summaryQuery.data as ReviewQueueSummary | undefined

  // Collect unique server and capability IDs to resolve human-readable names.
  const serverIds = useMemo(() => Array.from(new Set(mappings.map(m => m.server_id))), [mappings])
  const capabilityIds = useMemo(
    () => Array.from(new Set(mappings.map(m => m.capability_id))),
    [mappings]
  )

  const serverQueries = useQueries({
    queries: serverIds.map(id => ({
      queryKey: ['server', id],
      queryFn: () => fetchServer(id),
      enabled: !!id,
    })),
  })
  const capQueries = useQueries({
    queries: capabilityIds.map(id => ({
      queryKey: ['capability', id],
      queryFn: () => fetchCapability(id),
      enabled: !!id,
    })),
  })

  const serverNames = useMemo(() => {
    const map: Record<string, string> = {}
    serverQueries.forEach((q, i) => {
      if (q.data) map[serverIds[i]] = (q.data as any).name
    })
    return map
  }, [serverQueries, serverIds])
  const capNames = useMemo(() => {
    const map: Record<string, string> = {}
    capQueries.forEach((q, i) => {
      if (q.data) map[capabilityIds[i]] = (q.data as any).name
    })
    return map
  }, [capQueries, capabilityIds])

  // Count unreachable items visible so the bulk-retire action only shows when
  // there's something to retire.
  const unreachableCount = useMemo(
    () =>
      mappings.filter(m => m.failure_class === 'unreachable' || m.failure_class === 'timeout')
        .length,
    [mappings]
  )

  const rows = mappings.map((m: CapabilityMapping) => {
    const meta = m.failure_class ? FAILURE_CLASS_META[m.failure_class] : null
    return {
      id: m.id,
      capability: capNames[m.capability_id] || m.capability_id.slice(0, 8),
      server: serverNames[m.server_id] || m.server_id.slice(0, 8),
      tool: m.tool_name,
      digest: (m.tool_schema_digest || '').slice(0, 12),
      status: m.status || 'stale',
      failure_class: m.failure_class || '',
      failure_label: meta?.label || '—',
      failure_badge: meta?.badge || '',
      critical: meta?.critical ?? false,
      onApprove: () => reviewMutation.mutate({ id: m.id, decision: 'approved' }),
      onReject: () => reviewMutation.mutate({ id: m.id, decision: 'rejected' }),
    }
  })

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-4">Pending Schema Reviews</h1>

      {/* Queue priority summary (#447): critical (drifted/mismatch) vs
          unreachable (hands-off). Unreachable items never count toward the
          reviewer's pending-critical tally. */}
      {summary && (
        <div className="flex gap-4 mb-4 text-sm">
          <div className="px-3 py-2 bg-white rounded border">
            <span className="text-slate-500">Total</span>
            <span className="ml-2 font-semibold">{summary.total}</span>
          </div>
          <div className="px-3 py-2 bg-white rounded border">
            <span className="text-slate-500">Critical</span>
            <span className="ml-2 font-semibold text-amber-700">{summary.critical}</span>
          </div>
          <div className="px-3 py-2 bg-white rounded border">
            <span className="text-slate-500">Unreachable</span>
            <span className="ml-2 font-semibold text-slate-500">{summary.unreachable}</span>
          </div>
        </div>
      )}

      {/* Filter bar + bulk-retire action (#447). */}
      <div className="flex items-center gap-3 mb-4">
        <label htmlFor="failure-class-filter" className="text-sm text-slate-600">
          Filter:
        </label>
        <select
          id="failure-class-filter"
          className="px-2 py-1 text-sm border rounded"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        >
          {FILTER_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        {unreachableCount > 0 && (
          <button
            className="px-3 py-1 text-xs bg-slate-700 text-white rounded hover:bg-slate-800 disabled:opacity-50"
            onClick={() => bulkRetireMutation.mutate('unreachable')}
            disabled={bulkRetireMutation.isPending}
            title="Retire all unreachable items without per-item review"
          >
            Retire all unreachable ({unreachableCount})
          </button>
        )}
      </div>

      <PageState query={query}>
        {() => (
          <Table
            columns={[
              { accessorKey: 'capability', header: 'Capability' },
              { accessorKey: 'server', header: 'Server' },
              { accessorKey: 'tool', header: 'Tool' },
              { accessorKey: 'digest', header: 'Digest' },
              { accessorKey: 'status', header: 'Status' },
              {
                id: 'failure_class',
                header: 'Failure Class',
                cell: ({ row }) => {
                  const r = row.original as {
                    failure_label: string
                    failure_badge: string
                    critical: boolean
                  }
                  if (!r.failure_label || r.failure_label === '—') return <span className="text-slate-300">—</span>
                  return (
                    <span
                      className={`px-2 py-0.5 text-xs rounded ${r.failure_badge} ${
                        r.critical ? 'font-semibold' : ''
                      }`}
                    >
                      {r.failure_label}
                    </span>
                  )
                },
              },
              {
                id: 'actions',
                header: 'Actions',
                cell: ({ row }) => {
                  const r = row.original as {
                    onApprove: () => void
                    onReject: () => void
                  }
                  return (
                    <div className="flex gap-2">
                      <button
                        className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                        onClick={r.onApprove}
                        disabled={reviewMutation.isPending}
                      >
                        Approve
                      </button>
                      <button
                        className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                        onClick={r.onReject}
                        disabled={reviewMutation.isPending}
                      >
                        Reject
                      </button>
                    </div>
                  )
                },
              },
            ]}
            data={rows}
          />
        )}
      </PageState>
    </div>
  )
}
