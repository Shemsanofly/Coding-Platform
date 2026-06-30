import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthProvider";

export default function GuestGuard() {
  const { user, isBootstrapping } = useAuth();

  if (isBootstrapping) {
    // Keep login/register usable while session check runs in the background.
    return <Outlet />;
  }

  if (user) {
    return <Navigate to={user.role === "admin" ? "/admin/dashboard" : "/"} replace />;
  }

  return <Outlet />;
}
