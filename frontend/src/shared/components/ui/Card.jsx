const paddings = {
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

const variants = {
  default:
    "rounded-2xl border border-ocean-600/10 bg-white shadow-md dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-lg dark:backdrop-blur-xl",
  panel: "lc-panel",
  elevated:
    "rounded-2xl border border-ocean-600/10 bg-white shadow-lg dark:border-line/40 dark:bg-ocean-950/50 dark:shadow-xl dark:backdrop-blur-xl",
  subtle:
    "rounded-2xl border border-ocean-600/10 bg-white/90 shadow-sm backdrop-blur dark:border-line/40 dark:bg-ocean-950/40",
  alert:
    "rounded-2xl border border-amber-300/80 bg-amber-50 p-6 text-amber-950 dark:border-amber-400/40 dark:bg-amber-500/10 dark:text-amber-50",
};

export default function Card({
  as: Component = "div",
  variant = "default",
  padding = "md",
  className = "",
  children,
  ...props
}) {
  const paddingClass = variant === "alert" ? "" : paddings[padding] ?? paddings.md;
  return (
    <Component
      className={`${variants[variant] ?? variants.default} ${paddingClass} ${className}`.trim()}
      {...props}
    >
      {children}
    </Component>
  );
}
