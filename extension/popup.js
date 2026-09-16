import { formatSize, kindLabel } from "./detect.js";
import { pickLanguage, translate } from "./i18n.js";

const pageButton = document.getElementById("download-page");
const playingButton = document.getElementById("download-playing");
const resultLine = document.getElementById("result");
let pageSupported = false;
// Jezik browsera dok aplikacija ne javi svoj (isti kao u aplikaciji).
let language = pickLanguage(navigator.language);
let lastResult = null;

const t = (key, values) => translate(language, key, values);

async function currentTab() {
  // ?tabId= služi za testiranje prozora otvorenog kao obična stranica.
  const forced = Number(new URLSearchParams(location.search).get("tabId"));
  if (forced) return chrome.tabs.get(forced);
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function applyTexts() {
  document.documentElement.lang = language;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  for (const button of document.querySelectorAll("#media-list button")) button.textContent = t("popup.download");
  if (lastResult) showReply(lastResult);
}

function renderMedia(tab, state) {
  const list = document.getElementById("media-list");
  list.replaceChildren();
  for (const media of state.media) {
    const row = document.createElement("li");
    const kind = document.createElement("span");
    kind.className = "kind";
    kind.textContent = kindLabel(media);
    const label = document.createElement("span");
    label.className = "label";
    label.textContent = media.label;
    label.title = media.url;
    const size = document.createElement("span");
    size.className = "size";
    size.textContent = formatSize(media.size);
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = t("popup.download");
    button.addEventListener("click", () => send(tab.id, media.url));
    row.append(kind, label, size, button);
    list.append(row);
  }
  document.getElementById("media-empty").hidden = state.media.length > 0;
  document.getElementById("drm").hidden = !state.drm;
}

function setBusy(busy) {
  for (const button of document.querySelectorAll("button")) button.disabled = busy;
  pageButton.disabled = busy || !pageSupported;
  playingButton.disabled = busy || !pageSupported;
}

function setResult(text, kind) {
  resultLine.textContent = text;
  resultLine.className = `result ${kind || ""}`.trim();
}

function showReply(reply) {
  lastResult = reply;
  if (reply?.ok) {
    const sent = reply.target && /^https?:/.test(reply.target) ? ` ${t("popup.sent", { url: reply.target })}` : "";
    setResult(t(reply.launched ? "popup.launched" : "popup.added") + sent, "ok");
  } else if (reply?.code) {
    setResult(t(`error.${reply.code}`, { detail: reply.detail || "" }), "error");
  } else {
    setResult(reply?.error || t("popup.failed"), "error");
  }
}

async function send(tabId, mediaUrl, type = "send") {
  // Dozvola za kolačiće (video iza prijave) traži se kroz dijalog browsera, samo prvi put;
  // mora biti prvi poziv u kliku. Odbijanje ne smeta: preuzimanje ide bez prijave.
  await chrome.permissions.request({ permissions: ["cookies"] }).catch(() => false);
  setBusy(true);
  lastResult = null;
  setResult(t("popup.sending"));
  const reply = await chrome.runtime.sendMessage({ type, tabId, mediaUrl });
  setBusy(false);
  showReply(reply);
}

async function main() {
  // Verzija u zaglavlju: odmah se vidi da li je poslije izmjene urađen „Reload".
  document.getElementById("version").textContent = `v${chrome.runtime.getManifest().version}`;
  applyTexts();
  const tab = await currentTab();
  if (!tab) return;
  document.getElementById("page-title").textContent = tab.title || tab.url || "";
  pageSupported = /^https?:/.test(tab.url || "");
  pageButton.disabled = !pageSupported;
  playingButton.disabled = !pageSupported;
  pageButton.addEventListener("click", () => send(tab.id, null));
  playingButton.addEventListener("click", () => send(tab.id, null, "send-playing"));

  const state = await chrome.runtime.sendMessage({ type: "get-state", tabId: tab.id });
  renderMedia(tab, state);

  const status = await chrome.runtime.sendMessage({ type: "app-status" });
  const statusLine = document.getElementById("app-status");
  if (status?.language) {
    language = pickLanguage(status.language);
    applyTexts();
  }
  if (status?.ok) {
    statusLine.textContent = t(status.running ? "status.running" : "status.idle");
  } else {
    statusLine.textContent = t("status.offline");
    statusLine.title = status?.code ? t(`error.${status.code}`, { detail: status.detail || "" }) : "";
  }
}

main();
