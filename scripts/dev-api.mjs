import http from "node:http";
import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { buildApiServerArgs, shouldUseNodeWatcher } from "./dev-api-options.mjs";

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
const apiDirectory = path.join(projectRoot, "api");
let api;
let watcher;
let restartTimer;
let restarting = false;
let stopping = false;

function launchApi() {
  const child = spawn(python, buildApiServerArgs(), { stdio: "inherit", windowsHide: true });
  api = child;
  child.on("exit", (code) => {
    if (child !== api || stopping || restarting) return;
    process.exit(code ?? 1);
  });
}

function restartApi() {
  if (stopping || restarting) return;
  restarting = true;
  const previous = api;
  if (!previous || previous.killed) {
    restarting = false;
    launchApi();
    return;
  }
  previous.once("exit", () => {
    if (stopping) return;
    restarting = false;
    console.log("[api] Restarting after Python source change");
    launchApi();
  });
  previous.kill();
}

function watchApiFiles() {
  if (!shouldUseNodeWatcher()) return;
  watcher = fs.watch(apiDirectory, { recursive: true }, (_event, filename) => {
    if (!String(filename ?? "").endsWith(".py")) return;
    clearTimeout(restartTimer);
    restartTimer = setTimeout(restartApi, 150);
  });
  watcher.on("error", (error) => console.error(`[api] File watcher error: ${error.message}`));
  console.log(`[api] Watching ${apiDirectory} for Python changes`);
}

function stopApi() {
  if (stopping) return;
  stopping = true;
  clearTimeout(restartTimer);
  watcher?.close();
  if (!api || api.killed) {
    process.exit(0);
    return;
  }
  api.once("exit", () => process.exit(0));
  api.kill();
}

launchApi();
watchApiFiles();
process.on("SIGINT", stopApi);
process.on("SIGTERM", stopApi);
