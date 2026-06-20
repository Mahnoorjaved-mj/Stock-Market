import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="text-5xl font-bold text-accent">404</div>
      <p className="mt-2 text-secondary">This page could not be found.</p>
      <Link to="/" className="ss-btn mt-6">
        Back to dashboard
      </Link>
    </div>
  )
}
