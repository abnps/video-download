// Izolovani svijet ekstenzije: prosljeđuje DRM signal iz drm-main.js pozadinskom dijelu.
let reported = false;
window.addEventListener("message", (event) => {
  if (reported || event.source !== window || event.data?.source !== "video-download-drm") return;
  reported = true;
  chrome.runtime.sendMessage({ type: "drm-detected" }).catch(() => {});
});
