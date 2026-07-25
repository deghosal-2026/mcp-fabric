import type { ReactNode } from 'react'

interface PageStateProps<T> {
  query: { data?: T; isLoading: boolean; error: Error | null; refetch: () => void };
  children: (data: T) => ReactNode;
  loadingRows?: number;
}

export function PageState<T>({ query, children, loadingRows }: PageStateProps<T>) {
  if (query.isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        {Array.from({ length: loadingRows ?? 3 }).map((_, i) => (
          <div key={i} className="h-12 bg-gray-200 rounded-lg" />
        ))}
      </div>
    )
  }

  if (query.error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 text-lg font-medium mb-2">Error</div>
        <p className="text-gray-600 mb-4">{query.error.message}</p>
        <button
          onClick={() => query.refetch()}
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!query.data) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400 text-4xl mb-4">📭</p>
        <p className="text-gray-600">No data available</p>
      </div>
    )
  }

  return <>{children(query.data)}</>
}
