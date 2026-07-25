import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from './Login'
import { login, verifyMfa } from '../api/client'
import { useAuthStore } from '../stores/authStore'

vi.mock('../api/client', () => ({
  login: vi.fn(),
  verifyMfa: vi.fn(),
}))

const mockLogin = vi.mocked(login)
const mockVerifyMfa = vi.mocked(verifyMfa)

const mockStoreLogin = vi.fn()
vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

const mockUseAuthStore = vi.mocked(useAuthStore)

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/login']}>{ui}</MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockUseAuthStore.mockImplementation((selector?: (s: any) => any) => {
    const state = { login: mockStoreLogin, user: null, token: null, logout: vi.fn(), isAuthenticated: vi.fn() }
    return selector ? selector(state) : state
  })
})

describe('LoginPage', () => {
  it('renders username and password inputs, submit disabled when empty', () => {
    renderWithProviders(<LoginPage />)
    const inputs = screen.getAllByRole('textbox')
    expect(inputs[0]).toBeInTheDocument()
    expect(screen.getByText('Password')).toBeInTheDocument()
    const passwordInput = document.querySelector('input[type="password"]')
    expect(passwordInput).toBeInTheDocument()

    const submitButton = screen.getByRole('button', { name: /login/i })
    expect(submitButton).toBeDisabled()
  })

  it('submit calls login() with username and password', async () => {
    mockLogin.mockResolvedValue({
      token: 'tok-1',
      user: { id: 'u-1', username: 'admin', role: 'admin', team_namespace: 'eng', mfa_enabled: false },
      mfa_required: false,
    })

    renderWithProviders(<LoginPage />)
    const usernameInput = screen.getAllByRole('textbox')[0]
    const passwordInput = document.querySelector('input[type="password"]')!
    await userEvent.type(usernameInput, 'admin')
    await userEvent.type(passwordInput, 'secret')

    const submitButton = screen.getByRole('button', { name: /login/i })
    expect(submitButton).not.toBeDisabled()

    await userEvent.click(submitButton)
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin', 'secret')
    })
  })

  it('shows error message on API failure', async () => {
    mockLogin.mockRejectedValue(new Error('Invalid credentials'))

    renderWithProviders(<LoginPage />)
    const usernameInput = screen.getAllByRole('textbox')[0]
    const passwordInput = document.querySelector('input[type="password"]')!
    await userEvent.type(usernameInput, 'admin')
    await userEvent.type(passwordInput, 'wrong')

    await userEvent.click(screen.getByRole('button', { name: /login/i }))
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('MFA flow: login returns mfa_required=true -> MFA form replaces login form', async () => {
    mockLogin.mockResolvedValue({
      token: 'mfa-token',
      user: { id: 'u-1', username: 'admin', role: 'admin', team_namespace: 'eng', mfa_enabled: true },
      mfa_required: true,
    })

    renderWithProviders(<LoginPage />)
    const usernameInput = screen.getAllByRole('textbox')[0]
    const passwordInput = document.querySelector('input[type="password"]')!
    await userEvent.type(usernameInput, 'admin')
    await userEvent.type(passwordInput, 'secret')
    await userEvent.click(screen.getByRole('button', { name: /login/i }))

    await waitFor(() => {
      expect(screen.getByText('Authentication Code')).toBeInTheDocument()
    })
    expect(screen.getByPlaceholderText('Enter 6-digit code')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /verify/i })).toBeInTheDocument()
    expect(screen.queryByText('Username')).toBeNull()
  })

  it('MFA verify: calls verifyMfa, then authStore.login, then navigates to /', async () => {
    const authUser = { id: 'u-1', username: 'admin', role: 'admin', team_namespace: 'eng', mfa_enabled: true }
    mockLogin.mockResolvedValue({
      token: 'mfa-token',
      user: authUser,
      mfa_required: true,
    })
    mockVerifyMfa.mockResolvedValue({
      token: 'final-token',
      user: authUser,
    })

    renderWithProviders(<LoginPage />)
    const usernameInput = screen.getAllByRole('textbox')[0]
    const passwordInput = document.querySelector('input[type="password"]')!
    await userEvent.type(usernameInput, 'admin')
    await userEvent.type(passwordInput, 'secret')
    await userEvent.click(screen.getByRole('button', { name: /login/i }))

    await waitFor(() => {
      expect(screen.getByText('Authentication Code')).toBeInTheDocument()
    })

    await userEvent.type(screen.getByPlaceholderText('Enter 6-digit code'), '123456')
    await userEvent.click(screen.getByRole('button', { name: /verify/i }))

    await waitFor(() => {
      expect(mockVerifyMfa).toHaveBeenCalledWith('mfa-token', '123456')
      expect(mockStoreLogin).toHaveBeenCalledWith('final-token', authUser)
    })
  })
})
