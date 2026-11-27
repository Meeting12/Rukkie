import { getCSRFToken } from "./api";

export type PaymentLinkState = "invalid" | "pending" | "processing" | "paid" | "failed" | "expired" | "revoked" | "too_late" | "attempt_limit";

type Failure = { detail?: string; errors?: Record<string, string[]> };

export async function paymentLinkRequest<T>(path: string, body?: object): Promise<{ status: number; data: T & Failure }> {
  const headers = new Headers({ Accept: "application/json" });
  if (body) {
    headers.set("Content-Type", "application/json");
    const csrf = getCSRFToken();
    if (csrf) headers.set("X-CSRFToken", csrf);
  }
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
    credentials: "same-origin",
  });
  const data = await response.json().catch(() => ({})) as T & Failure;
  return { status: response.status, data };
}

export function paymentLinkError(data: Failure): string {
  return data.detail || Object.values(data.errors || {}).flat()[0] || "The request could not be completed. Please try again.";
}
