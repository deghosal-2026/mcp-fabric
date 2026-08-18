import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAgentClasses, createAgentClass, fetchAgentIdentities,
  createAgentIdentity, fetchIdentityResourceBindings, setIdentityResourceBindings,
} from '../api/client'
import { Table } from '../components/shared/Table'
import { Modal } from '../components/shared/Modal'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { LegacyColumnDef as ColumnDef } from '@tanstack/react-table/legacy'
import type { AgentClass, ResourceBinding } from '../types'

export function AgentClassesPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [showTokens, setShowTokens] = useState<string | null>(null)
  const [newTokenName, setNewTokenName] = useState('')
  const [createdToken, setCreatedToken] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', description: '' })
  const [resTarget, setResTarget] = useState<string | null>(null)
  const [resInput, setResInput] = useState({ dimension_key: '', allowed_value: '' })
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const classes = useQuery({
    queryKey: ['agent-classes'],
    queryFn: fetchAgentClasses,
  })

  const tokens = useQuery({
    queryKey: ['identities', showTokens],
    queryFn: () => fetchAgentIdentities(showTokens!),
    enabled: !!showTokens,
  })

  const create = useMutation({
    mutationFn: () => createAgentClass(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-classes'] })
      setShowCreate(false)
      setForm({ name: '', description: '' })
      addToast('success', 'Agent class created')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const generateToken = useMutation({
    mutationFn: () => createAgentIdentity(showTokens!, newTokenName),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['identities', showTokens] })
      setCreatedToken(data.token)
      addToast('success', 'Token created - copy it now, it will not be shown again')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const agentBindings = useQuery({
    queryKey: ['agent-bindings', resTarget],
    queryFn: () => fetchIdentityResourceBindings(resTarget!),
    enabled: !!resTarget,
  })

  const saveAgentBinding = useMutation({
    mutationFn: () => {
      const current = agentBindings.data ?? []
      const updated = [...current, { dimension_key: resInput.dimension_key, allowed_value: resInput.allowed_value }]
      return setIdentityResourceBindings(resTarget!, updated.map(b => ({ dimension_key: b.dimension_key, allowed_value: b.allowed_value })))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-bindings', resTarget] })
      setResInput({ dimension_key: '', allowed_value: '' })
      addToast('success', 'Binding added')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const removeAgentBinding = useMutation({
    mutationFn: (bindingId: string) => {
      const current = agentBindings.data ?? []
      const updated = current.filter(b => b.id !== bindingId)
      return setIdentityResourceBindings(resTarget!, updated.map(b => ({ dimension_key: b.dimension_key, allowed_value: b.allowed_value })))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-bindings', resTarget] })
      addToast('success', 'Binding removed')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const columns: ColumnDef<AgentClass>[] = [
    { header: 'Name', accessorKey: 'name' },
    { header: 'Description', accessorKey: 'description' },
    { header: 'Namespace', accessorKey: 'team_namespace' },
    {
      header: 'Actions',
      cell: ({ row }) => (
<div className="flex gap-2">
            <button
              onClick={e => { e.stopPropagation(); setResTarget(row.original.id) }}
              className="text-sm text-blue-500 hover:underline"
            >
              Bindings
            </button>
            <button
              onClick={e => { e.stopPropagation(); setShowTokens(row.original.id) }}
              className="text-sm text-blue-500 hover:underline"
            >
              Tokens
            </button>
          </div>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Agent Classes</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Create Agent Class
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm">
        <PageState query={classes}>
          {data => <Table data={data} columns={columns} />}
        </PageState>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Agent Class"
        onConfirm={() => create.mutate()} confirmDisabled={!form.name} loading={create.isPending}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input type="text" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="agent:developer" className="w-full px-3 py-2 border rounded-lg" autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg" rows={3} />
          </div>
        </div>
      </Modal>

      <Modal open={!!showTokens} onClose={() => { setShowTokens(null); setCreatedToken(null); setNewTokenName('') }}
        title="Agent Tokens" size="lg">
        {createdToken ? (
          <div>
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm p-3 rounded-lg mb-4">
              Copy this token now. It will not be shown again.
            </div>
            <div className="bg-gray-100 p-3 rounded-lg font-mono text-sm break-all">{createdToken}</div>
          </div>
        ) : (
          <div>
            <div className="flex gap-2 mb-4">
              <input type="text" value={newTokenName} onChange={e => setNewTokenName(e.target.value)}
                placeholder="Token name" className="flex-1 px-3 py-2 border rounded-lg" />
              <button onClick={() => generateToken.mutate()} disabled={!newTokenName || generateToken.isPending}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50">
                {generateToken.isPending ? '...' : 'Generate'}
              </button>
            </div>
            <PageState query={tokens}>
              {data => (
                <div className="space-y-2">
                  {data.map(t => (
                    <div key={t.id} className="flex items-center justify-between p-2 border rounded">
                      <div>
                        <span className="text-sm font-medium">{t.token_prefix}****</span>
                        <span className="text-xs text-gray-500 ml-2">{t.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </PageState>
          </div>
        )}
      </Modal>

      <Modal open={!!resTarget} onClose={() => { setResTarget(null); setResInput({ dimension_key: '', allowed_value: '' }) }}
        title="Identity Resource Bindings" size="lg">
        <div className="space-y-4">
          {agentBindings.isLoading && <p className="text-gray-500">Loading bindings...</p>}
          {agentBindings.data && agentBindings.data.length === 0 && (
            <p className="text-gray-400 text-sm">No resource bindings. This agent has unrestricted resource access.</p>
          )}
          {agentBindings.data?.map((b: ResourceBinding) => (
            <div key={b.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <span className="font-mono text-sm font-medium">{b.dimension_key}</span>
                <span className="text-gray-500 text-sm ml-2">= {b.allowed_value}</span>
              </div>
              <button onClick={() => removeAgentBinding.mutate(b.id)}
                className="text-sm text-red-500 hover:text-red-700">Remove</button>
            </div>
          ))}
          <div className="pt-4 border-t">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Add Binding</h4>
            <div className="flex gap-2">
              <input type="text" value={resInput.dimension_key}
                onChange={e => setResInput(p => ({ ...p, dimension_key: e.target.value }))}
                placeholder="env" className="flex-1 px-3 py-2 border rounded-lg text-sm" />
              <input type="text" value={resInput.allowed_value}
                onChange={e => setResInput(p => ({ ...p, allowed_value: e.target.value }))}
                placeholder="staging" className="flex-1 px-3 py-2 border rounded-lg text-sm" />
              <button onClick={() => saveAgentBinding.mutate()}
                disabled={!resInput.dimension_key || !resInput.allowed_value || saveAgentBinding.isPending}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 disabled:opacity-50">Add</button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
