import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchCapabilities, createCapability, deprecateCapability,
} from '../api/client'
import { Table } from '../components/shared/Table'
import { FilterBar } from '../components/shared/FilterBar'
import { Modal } from '../components/shared/Modal'
import { Badge } from '../components/shared/Badge'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { ColumnDef } from '@tanstack/react-table'
import type { Capability } from '../types'

const PER_PAGE = '100'

export function CapabilitiesPage() {
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [offset, setOffset] = useState(0)
  const handleFilter = useCallback((f: Record<string, string>) => { setFilters(f); setOffset(0) }, [])
  const [showCreate, setShowCreate] = useState(false)
  const [deprecateTarget, setDeprecateTarget] = useState<Capability | null>(null)
  const [form, setForm] = useState({ name: '', domain: '', description: '' })
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const capabilities = useQuery({
    queryKey: ['capabilities', filters],
    queryFn: () => fetchCapabilities({ ...filters, per_page: PER_PAGE }),
    placeholderData: (prev) => prev,
  })

  const create = useMutation({
    mutationFn: () => createCapability(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capabilities'] })
      setShowCreate(false)
      setForm({ name: '', domain: '', description: '' })
      addToast('success', 'Capability created')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const deprecate = useMutation({
    mutationFn: () => deprecateCapability(deprecateTarget!.id, 14),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capabilities'] })
      setDeprecateTarget(null)
      addToast('success', 'Capability deprecated')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const columns: ColumnDef<Capability>[] = [
    { header: 'Name', accessorKey: 'name' },
    { header: 'Domain', accessorKey: 'domain' },
    { header: 'Description', accessorKey: 'description' },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: ({ getValue }) => <Badge label={getValue() as string} />,
    },
    {
      header: 'Actions',
      cell: ({ row }) => (
        <button
          onClick={e => { e.stopPropagation(); setDeprecateTarget(row.original) }}
          disabled={row.original.status === 'deprecated'}
          className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
        >
          Deprecate
        </button>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Capability Catalog</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Create Capability
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-4">
          <FilterBar
            filters={[
              { key: 'domain', label: 'Domain', options: [
                { value: 'code', label: 'Code' },
                { value: 'knowledge', label: 'Knowledge' },
                { value: 'deployment', label: 'Deployment' },
                { value: 'incident', label: 'Incident' },
                { value: 'security', label: 'Security' },
              ]},
              { key: 'status', label: 'Status', options: [
                { value: 'active', label: 'Active' },
                { value: 'deprecated', label: 'Deprecated' },
              ]},
            ]}
            onFilter={handleFilter}
            searchPlaceholder="Search capabilities..."
          />
        </div>

        <PageState query={capabilities}>
          {data => {
            const items = Array.isArray(data) ? data : data.items ?? (data as any).capabilities ?? []
            const normalizedItems = items.map((item: Capability) => ({
              ...item,
              description: item.description ?? '',
            }))
            const pagination = data.pagination ?? { total: normalizedItems.length, has_more: false, next_cursor: undefined }
            return (
              <Table
                data={normalizedItems}
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
          }}
        </PageState>
      </div>

      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Capability"
        onConfirm={() => create.mutate()}
        confirmDisabled={!form.name || !form.domain}
        loading={create.isPending}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="code:search"
              className="w-full px-3 py-2 border rounded-lg"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
            <input
              type="text"
              value={form.domain}
              onChange={e => setForm(p => ({ ...p, domain: e.target.value }))}
              placeholder="code"
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
              rows={3}
            />
          </div>
        </div>
      </Modal>

      {deprecateTarget && (
        <Modal
          open={!!deprecateTarget}
          onClose={() => setDeprecateTarget(null)}
          title="Deprecate Capability"
          onConfirm={() => deprecate.mutate()}
          confirmLabel="Deprecate"
          destructive
          loading={deprecate.isPending}
        >
          <p className="text-gray-600">
            Are you sure you want to deprecate <strong>{deprecateTarget.name}</strong>?
            It will be removed from all capability packs and agents will receive a deprecation notice for 14 days.
          </p>
        </Modal>
      )}
    </div>
  )
}
