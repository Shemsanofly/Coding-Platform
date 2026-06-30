import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthProvider";
import UserAvatar from "@/shared/components/UserAvatar";
import { getDisplayName } from "@/shared/utils/userDisplay";

const THEME_STORAGE_KEY = "learncode.theme";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/playground", label: "Playground" },
  { to: "/catalog", label: "Courses" },
  { to: "/learning-path", label: "Learning Path" },
  { to: "/recommendations", label: "Recommendations" },
  { to: "/weakness", label: "Weak Topics" },
  { to: "/profile", label: "Profile" },
  { to: "/settings", label: "Settings" },
];

const mobileNavItems = [
  { to: "/", label: "Home", end: true },
  { to: "/playground", label: "Play", end: false },
  { to: "/catalog", label: "Courses" },
  { to: "/learning-path", label: "Path" },
  { to: "/recommendations", label: "Recs" },
  { to: "/weakness", label: "Weak" },
  { to: "/profile", label: "Profile" },
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

const mobileIcons = {
  Home: "⌂",
  Play: "⌨",
  Courses: "▦",
  Path: "↗",
  Recs: "★",
  Weak: "!",
  Profile: "◎",
};

function BrandMark() {
  return (
    <span className="lc-brand-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
        <path d="M8 6.5a1.5 1.5 0 0 1 1.5-1.5h7A2.5 2.5 0 0 1 19 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-7A1.5 1.5 0 0 1 8 17.5v-11Zm2 0v11h7a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-7ZM6 8a1 1 0 0 1 1 1v8a2 2 0 0 0 2 2h8a1 1 0 1 1 0 2H9a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1Z" />
      </svg>
    </span>
  );
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
                <span aria-hidden="true" className="text-base leading-none">
                  {mobileIcons[item.label] ?? "•"}
                </span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        </nav>
      ) : null}
    </div>
  );
}
