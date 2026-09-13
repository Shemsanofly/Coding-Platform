import Input from "@/shared/components/ui/Input";

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

export default function PasswordField({
  label,
  error,
  id,
  shown,
  onToggleVisibility,
  visibilityLabel = "password",
  className = "",
  ...props
}) {
  const inputId = id || props.name;

  return (
    <div>
      {label ? (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ocean-800">
          {label}
        </label>
      ) : null}
      <div className="relative">
        <input
          id={inputId}
          type={shown ? "text" : "password"}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? `${inputId}-error` : undefined}
          className={`lc-input pr-11 ${
            error ? "border-red-300 focus:border-red-400 focus:ring-red-200" : ""
          } ${className}`.trim()}
          {...props}
        />
        <VisibilityToggleButton
          shown={shown}
          label={visibilityLabel}
          onToggle={onToggleVisibility}
        />
      </div>
      {error ? (
        <p id={`${inputId}-error`} className="mt-1 text-xs font-medium text-red-600" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
