export default function Tabs({ tabs, activeTab, onChange, className = "" }) {
  return (
    <div
      role="tablist"
      aria-label="Sections"
      className={`flex flex-wrap gap-1 rounded-2xl border border-ocean-600/10 bg-white p-1 dark:border-line/40 dark:bg-ocean-950/50 ${className}`.trim()}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`min-h-[40px] flex-1 rounded-xl px-3 py-2 text-sm font-semibold transition sm:flex-none sm:px-4 ${
              isActive
                ? "bg-ocean-600 text-white shadow-sm"
                : "text-ocean-800 hover:bg-reef/60 dark:text-reef dark:hover:bg-ocean-900/60"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
