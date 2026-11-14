import { describe, expect, it } from "vitest";
import { buildApiServerArgs } from "./dev-api-options.mjs";

describe("dev API server options", () => {
  it("does not start the Uvicorn reload worker on Windows by default", () => {
    expect(buildApiServerArgs("win32")).toEqual(["-m", "uvicorn", "api.main:app", "--port", "8000"]);
  });

  it("keeps reload available when explicitly enabled", () => {
    expect(buildApiServerArgs("win32", true)).toEqual([
      "-m", "uvicorn", "api.main:app", "--port", "8000", "--reload", "--reload-dir", expect.stringContaining("api"),
    ]);
  });
});
