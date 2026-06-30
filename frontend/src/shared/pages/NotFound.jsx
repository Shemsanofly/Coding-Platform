import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-cream px-4 text-center">
      <p className="text-sm font-semibold text-ocean-700">404</p>
      <h1 className="mt-2 text-2xl font-bold text-ink">Page not found</h1>
      <p className="mt-2 max-w-md text-sm text-muted">
        The page you are looking for does not exist or was moved.
      </p>
      <Link
        to="/"
        className="mt-6 rounded-lg bg-ocean-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-reef/400"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
