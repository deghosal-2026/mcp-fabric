import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPacks, createPack, assignPackToClass, fetchAgentClasses,
  fetchPackResourceBindings, setPackResourceBindings } from '../api/client'
import { Modal } from '../components/shared/Modal'
import { PackBreadthWarning } from '../components/shared/PackBreadthWarning'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { CapabilityPack, ResourceBinding } from '../types'

export function PacksPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [assignTarget, setAssignTarget] = useState<string | null>(null)
  const [selectedClass, setSelectedClass] = useState('')
  const [form, setForm] = useState({ name: '', description: '' })
  const [resTarget, setResTarget] = useState<string | null>(null)
  const [resInput, setResInput] = useState({ dimension_key: '', allowed_value: '' })
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const packs = useQuery({
    queryKey: ['packs'],
    queryFn: fetchPacks,
  })

  const classes = useQuery({
    queryKey: ['agent-classes'],
    queryFn: fetchAgentClasses,
  })

  const create = useMutation({
    mutationFn: () => createPack(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packs'] })
      setShowCreate(false)
      setForm({ name: '', description: '' })
      addToast('success', 'Pack created')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const assign = useMutation({
    mutationFn: () => assignPackToClass(assignTarget!, selectedClass),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packs'] })
      setAssignTarget(null)
      setSelectedClass('')
      addToast('success', 'Pack assigned to class')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const packBindings = useQuery({
    queryKey: ['pack-bindings', resTarget],
    queryFn: () => fetchPackResourceBindings(resTarget!),
    enabled: !!resTarget,
  })

  const saveBindings = useMutation({
    mutationFn: () => {
      const current = packBindings.data ?? []
      const updated = [...current, { dimension_key: resInput.dimension_key, allowed_value: resInput.allowed_value }]
      return setPackResourceBindings(resTarget!, updated.map(b => ({ dimension_key: b.dimension_key, allowed_value: b.allowed_value })))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pack-bindings', resTarget] })
      setResInput({ dimension_key: '', allowed_value: '' })
      addToast('success', 'Binding added')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const removeBinding = useMutation({
    mutationFn: (bindingId: string) => {
      const current = packBindings.data ?? []
      const updated = current.filter(b => b.id !== bindingId)
      return setPackResourceBindings(resTarget!, updated.map(b => ({ dimension_key: b.dimension_key, allowed_value: b.allowed_value })))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pack-bindings', resTarget] })
      addToast('success', 'Binding removed')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Capability Packs</h1>
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
          Create Pack
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <PageState query={packs}>
          {data => data.length === 0 ? (
            <div className="col-span-full text-center py-12 text-gray-500">No capability packs yet. Create one to get started.</div>
          ) : (
            data.map((pack: CapabilityPack) => (
              <div key={pack.id} className="bg-white rounded-xl p-6 shadow-sm">
                <h3 className="font-semibold text-lg mb-1">{pack.name}</h3>
                <p className="text-sm text-gray-500 mb-4">{pack.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">
                    {pack.capabilities?.length || 0} capabilities
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => setResTarget(pack.id)}
                      className="text-sm text-blue-500 hover:underline">
                      Bindings
                    </button>
                    <button onClick={() => setAssignTarget(pack.id)}
                      className="text-sm text-blue-500 hover:underline">
                      Assign to class
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </PageState>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Capability Pack"
        onConfirm={() => create.mutate()} confirmDisabled={!form.name} loading={create.isPending}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input type="text" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg" autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg" rows={3} />
          </div>
        </div>
      </Modal>

      <Modal open={!!assignTarget} onClose={() => setAssignTarget(null)} title="Assign to Agent Class"
        onConfirm={() => assign.mutate()} confirmDisabled={!selectedClass} loading={assign.isPending}
        confirmLabel="Assign">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Agent Class</label>
          <select value={selectedClass} onChange={e => setSelectedClass(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg">
            <option value="">Select a class...</option>
            {classes.data?.map((c: { id: string; name: string }) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </Modal>

      <Modal open={!!resTarget} onClose={() => { setResTarget(null); setResInput({ dimension_key: '', allowed_value: '' }) }}
        title="Pack Resource Bindings" size="lg">
        <div className="space-y-4">
          {resTarget && <PackBreadthWarning packId={resTarget} variant="banner" />}
          {packBindings.isLoading && <p className="text-gray-500">Loading bindings...</p>}
          {packBindings.data && packBindings.data.length === 0 && (
            <p className="text-gray-400 text-sm">No resource bindings. This pack has unrestricted resource access.</p>
          )}
          {packBindings.data?.map((b: ResourceBinding) => (
            <div key={b.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <span className="font-mono text-sm font-medium">{b.dimension_key}</span>
                <span className="text-gray-500 text-sm ml-2">= {b.allowed_value}</span>
              </div>
              <button onClick={() => removeBinding.mutate(b.id)}
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
              <button onClick={() => saveBindings.mutate()}
                disabled={!resInput.dimension_key || !resInput.allowed_value || saveBindings.isPending}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 disabled:opacity-50">Add</button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
