// Radi u svijetu stranice: javlja kad stranica stvarno pokrene DRM zaštićenu reprodukciju.
// Samo provjera podrške (npr. YouTube) ne okida poruku; tek generateRequest za licencu.
(() => {
  const proto = window.MediaKeySession && window.MediaKeySession.prototype;
  if (!proto || proto.__videoDownloadHooked) return;
  const original = proto.generateRequest;
  Object.defineProperty(proto, "__videoDownloadHooked", { value: true });
  proto.generateRequest = function generateRequest(...args) {
    try {
      window.postMessage({ source: "video-download-drm" }, "*");
    } catch {
      // javljanje ne smije pokvariti reprodukciju
    }
    return original.apply(this, args);
  };
})();
