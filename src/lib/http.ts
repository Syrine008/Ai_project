/** Session-authenticated API calls. No credentials or tokens are stored in browser storage. */
export async function apiFetch(url: string, init: RequestInit): Promise<Response> {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim().replace(/\/$/, "");
  if (!base) throw new Error("The analysis service is not configured. Contact your administrator.");
  let session: Response;
  try {
    session = await fetch(`${base}/api/session/`, { credentials: "include" });
  } catch {
    throw new Error("Cannot reach the analysis service. Check your connection and try again.");
  }
  if (!session.ok) throw new Error("The analysis service is unavailable. Please try again later.");
  const state = await session.json();
  if (state.authenticationRequired && !state.authenticated)
    throw new Error("Sign in to the analysis service using the Sign in link above, then retry.");
  const headers = new Headers(init.headers);
  headers.set("X-CSRFToken", state.csrfToken);
  const response = await fetch(url, { ...init, headers, credentials: "include" });
  if (response.status === 403)
    throw new Error("Your session has expired or access was denied. Sign in and retry.");
  return response;
}
