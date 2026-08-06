import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center py-24 text-center">
      <div className="tnum text-6xl font-semibold text-accent-ink">404</div>
      <p className="mt-3 text-ink-2">This page doesn't exist — or was never listed.</p>
      <Link to="/" className="btn-go mt-6">Back to Stride</Link>
    </div>
  )
}
