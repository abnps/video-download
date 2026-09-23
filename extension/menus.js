// Stavke u meniju desnog klika. Odluka šta se šalje je ovdje, odvojeno od chrome API-ja,
// da se može testirati bez browsera.

export const MENU_LINK = "videodl-link";
export const MENU_VIDEO = "videodl-video";
export const MENU_PAGE = "videodl-page";
export const MENU_LINK_MP3 = "videodl-link-mp3";
export const MENU_PLAYING_MP3 = "videodl-playing-mp3";

// Ključ prevoda za naslov svake stavke (extension/i18n.js).
export const MENU_ITEMS = [
  { id: MENU_LINK, key: "menu.link", contexts: ["link"] },
  { id: MENU_LINK_MP3, key: "menu.link_mp3", contexts: ["link"] },
  { id: MENU_VIDEO, key: "menu.video", contexts: ["video"] },
  { id: MENU_PAGE, key: "menu.page", contexts: ["page", "frame"] },
  { id: MENU_PLAYING_MP3, key: "menu.playing_mp3", contexts: ["page", "frame", "video"] },
];

const isWebUrl = (value) => /^https?:\/\//i.test(value || "");

/** Šta klik na stavku znači: link, direktan tok videa ili „nađi video koji se pušta" (+ format). */
export function menuTarget(info) {
  const id = info?.menuItemId;
  if (id === MENU_LINK || id === MENU_LINK_MP3) {
    if (!isWebUrl(info.linkUrl)) return null;
    return withPreset({ kind: "url", url: info.linkUrl }, id === MENU_LINK_MP3);
  }
  if (id === MENU_VIDEO) {
    // blob: i MSE (X, Instagram, YouTube) nemaju upotrebljiv link, pa se traži objava.
    return isWebUrl(info.srcUrl) ? { kind: "media", url: info.srcUrl } : { kind: "playing" };
  }
  if (id === MENU_PLAYING_MP3) {
    // Na samom videu sa pravim linkom ide taj tok; inače video koji se pušta.
    return withPreset(isWebUrl(info.srcUrl) ? { kind: "media", url: info.srcUrl } : { kind: "playing" }, true);
  }
  if (id === MENU_PAGE) {
    return { kind: "playing" };
  }
  return null;
}

function withPreset(target, mp3) {
  return mp3 ? { ...target, preset: "mp3" } : target;
}
