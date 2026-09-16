// Prepoznavanje video tokova iz mrežnih odgovora. Bez Chrome API-ja, pa se testira u Node-u.

const HLS_TYPES = new Set([
  "application/vnd.apple.mpegurl",
  "application/x-mpegurl",
  "audio/mpegurl",
  "audio/x-mpegurl",
]);
const DASH_TYPES = new Set(["application/dash+xml"]);
const FILE_TYPES = new Set([
  "video/mp4",
  "video/webm",
  "video/x-matroska",
  "video/quicktime",
  "video/x-flv",
  "video/ogg",
  "video/x-m4v",
  "video/3gpp",
]);
const GENERIC_TYPES = new Set(["", "application/octet-stream", "binary/octet-stream", "application/binary"]);
const FILE_EXTENSIONS = new Set(["mp4", "webm", "mkv", "mov", "m4v", "flv", "ogv"]);

// Fajl koji <video> učitava direktno. Fetch/XHR MP4 odgovori su obično komadi (MSE),
// koji se sami ne mogu pustiti.
const DIRECT_FILE_REQUESTS = new Set(["media", "main_frame", "sub_frame", "object", "other"]);

// Kratki fajlovi su najčešće reklame ili pregledi pri prelasku mišem.
export const MIN_FILE_BYTES = 512 * 1024;
export const MAX_MEDIA_PER_TAB = 25;

// Na ovim sajtovima video ide preko linka stranice; njihovi tokovi su samo komadi.
const PAGE_ONLY_HOSTS = [/(^|\.)googlevideo\.com$/];

export function headerValue(headers, name) {
  const wanted = name.toLowerCase();
  const found = (headers || []).find((header) => header.name.toLowerCase() === wanted);
  return found ? found.value : null;
}

export function classifyResponse({ url, type, statusCode, responseHeaders }) {
  if (statusCode >= 400) return null;
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
  if (PAGE_ONLY_HOSTS.some((pattern) => pattern.test(parsed.hostname))) return null;

  const contentType = (headerValue(responseHeaders, "content-type") || "").split(";")[0].trim().toLowerCase();
  const kind = kindOf(contentType, extensionOf(parsed.pathname));
  if (!kind) return null;

  // Za HLS/DASH bi to bila veličina manifesta, ne videa, pa se ne prikazuje.
  const size = kind === "file" ? totalSize(statusCode, responseHeaders) : null;
  if (kind === "file") {
    if (!DIRECT_FILE_REQUESTS.has(type)) return null;
    if (size !== null && size < MIN_FILE_BYTES) return null;
  }
  return { kind, url, size, label: shortLabel(parsed) };
}

function kindOf(contentType, extension) {
  if (HLS_TYPES.has(contentType)) return "hls";
  if (DASH_TYPES.has(contentType)) return "dash";
  if (FILE_TYPES.has(contentType)) return "file";
  if (!GENERIC_TYPES.has(contentType) && !contentType.startsWith("text/")) return null;
  if (extension === "m3u8") return "hls";
  if (extension === "mpd") return "dash";
  return FILE_EXTENSIONS.has(extension) ? "file" : null;
}

function extensionOf(pathname) {
  const last = pathname.split("/").pop() || "";
  const dot = last.lastIndexOf(".");
  return dot > 0 ? last.slice(dot + 1).toLowerCase() : "";
}

function totalSize(statusCode, headers) {
  const range = headerValue(headers, "content-range");
  const match = range && /\/(\d+)\s*$/.exec(range);
  if (match) return Number(match[1]);
  const length = headerValue(headers, "content-length");
  return statusCode === 200 && length && /^\d+$/.test(length) ? Number(length) : null;
}

export function shortLabel(parsed) {
  let name = parsed.pathname.split("/").filter(Boolean).pop() || "";
  try {
    name = decodeURIComponent(name);
  } catch {
    // ostavi originalni zapis
  }
  if (name.length > 40) name = `${name.slice(0, 37)}…`;
  return name ? `${parsed.hostname} · ${name}` : parsed.hostname;
}

// Isti tok (isti put, drugi potpis u linku) se ne ponavlja; novi link zamjenjuje stari.
export function addMedia(list, media, max = MAX_MEDIA_PER_TAB) {
  const key = mediaKey(media);
  const index = list.findIndex((item) => mediaKey(item) === key);
  if (index >= 0) {
    const next = list.slice();
    next[index] = { ...list[index], ...media, size: media.size ?? list[index].size };
    return next;
  }
  return list.length >= max ? list : [...list, media];
}

function mediaKey(media) {
  const parsed = new URL(media.url);
  return `${media.kind}|${parsed.origin}${parsed.pathname}`;
}

export function kindLabel(media) {
  if (media.kind === "hls") return "HLS";
  if (media.kind === "dash") return "DASH";
  const extension = extensionOf(new URL(media.url).pathname);
  return extension ? extension.toUpperCase() : "VIDEO";
}

export function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit >= 2 ? 1 : 0;
  return `${value.toFixed(digits).replace(".", ",")} ${units[unit]}`;
}
