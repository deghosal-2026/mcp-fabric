import type { ColumnDef, Row } from '@tanstack/react-table'
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useMemo } from 'react'

interface TableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  onRowClick?: (row: Row<T>) => void;
  pagination?: {
    nextCursor?: string;
    hasMore: boolean;
    total: number;
    onNext?: () => void;
    onPrev?: () => void;
    cursor?: string;
  };
}

export function Table<T extends object>({
  data,
  columns,
  onRowClick,
  pagination,
}: TableProps<T>) {
  const tableData = useMemo(() => data, [data])
  const tableCols = useMemo(() => columns, [columns])

  const table = useReactTable({
    data: tableData,
    columns: tableCols,
    getCoreRowModel: getCoreRowModel<T>(),
    manualPagination: true,
  })

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          {table.getHeaderGroups().map(headerGroup => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map(header => (
                <th
                  key={header.id}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {table.getRowModel().rows.map(row => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              className={onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}
            >
              {row.getVisibleCells().map(cell => (
                <td key={cell.id} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {pagination && (
        <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50">
          <span className="text-sm text-gray-700">
            Total: {pagination.total}
          </span>
          <div className="flex gap-2">
            {pagination.onPrev && (
              <button
                onClick={pagination.onPrev}
                className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50"
              >
                Previous
              </button>
            )}
            {pagination.hasMore && pagination.onNext && (
              <button
                onClick={pagination.onNext}
                className="px-3 py-1 text-sm border rounded hover:bg-gray-100"
              >
                Next
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
