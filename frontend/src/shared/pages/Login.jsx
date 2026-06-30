import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthProvider";

const formatLoginApiMessage = (data) => {
  if (!data || typeof data !== "object") {
    return null;
  }
  const detail = data.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.filter(Boolean).join(" ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  const chunks = [];
  for (const [key, val] of Object.entries(data)) {
    if (key === "code") {
      continue;
    }
    if (Array.isArray(val)) {
      chunks.push(`${key}: ${val.join(" ")}`);
    } else if (typeof val === "string") {
      chunks.push(`${key}: ${val}`);
    }
  }
  return chunks.length ? chunks.join(" ") : null;
};

function VisibilityToggleButton({ shown, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute right-2 top-1/2 inline-flex -translate-y-1/2 items-center rounded-lg p-1.5 text-ocean-700 transition hover:bg-ocean-600/10"
      aria-label={shown ? "Hide password" : "Show password"}
      title={shown ? "Hide password" : "Show password"}
    >
      {shown ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
          <path d="M2.7 3.7a1 1 0 0 1 1.4 0l16.2 16.2a1 1 0 1 1-1.4 1.4l-2.8-2.8A11.8 11.8 0 0 1 12 19C6.9 19 3.2 15.8 1.2 12.7a1.2 1.2 0 0 1 0-1.4c.9-1.4 2.3-3.1 4.1-4.4L2.7 5.1a1 1 0 0 1 0-1.4Zm6.2 6.2a3.5 3.5 0 0 0 4.9 4.9l-4.9-4.9ZM12 5c5.1 0 8.8 3.2 10.8 6.3.3.4.3 1 0 1.4-.7 1.1-1.8 2.4-3.2 3.6l-2.9-2.9a4.9 4.9 0 0 0-6.1-6.1L8.4 5.1C9.5 5 10.7 5 12 5Z" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
          <path d="M12 5c5.1 0 8.8 3.2 10.8 6.3.3.4.3 1 0 1.4C20.8 15.8 17.1 19 12 19S3.2 15.8 1.2 12.7a1.2 1.2 0 0 1 0-1.4C3.2 8.2 6.9 5 12 5Zm0 2c-3.7 0-6.7 2.2-8.7 5 2 2.8 5 5 8.7 5s6.7-2.2 8.7-5c-2-2.8-5-5-8.7-5Zm0 2.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5Z" />
        </svg>
      )}
    </button>
  );
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const mutation = useMutation({
    mutationFn: login,
    onError: (error) => {
      if (!error?.response) {
        toast.error("Cannot reach backend server. Start Django API on http://localhost:8000.", {
          id: "login-error",
        });
        return;
      }
      const formatted = formatLoginApiMessage(error.response?.data);
      toast.error(formatted || "Could not sign in. Check your credentials.", { id: "login-error" });
    },
    onSuccess: (user) => {
      toast.success("Signed in", { id: "login-success" });
      if (user?.role === "admin") {
        navigate("/admin/dashboard", { replace: true });
        return;
      }
      navigate(from, { replace: true });
    },
  });

  const handleSubmit = (event) => {
    event.preventDefault();
    if (mutation.isPending) {
      return;
    }
    mutation.mutate({ email: email.trim(), password });
  };

  return (
    <div className="lc-auth-shell">
      <div className="lc-auth-card">
        <Link to="/" className="relative z-[1] inline-flex items-center gap-3 text-xl font-bold text-ocean-800">
          <span className="lc-brand-icon">
            <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current" aria-hidden="true">
              <path d="M8 6.5a1.5 1.5 0 0 1 1.5-1.5h7A2.5 2.5 0 0 1 19 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-7A1.5 1.5 0 0 1 8 17.5v-11Zm2 0v11h7a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-7ZM6 8a1 1 0 0 1 1 1v8a2 2 0 0 0 2 2h8a1 1 0 1 1 0 2H9a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1Z" />
            </svg>
          </span>
          LearnCode
        </Link>

        <div className="relative z-[1] mt-6">
          <p className="lc-tag">Welcome back</p>
          <h1 className="mt-2 text-3xl font-bold text-ocean-950">Sign in</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">Use your email and password to continue learning.</p>
        </div>

        <form className="relative z-[1] mt-6 grid gap-4" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-semibold text-ocean-800">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="lc-input"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-semibold text-ocean-800">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="lc-input pr-11"
              />
              <VisibilityToggleButton
                shown={showPassword}
                onToggle={() => setShowPassword((current) => !current)}
              />
            </div>
          </div>
          <button type="submit" disabled={mutation.isPending} className="lc-btn-primary w-full">
            {mutation.isPending ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="relative z-[1] mt-6 text-center text-sm text-muted">
          No account?{" "}
          <Link to="/register" className="font-semibold text-ocean-700 hover:text-ocean-800">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
