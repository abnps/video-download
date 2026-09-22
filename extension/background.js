import { addMedia, classifyResponse, headerValue } from "./detect.js";
import { pickLanguage, translate } from "./i18n.js";
import { MENU_ITEMS, menuTarget } from "./menus.js";
import { findPlayingVideo } from "./playing.js";

const NATIVE_HOST = "com.videodl.bridge";
const WATCHED_TYPES = ["main_frame", "sub_frame", "media", "xmlhttprequest", "object", "other"];
const MAX_TRACKED_REFERERS = 500;

// Referer kojim je browser tražio tok; mnogi serveri bez njega odbiju preuzimanje.
const referers = new Map();

// Stanje po tabu: memorija + storage.session, jer se service worker gasi kad miruje.
const cache = new Map();
const pending = new Map();

function emptyState(pageUrl = "") {
  return { pageUrl, media: [], drm: false };
}

async function loadState(tabId) {
  if (cache.has(tabId)) return cache.get(tabId);
  const key = `tab:${tabId}`;
  const stored = (await chrome.storage.session.get(key))[key];
  const state = stored || emptyState();
  cache.set(tabId, state);
  return state;
}

// Izmjene jednog taba idu redom, da se istovremeni odgovori ne prepišu međusobno.
function updateState(tabId, change) {
  const run = async () => {
    const next = change(structuredClone(await loadState(tabId)));
    cache.set(tabId, next);
    await chrome.storage.session.set({ [`tab:${tabId}`]: next });
    await refreshBadge(tabId, next);
    return next;
  };
  const result = (pending.get(tabId) || Promise.resolve()).then(run, run);
  pending.set(tabId, result.catch(() => {}));
  return result;
}

async function refreshBadge(tabId, state) {
  const text = state.drm ? "DRM" : state.media.length ? String(state.media.length) : "";
  try {
    await chrome.action.setBadgeBackgroundColor({ tabId, color: state.drm ? "#c62828" : "#6c4ce0" });
    await chrome.action.setBadgeText({ tabId, text });
  } catch {
    // tab je u međuvremenu zatvoren
  }
}

chrome.webRequest.onSendHeaders.addListener(
  (details) => {
    if (details.tabId < 0) return;
    const referer = headerValue(details.requestHeaders, "referer");
    if (!referer) return;
    referers.set(details.requestId, referer);
    if (referers.size > MAX_TRACKED_REFERERS) referers.delete(referers.keys().next().value);
  },
  { urls: ["<all_urls>"], types: WATCHED_TYPES },
  ["requestHeaders", "extraHeaders"],
);

chrome.webRequest.onHeadersReceived.addListener(
  (details) => {
    if (details.tabId < 0) return;
    const referer = referers.get(details.requestId) || null;
    referers.delete(details.requestId);
    const media = classifyResponse(details);

    if (details.type === "main_frame") {
      // Nova stranica u tabu: stari tokovi više ne važe.
      updateState(details.tabId, () => {
        const state = emptyState(details.url);
        if (media) state.media = addMedia([], { ...media, referer: null });
        return state;
      });
      return;
    }
    if (media) {
      updateState(details.tabId, (state) => ({ ...state, media: addMedia(state.media, { ...media, referer }) }));
    }
  },
  { urls: ["<all_urls>"], types: WATCHED_TYPES },
  ["responseHeaders"],
);

// Navigacija bez učitavanja stranice (npr. SPA) mijenja samo link taba.
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (!changeInfo.url) return;
  updateState(tabId, (state) => (state.pageUrl === changeInfo.url ? state : emptyState(changeInfo.url)));
});

chrome.tabs.onRemoved.addListener((tabId) => {
  cache.delete(tabId);
  pending.delete(tabId);
  chrome.storage.session.remove(`tab:${tabId}`);
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "drm-detected" && sender.tab) {
    updateState(sender.tab.id, (state) => ({ ...state, drm: true }));
    return false;
  }
  // Ostale radnje smiju tražiti samo stranice ekstenzije (popup), ne skripte na web stranicama.
  if (sender.id !== chrome.runtime.id || !sender.url?.startsWith(chrome.runtime.getURL(""))) return false;

  if (message?.type === "get-state") {
    loadState(message.tabId).then(sendResponse);
    return true;
  }
  if (message?.type === "app-status") {
    sendNative({ action: "status" }).then(sendResponse);
    return true;
  }
  if (message?.type === "send") {
    sendToApp(message.tabId, message.mediaUrl, message.preset).then(sendResponse);
    return true;
  }
  if (message?.type === "send-playing") {
    sendPlaying(message.tabId, message.preset).then(sendResponse);
    return true;
  }
  return false;
});

// Meni desnog klika: radi i kad prepoznavanje toka zataji i bez otvaranja prozora dodatka.
async function setupMenus() {
  const status = await sendNative({ action: "status" }).catch(() => null);
  const language = pickLanguage(status?.language || navigator.language);
  await chrome.contextMenus.removeAll();
  for (const item of MENU_ITEMS) {
    chrome.contextMenus.create({ id: item.id, title: translate(language, item.key), contexts: item.contexts });
  }
}

chrome.runtime.onInstalled.addListener(setupMenus);
chrome.runtime.onStartup.addListener(setupMenus);

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (tab && tab.id >= 0) sendFromMenu(info, tab.id);
});

