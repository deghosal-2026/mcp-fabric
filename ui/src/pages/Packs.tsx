import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPacks, createPack, assignPackToClass, fetchAgentClasses } from '../api/client'
import { Modal } from '../components/shared/Modal'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { CapabilityPack } from '../types'

export function PacksPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [assignTarget, setAssignTarget] = useState<string | null>(null)
  const [selectedClass, setSelectedClass] = useState('')
  const [form, setForm] = useState({ name: '', description: '' })
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
                  <button onClick={() => setAssignTarget(pack.id)}
                    className="text-sm text-blue-500 hover:underline">
                    Assign to class
                  </button>
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
    </div>
  )
}
