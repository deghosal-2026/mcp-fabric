import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchServers, fetchAgentClasses, setTrustAssignment } from '../api/client'
import { Badge } from '../components/shared/Badge'
import { PageState } from '../components/shared/PageState'
import { useToast } from '../components/shared/Toast'
import type { MCPServer } from '../types'

export function TrustPosturePage() {
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const servers = useQuery({
    queryKey: ['servers', 'all'],
    queryFn: () => fetchServers({ per_page: '200' }),
  })

  const classes = useQuery({
    queryKey: ['agent-classes', 'trust-posture'],
    queryFn: fetchAgentClasses,
  })

  const updateTrust = useMutation({
    mutationFn: ({ serverId, trustLevel }: { serverId: string; trustLevel: string }) =>
      setTrustAssignment(selectedClassId, serverId, trustLevel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servers'] })
      addToast('success', 'Trust level updated')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const trustColors: Record<string, string> = {
    trusted: 'border-green-500 bg-green-50',
    restricted: 'border-yellow-500 bg-yellow-50',
    'approval-gated': 'border-orange-500 bg-orange-50',
    unreviewed: 'border-red-500 bg-red-100',
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Trust Posture</h1>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">Agent Class:</label>
          <PageState query={classes}>
            {data => (
              <select
                value={selectedClassId}
                onChange={e => setSelectedClassId(e.target.value)}
                className="px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select a class...</option>
                {data.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            )}
          </PageState>
        </div>
      </div>

      <PageState query={servers}>
        {data => (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.items.map((server: MCPServer) => (
              <div key={server.id} className={`rounded-xl p-6 shadow-sm border-l-4 ${trustColors[server.trust_level] || 'border-gray-300'}`}>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold">{server.name}</h3>
                    <p className="text-xs text-gray-500 mt-1">{server.endpoint}</p>
                  </div>
                  <Badge label={server.trust_level} />
                </div>
                <div className="flex items-center gap-2 mb-3">
                  <Badge label={server.health_status} />
                  <span className="text-xs text-gray-400">{server.owner_team}</span>
                </div>
                <select
                  value={server.trust_level}
                  onChange={e => { if (selectedClassId) updateTrust.mutate({ serverId: server.id, trustLevel: e.target.value }) }}
                  className="w-full px-2 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="trusted">Trusted</option>
                  <option value="restricted">Restricted</option>
                  <option value="approval-gated">Approval Gated</option>
                  <option value="unreviewed">Unreviewed</option>
                </select>
                {server.trust_level === 'unreviewed' && (
                  <div className="mt-2 text-xs text-red-600 font-medium">⚠ Needs review</div>
                )}
              </div>
            ))}
          </div>
        )}
      </PageState>
    </div>
  )
}
