import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { ErrorBoundary } from './ErrorBoundary'

function BuggyComponent({ message = 'Intentional crash' }: { message?: string }) {
  throw new Error(message)
}

function SafeComponent() {
  return <div data-testid="safe-child">All good</div>
}

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ErrorBoundary', () => {
  it('renders children normally when no error', () => {
    render(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('safe-child')).toBeInTheDocument()
  })

  it('catches thrown error and shows fallback', () => {
    render(
      <ErrorBoundary>
        <BuggyComponent />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('shows error message in fallback', () => {
    render(
      <ErrorBoundary>
        <BuggyComponent message='Test error message' />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Test error message')).toBeInTheDocument()
  })

  it('"Try again" resets error state and re-renders children', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <BuggyComponent />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()

    const tryAgain = screen.getByText('Try again')
    tryAgain.click()

    rerender(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('safe-child')).toBeInTheDocument()
  })

  it('"Go to Dashboard" link has href="/"', () => {
    render(
      <ErrorBoundary>
        <BuggyComponent />
      </ErrorBoundary>,
    )
    const link = screen.getByText('Go to Dashboard')
    expect(link).toHaveAttribute('href', '/')
  })

  it('custom fallback prop overrides default', () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom error UI</div>}>
        <BuggyComponent />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument()
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
  })

  it('componentDidCatch logs to console.error', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <BuggyComponent message='Log test' />
      </ErrorBoundary>,
    )

    expect(errorSpy).toHaveBeenCalled()

    const boundaryCall = errorSpy.mock.calls.find(
      c => typeof c[0] === 'string' && c[0].includes('ErrorBoundary caught:'),
    )
    expect(boundaryCall).toBeDefined()
    expect(boundaryCall![1].message).toBe('Log test')
  })
})
