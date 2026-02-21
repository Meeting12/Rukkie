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

  const variants = [base];
  const folders = ["products", "categories", "hero"];
  for (const folder of folders) {
    variants.push(base.replace(`/image/upload/${folder}/`, `/image/upload/v1/${folder}/`));
    variants.push(base.replace(`/image/upload/v1/${folder}/`, `/image/upload/${folder}/`));
    variants.push(base.replace(`/image/upload/${folder}/`, `/image/upload/media/${folder}/`));
    variants.push(base.replace(`/image/upload/media/${folder}/`, `/image/upload/${folder}/`));
    variants.push(base.replace(`/image/upload/v1/${folder}/`, `/image/upload/v1/media/${folder}/`));
    variants.push(base.replace(`/image/upload/v1/media/${folder}/`, `/image/upload/v1/${folder}/`));
  }

  for (const variant of variants) {
    add(variant);
    const lastPart = (variant.split("/").pop() || "").toLowerCase();
    const hasExt = /\.[a-z0-9]{2,5}$/i.test(lastPart);
    if (!hasExt) {
      add(`${variant}.jpg`);
      add(`${variant}.png`);
      add(`${variant}.webp`);
    }
  }

  return candidates;
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

