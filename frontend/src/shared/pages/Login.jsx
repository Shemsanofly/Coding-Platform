import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useAuth } from "@/hooks/useAuth";
import BrandMark from "@/shared/components/BrandMark";
import Input from "@/shared/components/ui/Input";
import PasswordField from "@/shared/components/ui/PasswordField";
import { parseFieldErrors } from "@/shared/utils/parseFieldErrors";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const mutation = useMutation({
    mutationFn: login,
    onError: (error) => {
      const parsed = parseFieldErrors(error);
      setFieldErrors(parsed);
      if (parsed.form) {
        toast.error(parsed.form, { id: "login-error" });
      } else if (!error?.response) {
        toast.error("Cannot reach the server. Ensure the backend is running.", {
          id: "login-error",
        });
      }
    },
    onSuccess: (user) => {
      setFieldErrors({});
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

    const nextErrors = {};
    if (!email.trim()) nextErrors.email = "Email is required.";
    if (!password) nextErrors.password = "Password is required.";
    if (Object.keys(nextErrors).length) {
      setFieldErrors(nextErrors);
      return;
    }

    setFieldErrors({});
    mutation.mutate({ email: email.trim(), password });
  };

  return (
    <div className="lc-auth-shell">
      <div className="lc-auth-card">
        <Link
          to="/"
          className="relative z-[1] inline-flex items-center gap-3 text-xl font-bold text-ocean-800"
        >
          <BrandMark />
          LearnCode
        </Link>

        <div className="relative z-[1] mt-6">
          <p className="lc-tag">Welcome back</p>
          <h1 className="mt-2 text-3xl font-bold text-ocean-950">Sign in</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Use your email and password to continue learning.
          </p>
        </div>

        <form className="relative z-[1] mt-6 grid gap-4" onSubmit={handleSubmit} noValidate>
          <Input
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (fieldErrors.email)
                setFieldErrors((current) => ({ ...current, email: undefined }));
            }}
            error={fieldErrors.email}
          />
          <PasswordField
            id="password"
            label="Password"
            autoComplete="current-password"
            value={password}
            shown={showPassword}
            onToggleVisibility={() => setShowPassword((current) => !current)}
            onChange={(e) => {
              setPassword(e.target.value);
              if (fieldErrors.password)
                setFieldErrors((current) => ({ ...current, password: undefined }));
            }}
            error={fieldErrors.password}
          />
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
