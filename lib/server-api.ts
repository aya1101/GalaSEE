/**
 * Resolve the FastAPI service URL for server-side route handlers.
 *
 * Vercel injects TIDEAWARE_API_URL from the app -> api service binding at
 * runtime. EARTHDATA_API_URL remains a local-development fallback for the
 * standalone npm dev workflow; it is not the Vercel binding variable.
 */
export function serverApiUrl(): string | undefined {
  // Bracket access keeps Next from replacing the binding with a build-time
  // value; Vercel injects service bindings only when the function runs.
  const boundUrl = process.env["TIDEAWARE_API_URL"];
  const localUrl = process.env["EARTHDATA_API_URL"];
  return (boundUrl || localUrl)?.replace(/\/$/, "");
}
