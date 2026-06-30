import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthProvider";
import UserAvatar from "@/shared/components/UserAvatar";
import { getDisplayName } from "@/shared/utils/userDisplay";

const linkClass = ({ isActive }) =>
  `rounded-xl px-3 py-2 text-sm font-semibold transition ${
    isActive
      ? "bg-reef text-ocean-800 shadow-sm"
      : "text-ink hover:bg-white hover:text-ocean-700"
  }`;

function BrandMark() {
  return (
    <span className="lc-brand-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
        <path d="M8 6.5a1.5 1.5 0 0 1 1.5-1.5h7A2.5 2.5 0 0 1 19 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-7A1.5 1.5 0 0 1 8 17.5v-11Zm2 0v11h7a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-7ZM6 8a1 1 0 0 1 1 1v8a2 2 0 0 0 2 2h8a1 1 0 1 1 0 2H9a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1Z" />
      </svg>
    </span>
  );
}

export default function AdminLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen overflow-x-hidden bg-lc-page text-ink">
      <header className="sticky top-0 z-40 border-b border-ocean-600/10 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:py-4">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:gap-6">
            <NavLink to="/admin/dashboard" className="inline-flex shrink-0 items-center gap-2 text-sm font-bold text-ocean-800">
              <BrandMark />
              LearnCode Admin
            </NavLink>
            <nav className="flex flex-wrap items-center gap-1">
              <NavLink to="/admin/dashboard" className={linkClass}>
                Dashboard
              </NavLink>
              <NavLink to="/admin/courses" className={linkClass}>
                Courses
              </NavLink>
              <NavLink to="/admin/users" className={linkClass}>
                Students
              </NavLink>
              <NavLink to="/admin/analytics" className={linkClass}>
                Analytics
              </NavLink>
              <NavLink to="/admin/reports" className={linkClass}>
                Reports
              </NavLink>
              <NavLink to="/admin/settings" className={linkClass}>
                Settings
              </NavLink>
            </nav>
          </div>
          <div className="flex w-full shrink-0 items-center justify-end gap-2 sm:w-auto sm:gap-3">
            <NavLink to="/admin/settings" className="hidden items-center gap-2 md:inline-flex">
              <UserAvatar user={user} size="sm" className="rounded-xl" />
              <span className="max-w-[140px] truncate text-xs text-muted">{getDisplayName(user)}</span>
            </NavLink>
            <button type="button" onClick={() => void logout()} className="lc-btn-ghost min-h-10 px-3">
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl pb-12 pt-4 sm:pt-6">
        <Outlet />
      </main>
    </div>
  );
}
