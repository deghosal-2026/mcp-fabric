import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchServers, registerServer } from '../api/client'
import { Table } from '../components/shared/Table'
import { FilterBar } from '../components/shared/FilterBar'
import { Modal } from '../components/shared/Modal'
import { Badge } from '../components/shared/Badge'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { ColumnDef } from '@tanstack/react-table'
import type { MCPServer } from '../types'

export function ServersPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [cursor, setCursor] = useState<string | undefined>()
  const handleFilter = useCallback((f: Record<string, string>) => { setFilters(f); setCursor(undefined) }, [])
  const [showRegister, setShowRegister] = useState(false)
  const [form, setForm] = useState({ name: '', endpoint: '', owner_team: '', labels: '' })
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const servers = useQuery({
    queryKey: ['servers', filters],
    queryFn: () => fetchServers({ ...filters, cursor, per_page: '50' }),
    placeholderData: (prev) => prev,
  })

  const register = useMutation({
    mutationFn: () => registerServer({
      name: form.name,
      endpoint: form.endpoint,
      owner_team: form.owner_team,
      labels: form.labels.split(',').map(s => s.trim()).filter(Boolean),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
      setShowRegister(false)
      setForm({ name: '', endpoint: '', owner_team: '', labels: '' })
      addToast('success', 'Server registered successfully')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const columns: ColumnDef<MCPServer>[] = [
    { header: 'Name', accessorKey: 'name' },
    { header: 'Endpoint', accessorKey: 'endpoint' },
    { header: 'Team', accessorKey: 'owner_team' },
    {
      header: 'Health',
      accessorKey: 'health_status',
      cell: ({ getValue }) => <Badge label={getValue() as string} />,
    },
    {
      header: 'Trust',
      accessorKey: 'trust_level',
      cell: ({ getValue }) => <Badge label={getValue() as string} />,
    },
    {
      header: 'Tools',
      accessorKey: 'tools',
      cell: ({ getValue }) => <span>{(getValue() as unknown[])?.length || 0}</span>,
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Servers</h1>
        <button
          onClick={() => setShowRegister(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Register Server
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-4">
          <FilterBar
            filters={[
              { key: 'health_status', label: 'Health', options: [
                { value: 'healthy', label: 'Healthy' },
                { value: 'degraded', label: 'Degraded' },
                { value: 'unhealthy', label: 'Unhealthy' },
              ]},
              { key: 'trust_level', label: 'Trust', options: [
                { value: 'trusted', label: 'Trusted' },
                { value: 'restricted', label: 'Restricted' },
                { value: 'approval-gated', label: 'Approval Gated' },
                { value: 'unreviewed', label: 'Unreviewed' },
              ]},
              { key: 'team_namespace', label: 'Team', options: [
                { value: 'team:platform', label: 'Platform' },
                { value: 'team:security', label: 'Security' },
                { value: 'team:data', label: 'Data' },
              ]},
            ]}
            onFilter={handleFilter}
            searchPlaceholder="Search servers..."
          />
        </div>

        <PageState query={servers}>
          {data => (
            (() => {
              const items = data.items ?? (data as any).servers ?? []
              const pagination = data.pagination ?? { total: items.length, has_more: false, next_cursor: undefined }
              return (
            <Table
              data={items}
              columns={columns}
              pagination={{
                total: pagination.total,
                hasMore: pagination.has_more,
                nextCursor: pagination.next_cursor,
                cursor,
                onNext: pagination.next_cursor ? () => setCursor(pagination.next_cursor) : undefined,
                onPrev: cursor ? () => setCursor(undefined) : undefined,
              }}
            />
              )
            })()
          )}
        </PageState>
      </div>

      <Modal
        open={showRegister}
        onClose={() => setShowRegister(false)}
        title="Register MCP Server"
        onConfirm={() => register.mutate()}
        confirmDisabled={!form.name || !form.endpoint}
        loading={register.isPending}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint</label>
            <input
              type="text"
              value={form.endpoint}
              onChange={e => setForm(p => ({ ...p, endpoint: e.target.value }))}
              placeholder="http://localhost:3001"
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Owner Team</label>
            <input
              type="text"
              value={form.owner_team}
              onChange={e => setForm(p => ({ ...p, owner_team: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Labels (comma-separated)</label>
            <input
              type="text"
              value={form.labels}
              onChange={e => setForm(p => ({ ...p, labels: e.target.value }))}
              placeholder="security, production, read-only"
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
