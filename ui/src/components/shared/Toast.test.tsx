import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { useEffect, type ReactNode } from 'react'
import { ToastProvider, useToast } from './Toast'

describe('Toast', () => {
  function renderWithToast(ui: ReactNode) {
    return render(<ToastProvider>{ui}</ToastProvider>)
  }

  it('renders message when addToast is called', async () => {
    function Trigger() {
      const { addToast } = useToast()
      return <button onClick={() => addToast('success', 'Saved!')}>fire</button>
    }
    renderWithToast(<Trigger />)
    await userEvent.click(screen.getByText('fire'))
    expect(screen.getByText('Saved!')).toBeInTheDocument()
  })

  it('correct color per type', async () => {
    function Trigger() {
      const { addToast } = useToast()
      return (
        <>
          <button onClick={() => addToast('success', 'ok')}>s</button>
          <button onClick={() => addToast('error', 'fail')}>e</button>
          <button onClick={() => addToast('info', 'msg')}>i</button>
        </>
      )
    }
    renderWithToast(<Trigger />)
    await userEvent.click(screen.getByText('s'))
    expect(screen.getByText('ok').className).toContain('bg-green-500')
    await userEvent.click(screen.getByText('e'))
    expect(screen.getByText('fail').className).toContain('bg-red-500')
    await userEvent.click(screen.getByText('i'))
    expect(screen.getByText('msg').className).toContain('bg-blue-500')
  })

  it('auto-dismisses after 5 seconds', async () => {
    vi.useFakeTimers()
    renderWithToast(
      <AutoFire message="Temp" />
    )
    act(() => { vi.advanceTimersByTime(0) })
    expect(screen.getByText('Temp')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(5000) })
    expect(screen.queryByText('Temp')).toBeNull()
    vi.useRealTimers()
  })

  it('multiple toasts stack', () => {
    function AutoFire() {
      const { addToast } = useToast()
      useEffect(() => {
        addToast('success', 'A')
        addToast('error', 'B')
        addToast('info', 'C')
      }, [addToast])
      return null
    }
    renderWithToast(<AutoFire />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('C')).toBeInTheDocument()
  })
})

function AutoFire({ message }: { message: string }) {
  const { addToast } = useToast()
  useEffect(() => { addToast('info', message) }, [addToast, message])
  return null
}
