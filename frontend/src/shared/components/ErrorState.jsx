export default function ErrorState({ title = "Something went wrong", message, onRetry }) {
  return (
    <div className="rounded-2xl border border-red-200/80 bg-red-50 px-4 py-6 text-center dark:border-red-400/30 dark:bg-red-500/10">
      <p className="text-sm font-semibold text-red-800 dark:text-red-200">{title}</p>
      {message ? <p className="mt-2 text-sm text-red-700 dark:text-red-300/90">{message}</p> : null}
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex min-h-10 items-center rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100 dark:border-red-400/40 dark:bg-ocean-950/60 dark:text-red-200 dark:hover:bg-red-500/20"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
