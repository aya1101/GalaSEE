const rawApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";

export const apiBaseUrl = rawApiUrl.replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}
