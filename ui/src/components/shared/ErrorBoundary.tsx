import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="text-center py-12">
            <div className="text-red-500 text-lg font-medium mb-2">Something went wrong</div>
            <p className="text-gray-600 text-sm">{this.state.error?.message}</p>
            <div className="flex items-center justify-center gap-3 mt-4">
              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Try again
              </button>
              <a
                href="/"
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Go to Dashboard
              </a>
            </div>
          </div>
        )
      )
    }
    return this.props.children
  }
}
