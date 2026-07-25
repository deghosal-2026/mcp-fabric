import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ToastProvider } from '../components/shared/Toast'
import { PacksPage } from './Packs'
import { fetchPacks, createPack, fetchAgentClasses, assignPackToClass } from '../api/client'

vi.mock('../api/client', () => ({
  fetchPacks: vi.fn(),
  createPack: vi.fn(),
  fetchAgentClasses: vi.fn(),
  assignPackToClass: vi.fn(),
}))

const mockFetchPacks = vi.mocked(fetchPacks)
const mockCreatePack = vi.mocked(createPack)
const mockFetchAgentClasses = vi.mocked(fetchAgentClasses)
const mockAssignPackToClass = vi.mocked(assignPackToClass)

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

const mockPacks = [
  { id: 'p-1', name: 'Developer Tools', description: 'Code review and deployment tools', team_namespace: 'eng', capabilities: [{ id: 'c-1', name: 'code-review' }] },
  { id: 'p-2', name: 'Data Pipelines', description: 'ETL and data processing', team_namespace: 'data', capabilities: [] },
]

const mockClasses = [
  { id: 'cls-1', name: 'developer-agent', description: 'Dev agent class', team_namespace: 'eng' },
  { id: 'cls-2', name: 'data-agent', description: 'Data agent class', team_namespace: 'data' },
]

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchPacks.mockResolvedValue(mockPacks as any)
  mockFetchAgentClasses.mockResolvedValue(mockClasses as any)
})

describe('PacksPage', () => {
  it('renders pack cards with name and description', async () => {
    renderWithProviders(<PacksPage />)
    await waitFor(() => {
      expect(screen.getByText('Developer Tools')).toBeInTheDocument()
    })
    expect(screen.getByText('Code review and deployment tools')).toBeInTheDocument()
    expect(screen.getByText('Data Pipelines')).toBeInTheDocument()
    expect(screen.getByText('ETL and data processing')).toBeInTheDocument()
  })

  it('create modal submits', async () => {
    mockCreatePack.mockResolvedValue({} as any)
    renderWithProviders(<PacksPage />)
    await userEvent.click(screen.getByText('Create Pack'))

    const inputs = screen.getAllByRole('textbox')
    await userEvent.type(inputs[0], 'Security Tools')
    await userEvent.type(inputs[1], 'Security scanning tools')

    await userEvent.click(screen.getByText('Save'))
    await waitFor(() => {
      expect(mockCreatePack).toHaveBeenCalledWith({
        name: 'Security Tools',
        description: 'Security scanning tools',
      })
    })
  })

  it('assign modal opens and submits with selected class', async () => {
    mockAssignPackToClass.mockResolvedValue({} as any)
    renderWithProviders(<PacksPage />)
    const assignButtons = await screen.findAllByText('Assign to class')
    await userEvent.click(assignButtons[0])

    expect(screen.getByText('Assign to Agent Class')).toBeInTheDocument()

    const select = screen.getByRole('combobox')
    await userEvent.selectOptions(select, 'cls-1')

    await userEvent.click(screen.getByText('Assign'))
    await waitFor(() => {
      expect(mockAssignPackToClass).toHaveBeenCalledWith('p-1', 'cls-1')
    })
  })
})
