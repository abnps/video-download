// Stranica dobrodošlice: stvarna provjera veze s programom i uputstvo za ovaj browser. Ništa ne šalje na internet.
import { detectBrowser, siteUrl } from "./install.js";
import { pickLanguage, translate } from "./i18n.js";

let language = pickLanguage(navigator.language);
let lastStatus = null;
const t = (key, values) => translate(language, key, values);
const $ = (id) => document.getElementById(id);
const browser = detectBrowser(navigator.userAgent, navigator.userAgentData?.brands || []);

function applyTexts() {
  document.documentElement.lang = language;
  for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
  $("pin-text").textContent = t(`welcome.pin_${browser}`);
  $("click-text").textContent = t("welcome.click_text", { button: t("popup.playing") });
  $("get-app").href = siteUrl(language);
  $("help").href = siteUrl(language, "extension.html");
  $("support").href = `${siteUrl(language)}#support`;
  if (lastStatus) showStatus(lastStatus);
}

function showStatus(status) {
  lastStatus = status;
  const box = $("connection");
  const more = $("status-more");
  box.dataset.state = status?.ok ? "ok" : "offline";
  if (status?.ok) {
    $("status-text").textContent = t("welcome.connected");
    more.textContent = status.running ? "" : t("welcome.starts");
  } else {
    // Program nije registrovan kod browsera (nije instaliran ili nije nijednom pokrenut) ili se nije javio.
    $("status-text").textContent = t(`error.${status?.code || "no-reply"}`, { detail: status?.detail || "" });
    more.textContent = "";
  }
  more.hidden = !more.textContent;
  $("get-app").hidden = Boolean(status?.ok);
  $("retry").hidden = Boolean(status?.ok);
}

async function check() {
  $("connection").dataset.state = "checking";
  $("status-text").textContent = t("welcome.checking");
  const status = await chrome.runtime.sendMessage({ type: "app-status" }).catch(() => null);
  if (status?.language) {
    language = pickLanguage(status.language);  // isti jezik kao u programu
    lastStatus = status;
    applyTexts();
  }
  showStatus(status);
}

$("version").textContent = `v${chrome.runtime.getManifest().version}`;
$("retry").addEventListener("click", check);
applyTexts();
check();
