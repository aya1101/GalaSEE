import { describe, expect, it } from "vitest";
import { buildApiServerArgs, shouldUseNodeWatcher } from "./dev-api-options.mjs";

describe("dev API server options", () => {
  it("keeps Uvicorn single-process on Windows while Node owns reloads", () => {
    expect(buildApiServerArgs("win32")).toEqual(["-m", "uvicorn", "api.main:app", "--port", "8000"]);
    expect(shouldUseNodeWatcher("win32")).toBe(true);
  });

  it("keeps Uvicorn reload available on non-Windows platforms", () => {
    expect(shouldUseNodeWatcher("linux")).toBe(false);
    expect(buildApiServerArgs("win32", true)).toEqual([
      "-m", "uvicorn", "api.main:app", "--port", "8000",
    ]);
    expect(buildApiServerArgs("linux", true)).toEqual([
      "-m", "uvicorn", "api.main:app", "--port", "8000", "--reload", "--reload-dir", expect.stringContaining("api"),
    ]);
  });

  it("allows reload to be disabled with TIDEAWARE_API_RELOAD=0", () => {
    expect(shouldUseNodeWatcher("win32", false)).toBe(false);
    expect(buildApiServerArgs("linux", false)).toEqual(["-m", "uvicorn", "api.main:app", "--port", "8000"]);
  });
});
