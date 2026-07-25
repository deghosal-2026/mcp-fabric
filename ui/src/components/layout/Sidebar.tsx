import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '🏠', roles: ['admin', 'editor', 'viewer'] },
  { to: '/servers', label: 'Servers', icon: '🖥️', roles: ['admin', 'editor', 'viewer'] },
  { to: '/capabilities', label: 'Capabilities', icon: '🧩', roles: ['admin', 'editor', 'viewer'] },
  { to: '/agent-classes', label: 'Agent Classes', icon: '🤖', roles: ['admin', 'editor'] },
  { to: '/policies', label: 'Policies', icon: '🔒', roles: ['admin', 'editor'] },
  { to: '/audit', label: 'Audit Log', icon: '📋', roles: ['admin', 'editor', 'viewer'] },
  { to: '/approvals', label: 'Approvals', icon: '✅', roles: ['admin', 'editor'] },
  { to: '/packs', label: 'Capability Packs', icon: '📦', roles: ['admin', 'editor'] },
  { to: '/alerts', label: 'Alerts', icon: '🔔', roles: ['admin', 'editor', 'viewer'] },
  { to: '/admin/users', label: 'Admin Users', icon: '👥', roles: ['admin'] },
  { to: '/trust', label: 'Trust Posture', icon: '🛡️', roles: ['admin', 'editor', 'viewer'] },
]

export function Sidebar() {
  const user = useAuthStore(s => s.user)

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-screen">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold">MCP Fabric</h1>
        <p className="text-xs text-gray-400 mt-1">Admin Console</p>
      </div>
      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {navItems
          .filter(item => user && item.roles.includes(user.role))
          .map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
      </nav>
    </aside>
  )
}
