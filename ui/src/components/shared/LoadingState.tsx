export function LoadingState({ rows = 3 }: { rows?: number }) {
  return (
    <div data-testid="loading-state" className="space-y-4 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 bg-gray-200 rounded-lg" />
      ))}
    </div>
  )
}
