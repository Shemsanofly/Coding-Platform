import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-cream">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-ocean-600 border-t-transparent" />
    </div>
  );
}

export default function AuthGuard() {
  const { user, isBootstrapping } = useAuth();
  const location = useLocation();

  // Wait until auth bootstrap completes to avoid redirect flicker on page refresh.
  if (isBootstrapping) {
    return <FullPageSpinner />;
  }

  // Keep intended destination so user can continue after successful login.
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
