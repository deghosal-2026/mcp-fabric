const colorMap: Record<string, string> = {
  trusted: 'bg-green-100 text-green-800',
  restricted: 'bg-yellow-100 text-yellow-800',
  'approval-gated': 'bg-orange-100 text-orange-800',
  unreviewed: 'bg-red-100 text-red-800',
  healthy: 'bg-green-100 text-green-800',
  degraded: 'bg-yellow-100 text-yellow-800',
  unhealthy: 'bg-red-100 text-red-800',
  active: 'bg-green-100 text-green-800',
  deprecated: 'bg-gray-100 text-gray-800',
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  denied: 'bg-red-100 text-red-800',
  admin: 'bg-purple-100 text-purple-800',
  editor: 'bg-blue-100 text-blue-800',
  viewer: 'bg-gray-100 text-gray-800',
}

interface BadgeProps {
  label: string;
  variant?: string;
}

export function Badge({ label, variant }: BadgeProps) {
  const className = colorMap[variant || label] || 'bg-gray-100 text-gray-800'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium truncate max-w-[200px] ${className}`}>
      {label}
    </span>
  )
}
