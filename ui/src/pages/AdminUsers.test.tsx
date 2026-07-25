import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { AdminUsersPage } from './AdminUsers'
import { fetchAdminUsers, inviteUser, deactivateUser } from '../api/client'
import { useAuthStore } from '../stores/authStore'

vi.mock('../api/client', () => ({
  fetchAdminUsers: vi.fn(),
  inviteUser: vi.fn(),
  deactivateUser: vi.fn(),
}))

const mockFetchAdminUsers = vi.mocked(fetchAdminUsers)
const mockInviteUser = vi.mocked(inviteUser)
const mockDeactivateUser = vi.mocked(deactivateUser)

const mockStoreUser = { id: 'u-1', username: 'alice', role: 'admin' as const, team_namespace: 'eng', mfa_enabled: true, status: 'active' as const, email: 'alice@example.com', created_at: '2025-01-01T00:00:00Z' }

vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

const mockUseAuthStore = vi.mocked(useAuthStore)

function renderWithProviders(ui: React.ReactElement) {
  const testQueryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={testQueryClient}>
      <ToastProvider>
        <BrowserRouter>{ui}</BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}

const mockUsers = [
  { id: 'u-1', username: 'alice', email: 'alice@example.com', role: 'admin', team_namespace: 'eng', mfa_enabled: true, status: 'active', created_at: '2025-01-01T00:00:00Z' },
  { id: 'u-2', username: 'bob', email: 'bob@example.com', role: 'editor', team_namespace: 'eng', mfa_enabled: false, status: 'active', created_at: '2025-01-02T00:00:00Z' },
  { id: 'u-3', username: 'charlie', email: 'charlie@example.com', role: 'viewer', team_namespace: 'data', mfa_enabled: false, status: 'deactivated', created_at: '2025-01-03T00:00:00Z' },
]

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchAdminUsers.mockResolvedValue(mockUsers as any)
  mockUseAuthStore.mockImplementation((selector?: (s: any) => any) => {
    const state = { user: mockStoreUser }
    return selector ? selector(state) : state
  })
})

describe('AdminUsersPage', () => {
  it('renders user table with username, email, role, status, MFA', async () => {
    renderWithProviders(<AdminUsersPage />)
    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument()
    })
    expect(screen.getByText('alice@example.com')).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getAllByText('active').length).toBe(2)
    expect(screen.getByText('Enabled')).toBeInTheDocument()

    expect(screen.getByText('bob')).toBeInTheDocument()
    expect(screen.getByText('editor')).toBeInTheDocument()
    expect(screen.getAllByText('Disabled').length).toBe(2)
  })

  it('invite modal submits with username, email, role', async () => {
    mockInviteUser.mockResolvedValue({} as any)
    renderWithProviders(<AdminUsersPage />)
    await userEvent.click(screen.getByRole('button', { name: /invite user/i }))
    expect(screen.getByRole('heading', { name: /invite user/i })).toBeInTheDocument()

    const inputs = screen.getAllByRole('textbox')
    const select = screen.getByRole('combobox')
    await userEvent.type(inputs[0], 'newuser')
    await userEvent.type(inputs[1], 'newuser@example.com')
    await userEvent.selectOptions(select, 'viewer')

    await userEvent.click(screen.getByText('Send Invite'))
    await waitFor(() => {
      expect(mockInviteUser).toHaveBeenCalledWith({
        username: 'newuser',
        email: 'newuser@example.com',
        role: 'viewer',
      })
    })
  })

  it('deactivate button calls deactivateUser', async () => {
    mockDeactivateUser.mockResolvedValue({} as any)
    renderWithProviders(<AdminUsersPage />)
    const deactivateButtons = await screen.findAllByText('Deactivate')
    expect(deactivateButtons).toHaveLength(1)
    await userEvent.click(deactivateButtons[0])
    await waitFor(() => {
      expect(mockDeactivateUser).toHaveBeenCalledWith('u-2')
    })
  })
})
