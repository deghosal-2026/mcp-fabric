import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPackBreadth } from '../../api/client'
import type { PackBreadthRow } from '../../types'

function riskTier(cr: number): { label: string; color: string } {
  if (cr >= 0.95) return { label: 'Low', color: 'bg-green-100 text-green-800' }
  if (cr >= 0.80) return { label: 'Medium', color: 'bg-yellow-100 text-yellow-800' }
  if (cr >= 0.50) return { label: 'High', color: 'bg-orange-100 text-orange-800' }
  return { label: 'Critical', color: 'bg-red-100 text-red-800' }
}

type RiskFilter = 'all' | 'low' | 'medium' | 'high' | 'critical'

export function PackBreadthCard() {
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('all')
  const [sortAsc, setSortAsc] = useState(true)

  const { data, isLoading } = useQuery({
    queryKey: ['pack-breadth'],
    queryFn: fetchPackBreadth,
  })

  const filtered = useMemo(() => {
    if (!data) return []
    let rows = [...data]
    if (riskFilter !== 'all') {
      rows = rows.filter(r => riskTier(r.catch_rate).label.toLowerCase() === riskFilter)
    }
    rows.sort((a, b) =>
      sortAsc ? a.catch_rate - b.catch_rate : b.catch_rate - a.catch_rate
    )
    return rows
  }, [data, riskFilter, sortAsc])

  const filters: { key: RiskFilter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'low', label: 'Low' },
    { key: 'medium', label: 'Medium' },
    { key: 'high', label: 'High' },
    { key: 'critical', label: 'Critical' },
  ]

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Identity-Binding Coverage</h2>
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {filters.map(f => (
              <button
                key={f.key}
                onClick={() => setRiskFilter(f.key)}
                className={`px-2 py-1 text-xs rounded ${riskFilter === f.key ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => setSortAsc(v => !v)}
            className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
            title={sortAsc ? 'Sorted by catch rate ascending' : 'Sorted by catch rate descending'}
          >
            {sortAsc ? '↑ Rate' : '↓ Rate'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />
      ) : !data || data.length === 0 ? (
        <div className="text-center py-8 text-gray-400 text-sm">
          No agent classes with pack assignments yet.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-2 font-medium text-gray-600">Agent Class</th>
                <th className="text-right px-4 py-2 font-medium text-gray-600">Packs</th>
                <th className="text-right px-4 py-2 font-medium text-gray-600">Resources Covered</th>
                <th className="text-right px-4 py-2 font-medium text-gray-600">Domain Total</th>
                <th className="text-right px-4 py-2 font-medium text-gray-600">Catch Rate</th>
                <th className="text-center px-4 py-2 font-medium text-gray-600">Risk</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row: PackBreadthRow) => {
                const risk = riskTier(row.catch_rate)
                return (
                  <tr key={row.agent_class_id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{row.agent_class_name}</td>
                    <td className="px-4 py-2 text-right">{row.pack_count}</td>
                    <td className="px-4 py-2 text-right">{row.resources_covered}</td>
                    <td className="px-4 py-2 text-right">{row.total_resources_in_domain}</td>
                    <td className="px-4 py-2 text-right font-mono">{(row.catch_rate * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${risk.color}`}
                        title={`Catch rate: ${(row.catch_rate * 100).toFixed(1)}%`}
                      >
                        {risk.label}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-gray-400 mt-2">
        Catch rate measures identity-bound protection — higher is better.
        See <a href="/docs/guides/pack-granularity.md" className="underline" target="_blank" rel="noopener noreferrer">pack granularity guide</a> for details.
      </p>
    </div>
  )
}
