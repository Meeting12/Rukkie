function stripQueryHash(url: string): { base: string; suffix: string } {
  const input = String(url || "");
  const qIndex = input.indexOf("?");
  const hIndex = input.indexOf("#");
  const cut =
    qIndex === -1
      ? hIndex
      : hIndex === -1
      ? qIndex
      : Math.min(qIndex, hIndex);
  if (cut === -1) return { base: input, suffix: "" };
  return { base: input.slice(0, cut), suffix: input.slice(cut) };
}

function stripKnownCloudinaryPrefixes(value: string): string {
  let out = String(value || "").replace(/^\/+/, "");
  out = out.replace(/^v\d+\/media\//i, "");
  out = out.replace(/^v\d+\//i, "");
  out = out.replace(/^media\//i, "");
  return out;
}

function splitUploadUrl(base: string): { prefix: string; tail: string } | null {
  const marker = "/image/upload/";
  const idx = String(base || "").indexOf(marker);
  if (idx < 0) return null;
  return {
    prefix: base.slice(0, idx + marker.length),
    tail: base.slice(idx + marker.length).replace(/^\/+/, ""),
  };
}

export function getCloudinaryRetryCandidates(src: string): string[] {
  const normalized = String(src || "").replace(/^http:\/\//i, "https://");
  if (!normalized.includes("res.cloudinary.com/")) return [];

  const { base, suffix } = stripQueryHash(normalized);
  const candidates: string[] = [];
  const seen = new Set<string>();

  const add = (value: string) => {
    const next = `${value}${suffix}`;
    if (!next || next === normalized || seen.has(next)) return;
    seen.add(next);
    candidates.push(next);
  };

  // Keep retries intentionally conservative to avoid noisy 404 storms.
  // Most live failures are truly missing public IDs; aggressive extension/folder
  // guessing produces hundreds of failed requests with no recovery benefit.
  const variants = new Set<string>();
  const uploadParts = splitUploadUrl(base);
  if (!uploadParts) return [];

  const tail = stripKnownCloudinaryPrefixes(uploadParts.tail);
  if (!tail) return [];

  const normalizedTail = tail.replace(/^media\//i, "");
  variants.add(`${uploadParts.prefix}${normalizedTail}`);
  variants.add(`${uploadParts.prefix}v1/media/${normalizedTail}`);
  variants.add(`${uploadParts.prefix}media/${normalizedTail}`);

  for (const variant of variants) {
    add(variant);
  }

  return candidates.slice(0, 2);
}

export function advanceImageFallback(target: HTMLImageElement, fallbackSrc: string): void {
  if (!target || !fallbackSrc) return;
  if (target.src === fallbackSrc) return;

  let candidates: string[] = [];
  try {
    candidates = JSON.parse(target.dataset.rukkieFallbackCandidates || "[]");
    if (!Array.isArray(candidates)) candidates = [];
  } catch {
    candidates = [];
  }

  if (!candidates.length) {
    candidates = getCloudinaryRetryCandidates(target.currentSrc || target.src || "");
    target.dataset.rukkieFallbackCandidates = JSON.stringify(candidates);
    target.dataset.rukkieFallbackIndex = "0";
  }

  const idx = Number(target.dataset.rukkieFallbackIndex || "0");
  if (Number.isFinite(idx) && idx < candidates.length) {
    target.dataset.rukkieFallbackIndex = String(idx + 1);
    target.src = candidates[idx];
    return;
  }

  target.src = fallbackSrc;
}
