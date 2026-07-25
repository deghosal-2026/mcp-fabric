import { useAuthStore } from '../../stores/authStore'
import { useNavigate } from 'react-router-dom'

export function TopBar() {
  const user = useAuthStore(s => s.user)
  const logout = useAuthStore(s => s.logout)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="text-sm text-gray-500">
        Welcome, <span className="font-medium text-gray-900">{user?.username}</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-600">{user?.role}</span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-600 transition-colors"
        >
          Logout
        </button>
      </div>
    </header>
  )
}
