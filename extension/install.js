// Stranica dobrodošlice: kad se otvara i koja uputstva za kačenje ikone važe za koji browser.

// Samo prva instalacija; ažuriranje dodatka ili browsera ne otvara karticu ponovo.
export function shouldWelcome(details) {
  return details?.reason === "install";
}

// Edge i Firefox imaju drugačije dugme za kačenje ikone nego Chrome (i Brave, Opera…, koji rade kao Chrome).
export function detectBrowser(userAgent = "", brands = []) {
  const names = brands.map((brand) => brand.brand || "");
  if (/Firefox\//.test(userAgent)) return "firefox";
  if (names.includes("Microsoft Edge") || /\bEdg\//.test(userAgent)) return "edge";
  return "chrome";
}

// Adresa sajta na jeziku stranice (engleski je glavni, ostali u podfolderu).
export function siteUrl(language, page = "") {
  return `https://abnps.github.io/video-download/${language === "en" ? "" : `${language}/`}${page}`;
}
