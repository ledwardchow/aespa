export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ErrorBody = { detail?: string | Array<{ loc?: Array<string | number>; msg?: string }> };
export function formatError(data: unknown): string | null {
  if (!data) return null;
  const detail = (data as ErrorBody).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((item) => `${(item.loc || []).join(".")}: ${item.msg}`).join("\n");
  return JSON.stringify(data);
}

export async function readResponse<T>(response: Response): Promise<T | null> {
  if (response.status === 204) return null;
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      // Preserve the HTTP status for plain-text or HTML proxy error pages.
      if (response.ok) throw new Error("The server returned an invalid response");
    }
  }
  if (!response.ok)
    throw new ApiError(
      formatError(data) || `${response.status} ${response.statusText}`,
      response.status,
    );
  return data as T | null;
}

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };
export async function req<T = unknown>(
  url: string,
  { body, headers, ...options }: RequestOptions = {},
): Promise<T | null> {
  const requestHeaders = new Headers(headers);
  const multipart = body instanceof FormData;
  if (!multipart && !requestHeaders.has("Content-Type"))
    requestHeaders.set("Content-Type", "application/json");
  return readResponse<T>(
    await fetch(url, {
      ...options,
      method: options.method || "GET",
      headers: requestHeaders,
      body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
    }),
  );
}

/** Import text is already serialized JSON. Do not serialize it a second time. */
export async function importJson<T = unknown>(
  url: string,
  text: string,
  signal?: AbortSignal,
): Promise<T | null> {
  return readResponse<T>(
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: text,
      signal,
    }),
  );
}
