import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthProvider";

function VisibilityToggleButton({ shown, onToggle, label }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute right-2 top-1/2 inline-flex -translate-y-1/2 items-center rounded-lg p-1.5 text-ocean-700 transition hover:bg-ocean-600/10"
      aria-label={shown ? `Hide ${label}` : `Show ${label}`}
      title={shown ? `Hide ${label}` : `Show ${label}`}
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

export default function Register() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("beginner");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const getErrorMessage = (error) => {
    const data = error?.response?.data;
    if (!error?.response) {
      return "Cannot reach backend server. Start Django API on http://localhost:8000.";
    }
    if (!data) {
      return "Could not create account.";
    }
    if (typeof data.detail === "string") {
      return data.detail;
    }
    const preferredKeys = [
      "email",
      "password",
      "confirm_password",
      "experience_level",
      "non_field_errors",
    ];
    for (const key of preferredKeys) {
      const value = data[key];
      if (!value) {
        continue;
      }
      if (Array.isArray(value) && value.length) {
        return String(value[0]);
      }
      if (typeof value === "string") {
        return value;
      }
    }
    return "Could not create account.";
  };

  const mutation = useMutation({
    mutationFn: registerUser,
    onSuccess: () => {
      toast.success("Account created. Sign in to continue.", { id: "register-success" });
      navigate("/login", { replace: true });
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      toast.error(message, { id: "register-error" });
    },
  });

  const handleSubmit = (event) => {
    event.preventDefault();
    if (mutation.isPending) {
      return;
    }
    mutation.mutate({
      email: email.trim(),
      password,
      confirm_password: confirmPassword,
      role: "student",
      experience_level: experienceLevel,
    });
  };

  return (
    <div className="lc-auth-shell">
      <div className="lc-auth-card max-w-lg">
        <Link to="/" className="relative z-[1] inline-flex items-center gap-3 text-xl font-bold text-ocean-800">
          <span className="lc-brand-icon">
            <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current" aria-hidden="true">
              <path d="M8 6.5a1.5 1.5 0 0 1 1.5-1.5h7A2.5 2.5 0 0 1 19 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-7A1.5 1.5 0 0 1 8 17.5v-11Zm2 0v11h7a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-7ZM6 8a1 1 0 0 1 1 1v8a2 2 0 0 0 2 2h8a1 1 0 1 1 0 2H9a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1Z" />
            </svg>
          </span>
          LearnCode
        </Link>

        <div className="relative z-[1] mt-6">
          <p className="lc-tag">Join now</p>
          <h1 className="mt-2 text-3xl font-bold text-ocean-950">Create your account</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">Sign up as a student to start learning.</p>
        </div>

        <form className="relative z-[1] mt-6 grid gap-4" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="reg-email" className="mb-1.5 block text-sm font-semibold text-ocean-800">
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="lc-input"
            />
          </div>
          <div>
            <label htmlFor="reg-exp" className="mb-1.5 block text-sm font-semibold text-ocean-800">
              Learning level
            </label>
            <select
              id="reg-exp"
              value={experienceLevel}
              onChange={(e) => setExperienceLevel(e.target.value)}
              className="lc-input"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
            <p className="mt-1 text-xs text-muted">
              Used with quiz performance to tune recommendations and difficulty.
            </p>
          </div>
          <div>
            <label htmlFor="reg-password" className="mb-1.5 block text-sm font-semibold text-ocean-800">
              Password
            </label>
            <div className="relative">
              <input
                id="reg-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="lc-input pr-11"
              />
              <VisibilityToggleButton
                shown={showPassword}
                label="password"
                onToggle={() => setShowPassword((current) => !current)}
              />
            </div>
          </div>
          <div>
            <label htmlFor="reg-confirm" className="mb-1.5 block text-sm font-semibold text-ocean-800">
              Confirm password
            </label>
            <div className="relative">
              <input
                id="reg-confirm"
                type={showConfirmPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="lc-input pr-11"
              />
              <VisibilityToggleButton
                shown={showConfirmPassword}
                label="password confirmation"
                onToggle={() => setShowConfirmPassword((current) => !current)}
              />
            </div>
          </div>
          <button type="submit" disabled={mutation.isPending} className="lc-btn-primary w-full">
            {mutation.isPending ? "Creating..." : "Create account"}
          </button>
        </form>

        <p className="relative z-[1] mt-6 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-ocean-700 hover:text-ocean-800">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
