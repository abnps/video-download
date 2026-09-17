// Stavke u meniju desnog klika. Odluka šta se šalje je ovdje, odvojeno od chrome API-ja,
// da se može testirati bez browsera.

export const MENU_LINK = "videodl-link";
export const MENU_VIDEO = "videodl-video";
export const MENU_PAGE = "videodl-page";

// Ključ prevoda za naslov svake stavke (extension/i18n.js).
export const MENU_ITEMS = [
  { id: MENU_LINK, key: "menu.link", contexts: ["link"] },
  { id: MENU_VIDEO, key: "menu.video", contexts: ["video"] },
  { id: MENU_PAGE, key: "menu.page", contexts: ["page", "frame"] },
];

const isWebUrl = (value) => /^https?:\/\//i.test(value || "");

/** Šta klik na stavku znači: link, direktan tok videa ili „nađi video koji se pušta". */
export function menuTarget(info) {
  if (info?.menuItemId === MENU_LINK) {
    return isWebUrl(info.linkUrl) ? { kind: "url", url: info.linkUrl } : null;
  }
  if (info?.menuItemId === MENU_VIDEO) {
    // blob: i MSE (X, Instagram, YouTube) nemaju upotrebljiv link, pa se traži objava.
    return isWebUrl(info.srcUrl) ? { kind: "media", url: info.srcUrl } : { kind: "playing" };
  }
  if (info?.menuItemId === MENU_PAGE) {
    return { kind: "playing" };
  }
  return null;
}
