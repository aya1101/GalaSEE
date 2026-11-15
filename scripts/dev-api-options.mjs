import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export function buildApiServerArgs(platform = process.platform, enableReload = process.env.TIDEAWARE_API_RELOAD !== "0") {
  const args = ["-m", "uvicorn", "api.main:app", "--port", "8000"];
  if (platform !== "win32" && enableReload) {
    args.push("--reload", "--reload-dir", path.join(projectRoot, "api"));
  }
  return args;
}

export function shouldUseNodeWatcher(platform = process.platform, enableReload = process.env.TIDEAWARE_API_RELOAD !== "0") {
  return platform === "win32" && enableReload;
}
