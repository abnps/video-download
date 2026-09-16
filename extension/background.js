import { addMedia, classifyResponse, headerValue } from "./detect.js";
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
    sendToApp(message.tabId, message.mediaUrl).then(sendResponse);
    return true;
  }
  if (message?.type === "send-playing") {
    sendPlaying(message.tabId).then(sendResponse);
    return true;
  }
  return false;
});

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
    if (!media) return { error: "Tok više nije na listi. Osvježi stranicu i pokreni video ponovo." };
    request.media = { url: media.url, kind: media.kind };
    request.headers.Referer = media.referer || tab.url;
  }
  return { request };
}

// Feed (X, TikTok, Instagram…): link taba nije link videa, pa se traži objava videa koji se pušta.
async function sendPlaying(tabId) {
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
  let target = "stranica";
  const feedSite = /(^|\.)(tiktok\.com|x\.com|twitter\.com|instagram\.com|facebook\.com)$/.test(new URL(tab.url).hostname);
  const instagramStory = /(^|\.)instagram\.com$/.test(new URL(tab.url).hostname)
    && new URL(tab.url).pathname.startsWith("/stories/");
  if (best && instagramStory && !best.directSrc) {
    // yt-dlp stories preuzima samo uz prijavu (kolačiće), a dodatak ih ne šalje.
    await flashBadge(tabId, false);
    return {
      ok: false,
      error: "Instagram stories se mogu preuzeti samo uz prijavu (kolačiće), a to još nije uključeno. "
        + `Dijagnostika: ${JSON.stringify(best.debug)}`,
    };
  }
  if (best && !best.postUrl && !best.directSrc && feedSite) {
    // Link feeda yt-dlp ne može preuzeti; bolje jasna poruka nego neuspio red u aplikaciji.
    await flashBadge(tabId, false);
    return {
      ok: false,
      error: "Nisam našao link ovog videa. Klikni na video da se otvori, pa pokušaj ponovo, "
        + `ili kopiraj link desnim klikom. Dijagnostika: ${JSON.stringify(best.debug)}`,
    };
  }
  if (best?.postUrl) {
    request.page_url = best.postUrl;
    target = best.postUrl;
  } else if (best?.directSrc) {
    request.media = { url: best.directSrc, kind: "file" };
    request.headers.Referer = best.frameUrl;
    target = best.directSrc;
  } else if (!best) {
    const reply = { ok: false, error: "Na stranici nema videa. Pokreni video pa pokušaj ponovo." };
    await flashBadge(tabId, false);
    return reply;
  }
  const reply = await sendNative({ action: "add", request });
  await flashBadge(tabId, reply.ok);
  return { ...reply, target };
}

async function sendToApp(tabId, mediaUrl) {
  const { request, error } = await buildRequest(tabId, mediaUrl);
  const reply = error ? { ok: false, error } : await sendNative({ action: "add", request });
  await flashBadge(tabId, reply.ok);
  return reply;
}

function sendNative(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendNativeMessage(NATIVE_HOST, message, (reply) => {
      const failure = chrome.runtime.lastError;
      if (failure) {
        resolve({ ok: false, error: nativeError(failure.message || "") });
        return;
      }
      resolve(reply || { ok: false, error: "Aplikacija nije odgovorila." });
    });
  });
}

function nativeError(message) {
  if (/not found|forbidden/i.test(message)) {
    return "Aplikacija nije povezana sa browserom. Pokreni Video Download jednom ručno (pokreni.bat).";
  }
  return `Veza sa aplikacijom nije uspjela: ${message}`;
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
