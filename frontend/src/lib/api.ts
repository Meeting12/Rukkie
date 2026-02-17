export function getCSRFToken(): string | null {
  const match = document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'));
  return match ? match[2] : null;
}

function toTitleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function extractErrorMessage(payload: any, fallback: string): string {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload || fallback;

  if (payload.error === "insufficient_stock") {
    const available = Number(payload.available_stock ?? 0);
    if (Number.isFinite(available) && available <= 0) {
      return "This product is currently out of stock.";
    }
    return payload.detail || `Insufficient stock. Only ${available} item(s) available.`;
  }

  if (typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;
  if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
  if (typeof payload.error === "string" && payload.error.trim()) {
    return toTitleCase(payload.error);
  }

  if (Array.isArray(payload.fields) && payload.fields.length) {
    return `Missing required fields: ${payload.fields.join(", ")}`;
  }

  return fallback;
}

export async function fetchJSON(input: RequestInfo, init: RequestInit = {}) {
  const headers: Record<string,string> = {
    'Accept': 'application/json',
  };
  if (init && init.body) {
    headers['Content-Type'] = 'application/json';
    const csrftoken = getCSRFToken();
    if (csrftoken) headers['X-CSRFToken'] = csrftoken;
  }
  const res = await fetch(input, { ...init, headers });
  const contentType = res.headers.get("content-type") || "";
  let payload: any = null;
  let textPayload = "";

  if (contentType.includes("application/json")) {
    payload = await res.json().catch(() => null);
  } else {
    textPayload = await res.text();
    if (textPayload) {
      try {
        payload = JSON.parse(textPayload);
      } catch {
        payload = null;
      }
    }
  }

  if (!res.ok) {
    const fallback = textPayload || res.statusText || "Request failed";
    const message = extractErrorMessage(payload || textPayload, fallback);
    throw new Error(message);
  }

  if (res.status === 204) {
    return { ok: true };
  }

  if (payload !== null) {
    return payload;
  }

  if (!textPayload) {
    return {};
  }

  try {
    return JSON.parse(textPayload);
  } catch {
    return { detail: textPayload };
  }
}
