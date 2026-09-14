import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useAuth } from "@/hooks/useAuth";
import BrandMark from "@/shared/components/BrandMark";
import Input from "@/shared/components/ui/Input";
import PasswordField from "@/shared/components/ui/PasswordField";
import { parseFieldErrors } from "@/shared/utils/parseFieldErrors";

const LEVEL_HELP = {
  beginner: "New to programming or this subject area.",
  intermediate: "Comfortable with fundamentals and ready for applied topics.",
  advanced: "Strong foundation; prefers challenging material.",
};

export default function Register() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("beginner");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const mutation = useMutation({
    mutationFn: registerUser,
    onSuccess: () => {
      setFieldErrors({});
      toast.success("Account created. Sign in to continue.", { id: "register-success" });
      navigate("/login", { replace: true });
    },
    onError: (error) => {
      const parsed = parseFieldErrors(error);
      setFieldErrors(parsed);
      if (parsed.form) {
        toast.error(parsed.form, { id: "register-error" });
      } else if (!error?.response) {
        toast.error("Cannot reach the server. Ensure the backend is running.", {
          id: "register-error",
        });
      }
    },
  });

  const clearError = (key) => {
    if (fieldErrors[key]) {
      setFieldErrors((current) => ({ ...current, [key]: undefined }));
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (mutation.isPending) {
      return;
    }

    const nextErrors = {};
    if (!email.trim()) nextErrors.email = "Email is required.";
    if (!password) nextErrors.password = "Password is required.";
    if (!confirmPassword) nextErrors.confirm_password = "Please confirm your password.";
    else if (password !== confirmPassword) nextErrors.confirm_password = "Passwords do not match.";
    if (Object.keys(nextErrors).length) {
      setFieldErrors(nextErrors);
      return;
    }

    setFieldErrors({});
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
        <Link
          to="/"
          className="relative z-[1] inline-flex items-center gap-3 text-xl font-bold text-ocean-800"
        >
          <BrandMark />
          LearnCode
        </Link>

        <div className="relative z-[1] mt-6">
          <p className="lc-tag">Join now</p>
          <h1 className="mt-2 text-3xl font-bold text-ocean-950">Create your account</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Sign up as a student to start learning.
          </p>
        </div>

        <form className="relative z-[1] mt-6 grid gap-4" onSubmit={handleSubmit} noValidate>
          <Input
            id="reg-email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              clearError("email");
            }}
            error={fieldErrors.email}
          />
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
            <p className="mt-1 text-xs text-muted">{LEVEL_HELP[experienceLevel]}</p>
            {fieldErrors.experience_level ? (
              <p className="mt-1 text-xs font-medium text-red-600" role="alert">
                {fieldErrors.experience_level}
              </p>
            ) : null}
          </div>
          <PasswordField
            id="reg-password"
            label="Password"
            autoComplete="new-password"
            value={password}
            shown={showPassword}
            onToggleVisibility={() => setShowPassword((current) => !current)}
            onChange={(e) => {
              setPassword(e.target.value);
              clearError("password");
            }}
            error={fieldErrors.password}
          />
          <PasswordField
            id="reg-confirm"
            label="Confirm password"
            autoComplete="new-password"
            visibilityLabel="password confirmation"
            value={confirmPassword}
            shown={showConfirmPassword}
            onToggleVisibility={() => setShowConfirmPassword((current) => !current)}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              clearError("confirm_password");
            }}
            error={fieldErrors.confirm_password}
          />
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
