import { formatSize, kindLabel } from "./detect.js";

const pageButton = document.getElementById("download-page");
const resultLine = document.getElementById("result");
let pageSupported = false;

async function currentTab() {
  // ?tabId= služi za testiranje prozora otvorenog kao obična stranica.
  const forced = Number(new URLSearchParams(location.search).get("tabId"));
  if (forced) return chrome.tabs.get(forced);
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
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
    button.textContent = "Preuzmi";
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
}

function setResult(text, kind) {
  resultLine.textContent = text;
  resultLine.className = `result ${kind || ""}`.trim();
}

async function send(tabId, mediaUrl) {
  setBusy(true);
  setResult("Šaljem u Video Download…");
  const reply = await chrome.runtime.sendMessage({ type: "send", tabId, mediaUrl });
  setBusy(false);
  if (reply?.ok) {
    setResult(reply.launched ? "Aplikacija je pokrenuta i video je dodan u red." : "Dodano u red za preuzimanje.", "ok");
  } else {
    setResult(reply?.error || "Slanje nije uspjelo.", "error");
  }
}

async function main() {
  const tab = await currentTab();
  if (!tab) return;
  document.getElementById("page-title").textContent = tab.title || tab.url || "";
  pageSupported = /^https?:/.test(tab.url || "");
  pageButton.disabled = !pageSupported;
  pageButton.addEventListener("click", () => send(tab.id, null));

  const state = await chrome.runtime.sendMessage({ type: "get-state", tabId: tab.id });
  renderMedia(tab, state);

  const status = await chrome.runtime.sendMessage({ type: "app-status" });
  const statusLine = document.getElementById("app-status");
  if (status?.ok) {
    statusLine.textContent = status.running ? "aplikacija radi" : "pokreće se na klik";
  } else {
    statusLine.textContent = "nije povezano";
    statusLine.title = status?.error || "";
  }
}

main();
