import { Component, type ReactNode } from 'react'

interface State {
  error: Error | null
}

/** Last-resort catch: a render error shows a calm recovery panel, never a white screen. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="flex min-h-screen items-center justify-center bg-ground p-6">
        <div className="panel max-w-md p-8 text-center">
          <div className="cap">Something went wrong</div>
          <p className="mt-3 text-sm text-ink-2">
            The page hit an unexpected error. Reloading usually resolves it — if it keeps
            happening, the error has been logged.
          </p>
          <button className="btn-go mt-5" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      </div>
    )
  }
}