async function sendFromMenu(info, tabId) {
  const target = menuTarget(info);
  if (!target) return;
  if (target.kind === "playing") {
    await sendPlaying(tabId);
    return;
  }
  const tab = await chrome.tabs.get(tabId);
  const request = {
    page_url: target.kind === "url" ? target.url : tab.url,
    page_title: tab.title || "",
    headers: { "User-Agent": navigator.userAgent },
  };
  if (target.kind === "media") {
    request.media = { url: target.url, kind: "file" };
    request.headers.Referer = info.frameUrl || tab.url;
  }
  // Kolačići samo ako je dozvola već data kroz prozor dodatka; meni je ne može tražiti.
  request.cookies = await cookiesFor([tab.url, request.page_url, request.media?.url]);
  const reply = await sendNative({ action: "add", request });
  await flashBadge(tabId, reply.ok);
}

async function buildRequest(tabId, mediaUrl) {
  const tab = await chrome.tabs.get(tabId);
  const request = {
    page_url: tab.url,
    page_title: tab.title || "",
    headers: { "User-Agent": navigator.userAgent },
  };
  if (mediaUrl) {
    const state = await loadState(tabId);
    const media = state.media.find((item) => item.url === mediaUrl);
    if (!media) return { error: { ok: false, code: "media-gone" } };
    request.media = { url: media.url, kind: media.kind };
    request.headers.Referer = media.referer || tab.url;
  }
  return { request };
}

// Feed (X, TikTok, Instagram…): link taba nije link videa, pa se traži objava videa koji se pušta.
async function sendPlaying(tabId, preset) {
  const tab = await chrome.tabs.get(tabId);
  let frames = [];
  try {
    frames = await chrome.scripting.executeScript({ target: { tabId, allFrames: true }, func: findPlayingVideo });
  } catch {
    // stranica ne dozvoljava skripte (npr. prodavnica ekstenzija); ide se na link taba
  }
  const best = frames
    .map((frame) => frame.result)
    .filter(Boolean)
    .sort((a, b) => Number(b.playing) - Number(a.playing) || b.area - a.area)[0];

  const request = { page_url: tab.url, page_title: tab.title || "", headers: { "User-Agent": navigator.userAgent } };
  let target = "";
  const feedSite = /(^|\.)(tiktok\.com|x\.com|twitter\.com|instagram\.com|facebook\.com)$/.test(new URL(tab.url).hostname);
  const instagramStory = /(^|\.)instagram\.com$/.test(new URL(tab.url).hostname)
    && new URL(tab.url).pathname.startsWith("/stories/");
  if (best && instagramStory && !(await chrome.permissions.contains({ permissions: ["cookies"] }))) {
    // yt-dlp stories preuzima samo uz prijavu, a dozvola za kolačiće nije data.
    await flashBadge(tabId, false);
    return { ok: false, code: "story-login" };
  }
  if (best && !best.postUrl && !best.directSrc && feedSite) {
    // Link feeda yt-dlp ne može preuzeti; bolje jasna poruka nego neuspio red u aplikaciji.
    await flashBadge(tabId, false);
    return { ok: false, code: "feed-no-post", detail: JSON.stringify(best.debug) };
  }
  if (best?.live) {
    await flashBadge(tabId, false);
    return { ok: false, code: "live" };
  }
  if (best?.postUrl) {
    request.page_url = best.postUrl;
    target = best.postUrl;
  } else if (best?.directSrc) {
    request.media = { url: best.directSrc, kind: "file" };
    request.headers.Referer = best.frameUrl;
    target = best.directSrc;
  } else if (!best) {
    const reply = { ok: false, code: "no-video" };
    await flashBadge(tabId, false);
    return reply;
  }
  request.cookies = await cookiesFor([tab.url, request.page_url, request.media?.url]);
  if (preset) request.preset = preset;  // npr. „mp3": aplikacija snima samo zvuk
  const reply = await sendNative({ action: "add", request });
  await flashBadge(tabId, reply.ok);
  return { ...reply, target };
}

// Kolačići prijave samo za sajtove sa kojih se preuzima, i samo ako je Ahmed u browseru
// dao opcionu dozvolu „cookies". Aplikacija ih ne čuva.
async function cookiesFor(urls) {
  if (!(await chrome.permissions.contains({ permissions: ["cookies"] }))) return [];
  const found = new Map();
  for (const url of new Set(urls.filter((value) => /^https?:/.test(value || "")))) {
    let cookies = [];
    try {
      cookies = await chrome.cookies.getAll({ url });
    } catch {
      continue;
    }
    for (const cookie of cookies) {
      found.set(`${cookie.domain}|${cookie.path}|${cookie.name}`, {
        name: cookie.name,
        value: cookie.value,
        domain: cookie.domain,
        path: cookie.path,
        secure: cookie.secure,
        hostOnly: cookie.hostOnly,
        expirationDate: cookie.expirationDate,
      });
    }
  }
  return [...found.values()];
}

async function sendToApp(tabId, mediaUrl, preset) {
  const { request, error } = await buildRequest(tabId, mediaUrl);
  if (request) {
    request.cookies = await cookiesFor([request.page_url, request.media?.url]);
    if (preset) request.preset = preset;
  }
  const reply = error || (await sendNative({ action: "add", request }));
  await flashBadge(tabId, reply.ok);
  return reply;
}

function sendNative(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendNativeMessage(NATIVE_HOST, message, (reply) => {
      const failure = chrome.runtime.lastError;
      if (failure) {
        const detail = failure.message || "";
        resolve(/not found|forbidden/i.test(detail) ? { ok: false, code: "not-connected" } : { ok: false, code: "connection", detail });
        return;
      }
      resolve(reply || { ok: false, code: "no-reply" });
    });
  });
}

async function flashBadge(tabId, ok) {
  try {
    await chrome.action.setBadgeBackgroundColor({ tabId, color: ok ? "#2e7d32" : "#c62828" });
    await chrome.action.setBadgeText({ tabId, text: ok ? "✓" : "!" });
  } catch {
    return;
  }
  setTimeout(() => loadState(tabId).then((state) => refreshBadge(tabId, state)), 3000);
}
