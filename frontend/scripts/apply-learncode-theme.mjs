import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..", "src");

const replacements = [
  ["from-cyan-400 to-indigo-500", "from-coral to-ocean-600"],
  ["from-cyan-500 to-indigo-500", "from-coral to-ocean-600"],
  ["from-indigo-600 to-violet-600", "from-coral to-ocean-600"],
  ["hover:from-cyan-300 hover:to-indigo-400", "hover:brightness-110"],
  ["hover:from-indigo-500 hover:to-violet-500", "hover:brightness-110"],
  ["bg-cyan-600", "bg-ocean-600"],
  ["hover:bg-cyan-500", "hover:bg-ocean-700"],
  ["text-cyan-700", "text-ocean-700"],
  ["text-cyan-200", "text-reef"],
  ["border-cyan-200/70", "border-ocean-200/70"],
  ["border-cyan-200/50", "border-ocean-200/50"],
  ["border-cyan-400/30", "border-ocean-600/30"],
  ["bg-cyan-50/60", "bg-reef/60"],
  ["bg-cyan-50/80", "bg-reef/80"],
  ["bg-cyan-500/10", "bg-ocean-600/10"],
  ["text-indigo-600", "text-ocean-700"],
  ["text-indigo-700", "text-ocean-800"],
  ["text-indigo-800", "text-ocean-800"],
  ["text-indigo-200", "text-reef"],
  ["text-indigo-100/90", "text-muted"],
  ["text-indigo-100/80", "text-muted/90"],
  ["text-indigo-100/95", "text-muted"],
  ["text-indigo-50", "text-sand"],
  ["dark:text-indigo-100/90", "dark:text-reef/90"],
  ["dark:text-indigo-100/80", "dark:text-reef/80"],
  ["dark:text-indigo-100/95", "dark:text-reef/95"],
  ["dark:text-indigo-200", "dark:text-reef"],
  ["dark:text-indigo-50", "dark:text-sand"],
  ["dark:text-indigo-200/80", "dark:text-reef/80"],
  ["ring-indigo-500/30", "ring-ocean-600/30"],
  ["focus:border-indigo-500", "focus:border-ocean-600"],
  ["border-slate-200/90", "border-ocean-600/10"],
  ["border-slate-200/80", "border-ocean-600/10"],
  ["border-slate-300", "border-line"],
  ["text-slate-900", "text-ink"],
  ["text-slate-800", "text-ink"],
  ["text-slate-700", "text-ocean-800"],
  ["text-slate-600", "text-muted"],
  ["text-slate-500", "text-muted"],
  ["text-slate-400", "text-muted/80"],
  ["text-slate-300", "text-reef/80"],
  ["text-slate-200", "text-reef"],
  ["text-slate-100", "text-sand"],
  ["dark:text-white", "dark:text-sand"],
  ["bg-slate-200", "bg-reef/50"],
  ["bg-slate-100", "bg-sand"],
  ["bg-slate-50", "bg-cream"],
  ["hover:bg-slate-100", "hover:bg-sand"],
  ["hover:bg-slate-50", "hover:bg-cream"],
  ["divide-slate-200", "divide-line"],
  ["dark:divide-white/10", "dark:divide-line/30"],
  ["dark:border-white/20", "dark:border-line/40"],
  ["dark:border-white/15", "dark:border-line/30"],
  ["dark:border-white/30", "dark:border-line/40"],
  ["dark:border-white/10", "dark:border-line/20"],
  ["dark:bg-white/10", "dark:bg-ocean-950/50"],
  ["dark:bg-white/5", "dark:bg-ocean-950/40"],
  ["dark:bg-white/15", "dark:bg-ocean-950/60"],
  ["dark:hover:bg-white/10", "dark:hover:bg-ocean-900/50"],
  ["dark:hover:bg-white/25", "dark:hover:bg-ocean-900/70"],
  ["bg-emerald-100 text-emerald-900", "bg-reef text-ocean-800"],
  ["from-slate-100 via-emerald-50 to-cyan-100", "bg-lc-page"],
  ["bg-slate-950", "bg-ocean-950"],
  ["bg-slate-900", "bg-ocean-900"],
  ["border-slate-700/60", "border-ocean-600/20"],
  ["border-slate-500", "border-line"],
  ["border-slate-200/80 bg-slate-50", "border-line bg-cream"],
  ["shadow-lg dark:border-white/20 dark:bg-white/10 dark:shadow-xl dark:backdrop-blur-xl", "shadow-panel dark:border-line/30 dark:bg-ocean-950/50 dark:shadow-none"],
  ["dark:text-indigo-100", "dark:text-reef"],
  ["dark:text-indigo-300", "dark:text-reef"],
  ["dark:text-indigo-100/70", "dark:text-reef/70"],
  ["dark:hover:bg-indigo-500/10", "dark:hover:bg-ocean-600/10"],
  ["dark:bg-indigo-500/20", "dark:bg-ocean-600/20"],
  ["dark:bg-indigo-500/10", "dark:bg-ocean-600/10"],
  ["dark:border-indigo-400/40", "dark:border-ocean-600/40"],
  ["dark:border-cyan-200/60", "dark:border-ocean-600/40"],
  ["dark:bg-cyan-300/15", "dark:bg-ocean-600/15"],
  ["dark:from-cyan-500/10", "dark:from-ocean-600/10"],
  ["dark:to-indigo-500/10", "dark:to-coral/10"],
  ["dark:via-white/5", "dark:via-ocean-950/30"],
  ["border-indigo-200", "border-ocean-200"],
  ["border-indigo-300", "border-ocean-200"],
  ["hover:bg-indigo-50", "hover:bg-reef/40"],
  ["bg-indigo-50", "bg-reef/50"],
  ["bg-indigo-600", "bg-ocean-600"],
  ["text-indigo-900", "text-ocean-900"],
  ["text-cyan-900", "text-ocean-900"],
  ["text-cyan-800", "text-ocean-800"],
  ["dark:text-cyan-100/90", "dark:text-reef/90"],
  ["border-cyan-300/50", "border-ocean-200/50"],
  ["border-cyan-600/50", "border-ocean-600/50"],
  ["bg-cyan-100", "bg-reef"],
  ["bg-cyan-500/20", "bg-ocean-600/20"],
  ["from-cyan-50 via-white to-indigo-50", "from-reef/40 via-white to-sand"],
  ["from-cyan-300 to-indigo-300", "from-coral to-ocean-600"],
  ["hover:from-cyan-400 hover:to-indigo-400", "hover:brightness-110"],
  ["border-slate-200", "border-line"],
  ["border-slate-100", "border-line/70"],
  ["disabled:from-slate-400 disabled:to-slate-400", "disabled:opacity-50"],
  ["dark:hover:border-white/40", "dark:hover:border-line/50"],
  ["dark:hover:bg-white/15", "dark:hover:bg-ocean-900/50"],
  ["dark:text-indigo-100", "dark:text-reef"],
];

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, files);
    } else if (/\.(jsx|js)$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

for (const file of walk(root)) {
  if (file.includes("StudentLayout") || file.includes("AdminLayout") || file.includes("Login.jsx")) {
    continue;
  }
  let content = fs.readFileSync(file, "utf8");
  let changed = false;
  for (const [from, to] of replacements) {
    if (content.includes(from)) {
      content = content.split(from).join(to);
      changed = true;
    }
  }
  if (changed) {
    fs.writeFileSync(file, content);
    console.log("updated", path.relative(root, file));
  }
}
