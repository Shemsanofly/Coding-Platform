import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthProvider";
import UserAvatar from "@/shared/components/UserAvatar";
import BrandMark from "@/shared/components/BrandMark";
import { getDisplayName } from "@/shared/utils/userDisplay";

const THEME_STORAGE_KEY = "learncode.theme";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/catalog", label: "Courses" },
  { to: "/learning-path", label: "Study Plan" },
  { to: "/playground", label: "Playground" },
  { to: "/analytics", label: "Analytics" },
  { to: "/profile", label: "Profile" },
];

const mobileNavItems = [
  { to: "/", label: "Home", end: true, icon: "home" },
  { to: "/catalog", label: "Courses", icon: "courses" },
  { to: "/learning-path", label: "Plan", icon: "plan" },
  { to: "/playground", label: "Play", icon: "play" },
  { to: "/analytics", label: "Stats", icon: "stats" },
  { to: "/profile", label: "Profile", icon: "profile" },
];

const sidebarLinkClass =
  (isLight) =>
  ({ isActive }) =>
    `flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
      isActive
        ? isLight
          ? "border border-ocean-600/20 bg-white text-ocean-700 shadow-sm"
          : "border border-ocean-600/30 bg-ocean-900/80 text-reef shadow-sm"
        : isLight
          ? "border border-transparent text-ocean-950 hover:border-ocean-600/20 hover:bg-white hover:text-ocean-700"
          : "border border-transparent text-reef/90 hover:border-ocean-600/30 hover:bg-ocean-900/60 hover:text-reef"
    }`;

const mobileLinkClass =
  (isLight) =>
  ({ isActive }) =>
    `flex min-h-[48px] min-w-[52px] shrink-0 flex-col items-center justify-center gap-0.5 rounded-xl px-2 py-1.5 text-[10px] font-medium transition ${
      isActive
        ? isLight
          ? "bg-white text-ocean-700 shadow-sm"
          : "bg-ocean-900/80 text-reef shadow-sm"
        : isLight
          ? "text-ocean-800 hover:bg-white/70"
          : "text-reef/90 hover:bg-ocean-900/60"
    }`;

function MobileNavIcon({ name }) {
  const className = "h-5 w-5";
  switch (name) {
    case "home":
      return (
        <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5Z" strokeLinejoin="round" />
        </svg>
      );
    case "courses":
      return (
        <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h7" strokeLinecap="round" />
        </svg>
      );
    case "plan":
      return (
        <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="m4 6 8-2 8 2M6 8v11l6 2 6-2V8" strokeLinejoin="round" />
        </svg>
      );
    case "play":
      return (
        <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M8 9l3 2-3 2V9Zm5 0h3m-3 4h3M6 5h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" strokeLinecap="round" />
        </svg>
      );
    case "stats":
      return (
        <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M5 19V9m7 10V5m7 14v-7" strokeLinecap="round" />
        </svg>
      );
    case "profile":
      return (
        <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-4 0-7 2-7 4v1h14v-1c0-2-3-4-7-4Z" strokeLinejoin="round" />
        </svg>
      );
    default:
      return null;
  }
}

export default function StudentLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [theme, setTheme] = useState(() => {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "dark" || saved === "light") {
      return saved;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const hideBottomNav = location.pathname.includes("/quiz");
  const isLight = theme === "light";

  return (
    <div
      className={`student-theme-root min-h-screen ${isLight ? "student-theme-light bg-lc-page text-ink" : "bg-lc-page-dark text-white"}`}
    >
      <div className="dashboard-layout min-h-screen md:grid md:grid-cols-[240px_1fr]">
        <aside
          className={`hidden border-r border-ocean-600/10 bg-lc-sidebar backdrop-blur-md md:sticky md:top-0 md:flex md:h-screen md:flex-col md:gap-5 md:p-4 ${
            isLight ? "" : "border-line/80 bg-[linear-gradient(180deg,rgba(17,27,38,0.95)_0%,rgba(12,22,34,0.95)_100%)]"
          }`}
        >
          <NavLink to="/" className="inline-flex items-center gap-2.5 px-2 text-lg font-bold text-ocean-800">
            <BrandMark />
            <span className={isLight ? "text-ocean-800" : "text-white"}>LearnCode</span>
          </NavLink>

          <nav className="grid gap-2">
            {navItems.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={sidebarLinkClass(isLight)}>
                {item.label}
              </NavLink>
            ))}
            <NavLink to="/settings" className={sidebarLinkClass(isLight)}>
              Settings
            </NavLink>
          </nav>

          <div className="mt-auto grid gap-2 border-t border-ocean-600/10 pt-4">
            <button
              type="button"
              onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
              className={sidebarLinkClass(isLight)({ isActive: false })}
            >
              {isLight ? "Dark mode" : "Light mode"}
            </button>
            <button type="button" onClick={() => void logout()} className={sidebarLinkClass(isLight)({ isActive: false })}>
              Log out
            </button>
            <div className={`flex items-center gap-2 px-2 ${isLight ? "text-muted" : "text-reef/80"}`}>
              <UserAvatar user={user} size="sm" className="rounded-xl" />
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-ink dark:text-sand">{getDisplayName(user)}</p>
                <p className="truncate text-[11px]">{user?.email}</p>
              </div>
            </div>
          </div>
        </aside>

        <div className="min-w-0">
          <header className="sticky top-0 z-40 border-b border-ocean-600/10 bg-white/90 backdrop-blur-xl md:hidden">
            <div className="flex items-center justify-between gap-2 px-4 py-3">
              <NavLink to="/" className="inline-flex items-center gap-2 font-bold text-ocean-800">
                <BrandMark />
                LearnCode
              </NavLink>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
                  className="lc-btn-ghost min-h-10 min-w-10 px-2"
                  aria-label={isLight ? "Switch to dark theme" : "Switch to light theme"}
                >
                  {isLight ? "☾" : "☀"}
                </button>
                <button type="button" onClick={() => void logout()} className="lc-btn-ghost min-h-10 px-3">
                  Log out
                </button>
              </div>
            </div>
          </header>

          <main className="mx-auto max-w-6xl overflow-x-hidden px-4 pb-24 pt-5 md:px-6 md:pb-10 md:pt-8">
            <Outlet />
          </main>
        </div>
      </div>

      {!hideBottomNav ? (
        <nav
          className={`fixed bottom-0 left-0 right-0 z-50 border-t py-1 backdrop-blur-xl md:hidden ${
            isLight ? "border-ocean-600/10 bg-white/95" : "border-line/30 bg-ocean-950/95"
          }`}
          aria-label="Mobile navigation"
        >
          <div className="mx-auto flex max-w-6xl items-stretch justify-start gap-0.5 overflow-x-auto px-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {mobileNavItems.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={mobileLinkClass(isLight)}>
                <MobileNavIcon name={item.icon} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        </nav>
      ) : null}
    </div>
  );
}
