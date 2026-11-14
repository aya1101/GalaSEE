import http from "node:http";
import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const apiHealthUrl = "http://127.0.0.1:8000/health";
const apiPort = 8000;

function apiAlreadyRunning() {
  return new Promise((resolve) => {
    const request = http.get(apiHealthUrl, (response) => {
      response.resume();
      resolve(response.statusCode === 200);
    });
    request.setTimeout(900, () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

function apiPortIsOccupied() {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: "127.0.0.1", port: apiPort });
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.once("error", () => resolve(false));
    socket.setTimeout(900, () => {
      socket.destroy();
      resolve(false);
    });
  });
}

if (await apiAlreadyRunning()) {
  console.log("[api] FastAPI is already running on http://127.0.0.1:8000");
  process.exit(0);
}

if (await apiPortIsOccupied()) {
  console.log("[api] Port 8000 is already occupied; reusing the existing API process");
  process.exit(0);
}

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const localPython = process.platform === "win32"
  ? path.join(projectRoot, "api", ".venv", "Scripts", "python.exe")
  : path.join(projectRoot, "api", ".venv", "bin", "python");
const python = fs.existsSync(localPython)
  ? localPython
  : (process.platform === "win32" ? "python" : "python3");

console.log(`[api] Using Python: ${python}`);
// Keep the single `npm run dev` workflow, but let Uvicorn restart its worker
// whenever Python code changes. Next.js already watches the frontend files.
const api = spawn(python, [
  "-m", "uvicorn", "api.main:app",
  "--port", "8000",
  "--reload",
  "--reload-dir", path.join(projectRoot, "api"),
], { stdio: "inherit" });

const stopApi = () => {
  if (!api.killed) api.kill();
};

process.on("SIGINT", stopApi);
process.on("SIGTERM", stopApi);
api.on("exit", (code) => process.exit(code ?? 1));
