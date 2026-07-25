import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchDashboard, fetchServers, fetchApprovals, fetchAuditEvents } from '../api/client'
import { Badge } from '../components/shared/Badge'
import { PageState } from '../components/shared/PageState'

export function DashboardPage() {
  const stats = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => fetchDashboard(),
  })

  const servers = useQuery({
    queryKey: ['servers', 'recent'],
    queryFn: () => fetchServers({ per_page: '5' }),
  })

  const approvals = useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: () => fetchApprovals({ status: 'pending', per_page: '5' }),
  })

  const audit = useQuery({
    queryKey: ['audit', 'recent'],
    queryFn: () => fetchAuditEvents({ per_page: '5' }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <PageState query={stats}>
        {data => (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="text-sm text-gray-500 mb-1">Servers</div>
              <div className="text-3xl font-bold">{data.server_count}</div>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="text-sm text-gray-500 mb-1">Healthy</div>
              <div className="text-3xl font-bold text-green-600">{data.healthy_servers}</div>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="text-sm text-gray-500 mb-1">Pending Approvals</div>
              <div className="text-3xl font-bold text-yellow-600">{data.pending_approvals}</div>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="text-sm text-gray-500 mb-1">Degraded Servers</div>
              <div className="text-3xl font-bold text-red-600">{data.degraded_servers}</div>
            </div>
          </div>
        )}
      </PageState>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h2 className="font-semibold">Recent Servers</h2>
            <Link to="/servers" className="text-sm text-blue-500 hover:underline">View all</Link>
          </div>
          <PageState query={servers}>
            {data => (
              <div className="divide-y">
                {(data.items ?? (data as any).servers ?? []).map(s => (
                  <Link key={s.id} to={`/servers/${s.id}`} className="flex items-center justify-between px-6 py-3 hover:bg-gray-50">
                    <span className="font-medium">{s.name}</span>
                    <Badge label={s.health_status} />
                  </Link>
                ))}
              </div>
            )}
          </PageState>
        </div>

        <div className="bg-white rounded-xl shadow-sm">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h2 className="font-semibold">Pending Approvals</h2>
            <Link to="/approvals" className="text-sm text-blue-500 hover:underline">View all</Link>
          </div>
          <PageState query={approvals}>
            {data => (
              <div className="divide-y">
                {(() => {
                  const items = data.items ?? (data as any).approvals ?? []
                  if (items.length === 0) {
                    return <p className="px-6 py-4 text-gray-500 text-sm">No pending approvals</p>
                  }
                  return items.map(a => (
                    <Link key={a.id} to="/approvals" className="block px-6 py-3 hover:bg-gray-50">
                      <div className="font-medium text-sm">{a.capability_name || a.capability_id}</div>
                      <div className="text-xs text-gray-500 mt-1">{a.agent_name || a.agent_identity_id}</div>
                    </Link>
                  ))
                })()}
              </div>
            )}
          </PageState>
        </div>

        <div className="bg-white rounded-xl shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <h2 className="font-semibold">Recent Audit Events</h2>
            <Link to="/audit" className="text-sm text-blue-500 hover:underline">View all</Link>
          </div>
          <PageState query={audit}>
            {data => (
              <div className="divide-y">
                {(data.items ?? (data as any).events ?? []).slice(0, 5).map(e => (
                  <div key={e.id} className="px-6 py-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-sm">{e.event_type}</span>
                      <span className="text-xs text-gray-500">{new Date(e.created_at).toLocaleString()}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Actor: {e.actor_id}</div>
                  </div>
                ))}
              </div>
            )}
          </PageState>
        </div>
      </div>
    </div>
  )
}
