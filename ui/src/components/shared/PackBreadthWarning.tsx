import { useQuery } from '@tanstack/react-query'
import { fetchPackSecurityMetrics } from '../../api/client'

const tierColors: Record<string, string> = {
  none: 'bg-green-100 text-green-800',
  full: 'bg-green-100 text-green-800',
  strong: 'bg-blue-100 text-blue-800',
  moderate: 'bg-yellow-100 text-yellow-800',
  reduced: 'bg-orange-100 text-orange-800',
  low: 'bg-red-100 text-red-800',
}

const tierLabels: Record<string, string> = {
  none: 'No resources — no risk',
  full: 'Full coverage — all domain resources included',
  strong: 'Strong coverage — catch rate ≥ 97%',
  moderate: 'Moderate coverage — catch rate ≥ 87%',
  reduced: 'Reduced coverage — catch rate ≥ 50%',
  low: 'Low coverage — catch rate < 50%',
}

const tierRecommendations: Record<string, string> = {
  none: 'Add resource bindings to enable identity-bound protection.',
  full: 'No action needed — this pack covers all resources in the domain.',
  strong: 'No action needed — protection is strong.',
  moderate: 'Consider splitting this pack into smaller, more granular packs to improve identity-bound protection.',
  reduced: 'Split this pack by environment, team, or resource type to improve security coverage.',
  low: 'Split this pack immediately. Large packs with low catch rates offer minimal protection against confused-deputy attacks.',
}

interface PackBreadthWarningProps {
  packId: string;
  variant?: 'badge' | 'banner';
}

export function PackBreadthWarning({ packId, variant = 'badge' }: PackBreadthWarningProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['pack-security-metrics', packId],
    queryFn: () => fetchPackSecurityMetrics(packId),
  })

  if (isLoading) {
    return variant === 'banner'
      ? <div className="h-12 bg-gray-100 rounded-lg animate-pulse" />
      : <span className="inline-block w-20 h-4 bg-gray-200 rounded animate-pulse" />
  }

  if (isError || !data) {
    return null
  }

  const tierClass = tierColors[data.warning_tier] || 'bg-gray-100 text-gray-800'
  const tierHint = tierLabels[data.warning_tier] || 'Unknown'
  const rec = tierRecommendations[data.warning_tier] || ''

  const tooltip = [
    `Catch rate: ${(data.implied_catch_rate * 100).toFixed(1)}%`,
    `Resources: ${data.resource_count} of ${data.total_resources_in_domain} in domain`,
    rec,
    'See docs/guides/pack-granularity.md for guidance',
  ].filter(Boolean).join(' · ')

  if (variant === 'banner') {
    return (
      <div className={`px-4 py-3 rounded-lg text-sm ${tierClass}`}>
        <div className="font-medium">{tierHint}</div>
        <div className="mt-1 opacity-80">
          Catch rate: {(data.implied_catch_rate * 100).toFixed(1)}% ({data.resource_count} of {data.total_resources_in_domain} resources)
        </div>
        {rec && <div className="mt-1 opacity-80">{rec}</div>}
        <a
          href="/docs/guides/pack-granularity.md"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-block underline opacity-80 hover:opacity-100"
        >
          Pack granularity guide →
        </a>
      </div>
    )
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium cursor-help ${tierClass}`}
      title={tooltip}
    >
      {tierHint}
    </span>
  )
}
