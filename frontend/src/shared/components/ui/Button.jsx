const variants = {
  primary: "lc-btn-primary",
  ghost: "lc-btn-ghost",
  danger:
    "inline-flex items-center justify-center rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-70 dark:border-red-400/40 dark:bg-ocean-950/60 dark:text-red-200 dark:hover:bg-red-500/20",
  gradient:
    "inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-coral to-ocean-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70",
};

const sizes = {
  sm: "min-h-9 px-3 py-2 text-xs",
  md: "",
  lg: "min-h-[48px] px-6 py-3",
};

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className = "",
  children,
  disabled,
  ...props
}) {
  const base = variants[variant] ?? variants.primary;
  const sizeClass = sizes[size] ?? "";
  const isDisabled = disabled || loading;

  return (
    <button
      type="button"
      disabled={isDisabled}
      className={`${base} ${sizeClass} ${className}`.trim()}
      {...props}
    >
      {loading ? "Please wait…" : children}
    </button>
  );
}
