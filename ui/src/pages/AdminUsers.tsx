import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAdminUsers, inviteUser, deactivateUser } from '../api/client'
import { Table } from '../components/shared/Table'
import { Modal } from '../components/shared/Modal'
import { Badge } from '../components/shared/Badge'
import { PageState } from '../components/shared/PageState'
import { useAuthStore } from '../stores/authStore'
import { useToast } from '../components/shared/Toast'
import type { LegacyColumnDef as ColumnDef } from '@tanstack/react-table/legacy'
import type { AdminUser } from '../types'

export function AdminUsersPage() {
  const [showInvite, setShowInvite] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', role: 'editor' })
  const currentUser = useAuthStore(s => s.user)
  const queryClient = useQueryClient()
  const { addToast } = useToast()

  const users = useQuery({
    queryKey: ['admin-users'],
    queryFn: fetchAdminUsers,
  })

  const invite = useMutation({
    mutationFn: () => inviteUser(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setShowInvite(false)
      setForm({ username: '', email: '', role: 'editor' })
      addToast('success', 'User invited')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const deactivate = useMutation({
    mutationFn: (id: string) => deactivateUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      addToast('success', 'User deactivated')
    },
    onError: (err: Error) => addToast('error', err.message),
  })

  const columns: ColumnDef<AdminUser>[] = [
    { header: 'Username', accessorKey: 'username' },
    { header: 'Email', accessorKey: 'email' },
    {
      header: 'Role',
      accessorKey: 'role',
      cell: ({ getValue }) => <Badge label={getValue() as string} variant={getValue() as string} />,
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: ({ getValue }) => <Badge label={getValue() as string} />,
    },
    {
      header: 'MFA',
      accessorKey: 'mfa_enabled',
      cell: ({ getValue }) => getValue() ? <span className="text-green-600">Enabled</span> : <span className="text-gray-400">Disabled</span>,
    },
    {
      header: 'Actions',
      cell: ({ row }) => (
        row.original.status === 'active' && row.original.id !== currentUser?.id ? (
          <button onClick={e => { e.stopPropagation(); deactivate.mutate(row.original.id) }}
            className="text-sm text-red-500 hover:underline">Deactivate</button>
        ) : null
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Admin Users</h1>
        <button onClick={() => setShowInvite(true)}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
          Invite User
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm">
        <PageState query={users}>
          {data => <Table data={data} columns={columns} />}
        </PageState>
      </div>

      <Modal open={showInvite} onClose={() => setShowInvite(false)} title="Invite User"
        onConfirm={() => invite.mutate()} confirmDisabled={!form.username || !form.email} loading={invite.isPending}
        confirmLabel="Send Invite">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input type="text" value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg" autoFocus />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
            <select value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg">
              <option value="admin">Admin</option>
              <option value="editor">Editor</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
        </div>
      </Modal>
    </div>
  )
}
