export default function Input({ label, error, helperText, id, className = "", ...props }) {
  const inputId = id || props.name;

  return (
    <div>
      {label ? (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ocean-800">
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
        className={`lc-input ${error ? "border-red-300 focus:border-red-400 focus:ring-red-200" : ""} ${className}`.trim()}
        {...props}
      />
      {helperText && !error ? (
        <p id={`${inputId}-helper`} className="mt-1 text-xs text-muted">
          {helperText}
        </p>
      ) : null}
      {error ? (
        <p id={`${inputId}-error`} className="mt-1 text-xs font-medium text-red-600" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
