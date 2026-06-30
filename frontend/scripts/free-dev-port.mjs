/**
 * Frees the Vite dev port before `npm run dev` so a leftover process
 * cannot block startup (EADDRINUSE / "Port 5173 is already in use").
 */
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");

function readDevPort() {
  const fromEnv = Number(process.env.VITE_DEV_SERVER_PORT);
  if (fromEnv > 0) return fromEnv;

  const envFile = path.join(frontendRoot, ".env.development");
  if (fs.existsSync(envFile)) {
    const match = fs
      .readFileSync(envFile, "utf8")
      .match(/^\s*VITE_DEV_SERVER_PORT\s*=\s*(\d+)\s*$/m);
    if (match) return Number(match[1]);
  }

  return 5173;
}

function pidsOnPortWindows(port) {
  try {
    const out = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "ignore"],
    });
    const pids = new Set();
    for (const line of out.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const pid = trimmed.split(/\s+/).at(-1);
      if (pid && /^\d+$/.test(pid)) pids.add(pid);
    }
    return [...pids];
  } catch {
    return [];
  }
}

function pidsOnPortUnix(port) {
  try {
    const out = execSync(`lsof -ti :${port} -sTCP:LISTEN`, {
      encoding: "utf8",
      stdio: ["pipe", "pipe", "ignore"],
    });
    return out
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter((pid) => /^\d+$/.test(pid));
  } catch {
    return [];
  }
}

function killPid(pid) {
  if (process.platform === "win32") {
    execSync(`taskkill /PID ${pid} /F`, { stdio: "ignore" });
    return;
  }
  execSync(`kill -9 ${pid}`, { stdio: "ignore" });
}

const port = readDevPort();
const pids =
  process.platform === "win32" ? pidsOnPortWindows(port) : pidsOnPortUnix(port);

if (pids.length === 0) {
  process.exit(0);
}

for (const pid of pids) {
  console.log(`[predev] Port ${port} in use by PID ${pid} — stopping it.`);
  try {
    killPid(pid);
  } catch {
    console.warn(`[predev] Could not stop PID ${pid}; you may need to close it manually.`);
  }
}
