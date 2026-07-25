import { useState, useCallback } from 'react'

interface FilterOption {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}

interface FilterBarProps {
  filters: FilterOption[];
  onFilter: (filters: Record<string, string>) => void;
  searchPlaceholder?: string;
}

export function FilterBar({ filters, onFilter, searchPlaceholder }: FilterBarProps) {
  const [search, setSearch] = useState('')
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({})
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null)

  const handleSearch = useCallback((value: string) => {
    setSearch(value)
    if (debounceTimer) clearTimeout(debounceTimer)
    const timer = setTimeout(() => {
      void onFilter({ ...activeFilters, q: value || '' })
    }, 300)
    setDebounceTimer(timer)
  }, [activeFilters, onFilter, debounceTimer])

  const handleFilterChange = (key: string, value: string) => {
    const next = { ...activeFilters, [key]: value }
    setActiveFilters(next)
    void onFilter({ ...next, q: search || '' })
  }

  const clearAll = () => {
    setSearch('')
    setActiveFilters({})
    onFilter({})
  }

  const hasActiveFilters = Object.values(activeFilters).some(Boolean) || search

  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <input
        type="text"
        value={search}
        onChange={e => handleSearch(e.target.value)}
        placeholder={searchPlaceholder || 'Search...'}
        className="px-3 py-2 border rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {filters.map(filter => (
        <select
          key={filter.key}
          value={activeFilters[filter.key] || ''}
          onChange={e => handleFilterChange(filter.key, e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{filter.label}</option>
          {filter.options.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      ))}
      {hasActiveFilters && (
        <button
          onClick={clearAll}
          className="text-sm text-red-500 hover:text-red-700"
        >
          Clear all
        </button>
      )}
    </div>
  )
}
