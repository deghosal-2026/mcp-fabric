import { useQuery, useMutation, useQueries } from '@tanstack/react-query'
import { fetchStaleMappings, reviewMapping, queryClient, fetchServer, fetchCapability } from '../api/client'
import { PageState } from '../components/shared/PageState'
import { Table } from '../components/shared/Table'
import type { CapabilityMapping } from '../types'
import { useMemo } from 'react'
import { useToast } from '../components/shared/Toast'

export function ReviewsPage() {
  // Fetch stale mappings — mappings whose tool_schema_digest has drifted from the
  // server's current tool signature, requiring admin review
  const query = useQuery({ queryKey: ['stale-mappings'], queryFn: fetchStaleMappings })
  const { addToast } = useToast()

  // Mutation: POST a review decision (approve/reject) for a single mapping.
  // Invalidates the stale-mappings list on success and surfaces a toast
  // with the decision outcome; shows error toast on failure.
  const mutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'approved' | 'rejected' }) => reviewMapping(id, decision),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['stale-mappings'] })
      addToast('success', `Mapping ${vars.decision}`)
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const mappings = (query.data || []) as CapabilityMapping[]
  // Collect unique server and capability IDs from the stale mappings, then
  // fire parallel queries to resolve each to a human-readable name.
  // useQueries runs one query per ID; the resolved names are memoised into
  // lookup maps keyed by the raw ID.
  const serverIds = useMemo(() => Array.from(new Set(mappings.map(m => m.server_id))), [mappings])
  const capabilityIds = useMemo(() => Array.from(new Set(mappings.map(m => m.capability_id))), [mappings])

  const serverQueries = useQueries({
    queries: serverIds.map(id => ({ queryKey: ['server', id], queryFn: () => fetchServer(id), enabled: !!id })),
  })
  // Parallel capability name queries — same pattern as server name resolution above
  const capQueries = useQueries({
    queries: capabilityIds.map(id => ({ queryKey: ['capability', id], queryFn: () => fetchCapability(id), enabled: !!id })),
  })

  const serverNames = useMemo(() => {
    const map: Record<string, string> = {}
    serverQueries.forEach((q, i) => { if (q.data) map[serverIds[i]] = (q.data as any).name })
    return map
  }, [serverQueries, serverIds])
  const capNames = useMemo(() => {
    const map: Record<string, string> = {}
    capQueries.forEach((q, i) => { if (q.data) map[capabilityIds[i]] = (q.data as any).name })
    return map
  }, [capQueries, capabilityIds])

  // Transform the raw stale mappings into table rows. Each row resolves the
  // opaque server_id / capability_id to a display name (falling back to a
  // truncated ID if the name query hasn't settled). Status defaults to "stale"
  // so every row is actionable even when the backend omits it.
  const rows = mappings.map((m: CapabilityMapping) => ({
    id: m.id,
    capability: capNames[m.capability_id] || m.capability_id.slice(0, 8),
    server: serverNames[m.server_id] || m.server_id.slice(0, 8),
    tool: m.tool_name,
    digest: (m.tool_schema_digest || '').slice(0, 12),
    status: m.status || 'stale',
  }))

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-4">Pending Schema Reviews</h1>
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
                id: 'actions',
                header: 'Actions',
                cell: ({ row }) => {
                  const r = row.original as { id: string }
                  return (
                    <div className="flex gap-2">
                      <button
                        className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                        onClick={() => mutation.mutate({ id: r.id, decision: 'approved' })}
                        disabled={mutation.isPending}
                      >Approve</button>
                      <button
                        className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                        onClick={() => mutation.mutate({ id: r.id, decision: 'rejected' })}
                        disabled={mutation.isPending}
                      >Reject</button>
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
