export default function BrandMark({ className = "" }) {
  return (
    <span className={`lc-brand-icon ${className}`.trim()} aria-hidden="true">
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
        <path d="M8 6.5a1.5 1.5 0 0 1 1.5-1.5h7A2.5 2.5 0 0 1 19 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-7A1.5 1.5 0 0 1 8 17.5v-11Zm2 0v11h7a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-7ZM6 8a1 1 0 0 1 1 1v8a2 2 0 0 0 2 2h8a1 1 0 1 1 0 2H9a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1Z" />
      </svg>
    </span>
  );
}
