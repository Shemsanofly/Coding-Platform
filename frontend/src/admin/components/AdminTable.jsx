import ResponsiveDataCard from "@/admin/components/ResponsiveDataCard";

export default function AdminTable({ columns, rows, emptyMessage = "No data.", loading, error, onRetry }) {
  if (loading) {
    return <p className="px-4 py-8 text-sm text-muted">Loading…</p>;
  }

  if (error) {
    return (
      <p className="px-4 py-8 text-sm text-red-600">
        {error}{" "}
        {onRetry ? (
          <button type="button" onClick={onRetry} className="font-semibold underline">
            Retry
          </button>
        ) : null}
      </p>
    );
  }

  if (!rows.length) {
    return <p className="px-4 py-8 text-sm text-muted">{emptyMessage}</p>;
  }

  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full divide-y divide-line">
          <thead className="bg-emerald-50/70">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line/70 bg-white">
            {rows.map((row) => (
              <tr key={row.id} className="hover:bg-emerald-50/40">
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-sm text-ink">
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-3 p-3 md:hidden">
        {rows.map((row) => (
          <ResponsiveDataCard
            key={row.id}
            title={row.cardTitle || row.title || row.name || `#${row.id}`}
            rows={columns
              .filter((col) => col.key !== "actions")
              .map((col) => ({
                label: col.label,
                value: col.render ? col.render(row) : row[col.key],
              }))}
            actions={
              columns.find((col) => col.key === "actions")?.render
                ? columns.find((col) => col.key === "actions").render(row)
                : null
            }
          />
        ))}
      </div>
    </>
  );
}
