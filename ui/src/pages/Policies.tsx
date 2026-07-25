import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPolicies, deployPolicy } from '../api/client'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'

export function PoliciesPage() {
  const [regoContent, setRegoContent] = useState('')
  const [showEditor, setShowEditor] = useState(false)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const policies = useQuery({
    queryKey: ['policies'],
    queryFn: fetchPolicies,
  })

  const deploy = useMutation({
    mutationFn: () => deployPolicy(regoContent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] })
      addToast('success', 'Policy deployed')
      setShowEditor(false)
      setRegoContent('')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Policy Editor</h1>
        <button
          onClick={() => setShowEditor(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          New Policy
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <PageState query={policies}>
          {data => (
            <div className="space-y-4">
              {data.map((p: { id: string; version: string; deployed_at: string }) => (
                <div key={p.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <div className="font-medium">v{p.version}</div>
                    <div className="text-sm text-gray-500">{new Date(p.deployed_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </PageState>
      </div>

      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h2 className="text-lg font-semibold">Edit Rego Policy</h2>
              <button onClick={() => setShowEditor(false)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="p-6">
              <textarea
                value={regoContent}
                onChange={e => setRegoContent(e.target.value)}
                className="w-full h-96 font-mono text-sm border rounded-lg p-4"
                placeholder="package fabric.policy&#10;&#10;default allow := false&#10;..."
              />
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t bg-gray-50 rounded-b-xl">
              <button onClick={() => setShowEditor(false)} className="px-4 py-2 text-sm border rounded-lg">Cancel</button>
              <button
                onClick={() => deploy.mutate()}
                disabled={!regoContent || deploy.isPending}
                className="px-4 py-2 text-sm text-white bg-blue-500 rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {deploy.isPending ? 'Deploying...' : 'Deploy'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
