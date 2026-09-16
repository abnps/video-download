// Pokreće se NA STRANICI (chrome.scripting.executeScript), zato funkcija ne smije
// koristiti ništa izvan sebe. Traži video koji se pušta i link objave kojoj pripada.
export function findPlayingVideo() {
  const POST_PATTERNS = [
    /\/status(?:es)?\/\d+/, // X / Twitter
    /\/video\/\d+/, // TikTok
    // Instagram, Facebook: /reels/audio/… je stranica muzike, ne video (isto isključuje i yt-dlp)
    /\/(?:reels?|p|tv)\/(?!audio\/)[\w-]{5,}/,
    /\/videos?\/[\w.-]+/, // Facebook, Vimeo i slični
    /\/shorts\/[\w-]+/, // YouTube Shorts
    /\/watch\?(?:.*&)?v=[\w-]+/, // YouTube
  ];

  function postUrl(href) {
    let url;
    try {
      url = new URL(href, location.href);
    } catch {
      return null;
    }
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    const path = url.pathname + url.search;
    if (!POST_PATTERNS.some((pattern) => pattern.test(path))) return null;
    // X: /status/123/photo/1, /analytics i slično vode na istu objavu.
    const status = /^(.*\/status(?:es)?\/\d+)/.exec(url.pathname);
    if (status) return url.origin + status[1];
    url.hash = "";
    return url.href;
  }

  function visibleArea(element) {
    const rect = element.getBoundingClientRect();
    const width = Math.max(0, Math.min(rect.right, innerWidth) - Math.max(rect.left, 0));
    const height = Math.max(0, Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0));
    return width * height;
  }

  const candidates = [...document.querySelectorAll("video")]
    .map((video) => ({
      video,
      playing: !video.paused && !video.ended && video.currentTime > 0,
      started: video.currentTime > 0, // pokrenut pa pauziran i dalje je „onaj" video
      area: visibleArea(video),
    }))
    .filter((candidate) => candidate.playing || candidate.area > 0);
  if (!candidates.length) return null;
  candidates.sort((a, b) => Number(b.playing) - Number(a.playing)
    || Number(b.started) - Number(a.started) || b.area - a.area);
  const { video, playing, area } = candidates[0];

  // Penje se od videa kroz roditelje dok je u njima samo taj jedan video (jedna
  // objava u feedu) i uzima link objave; link sa <time> je na X-u link same objave.
  let found = null;
  // Instagram storija ili otvoren reel: link je sam tab; okolni linkovi vode na tuđe
  // storije, muziku (/reels/audio/) ili druge reelove.
  if (/(^|\.)instagram\.com$/.test(location.hostname)
      && /^\/(?:stories\/[^/]+(?:\/\d+)?|(?:[^/]+\/)?(?:reels?|p|tv)\/(?!audio\/)[\w-]{5,})\/?$/.test(location.pathname)) {
    found = location.origin + location.pathname;
  }
  for (let node = video.parentElement; !found && node && node !== document.body; node = node.parentElement) {
    if (node.querySelectorAll("video").length > 1) break;
    const links = [...node.querySelectorAll("a[href]")];
    const withTime = links.find((link) => link.querySelector("time") && postUrl(link.getAttribute("href")));
    const link = withTime || links.find((candidate) => postUrl(candidate.getAttribute("href")));
    if (link) {
      found = postUrl(link.getAttribute("href"));
      break;
    }
  }

  // TikTok feed nema link /video/: ID je u omotaču playera (xgwrapper-<n>-<ID>),
  // a autor je prvi /@ link u istoj objavi. Tako nastaje isti link kao „Kopiraj link".
  let item = video;
  for (let node = video.parentElement; node && node !== document.body; node = node.parentElement) {
    if (node.querySelectorAll("video").length > 1) break;
    item = node;
  }
  // Kartica objave može imati i drugi <video> (npr. zamućenu pozadinu), pa se traži i po oznaci.
  const card = video.closest('article, [data-e2e="recommend-list-item-container"], [data-e2e*="item-container"]') || item;

  // TikTok feed nema link /video/: ID je u omotaču playera (xgwrapper-<n>-<ID>) ili u
  // drugom id/data atributu kartice, a autor je /@ link u istoj objavi.
  if (!found && /(^|\.)tiktok\.com$/.test(location.hostname)) {
    let videoId = null;
    for (let node = video; node && node !== card.parentElement; node = node.parentElement) {
      const match = /^xgwrapper-\d+-(\d{15,})$/.exec(node.id || "");
      if (match) {
        videoId = match[1];
        break;
      }
    }
    if (!videoId) {
      for (const element of [card, ...card.querySelectorAll("*")]) {
        for (const attribute of element.attributes) {
          const isIdAttribute = attribute.name === "id" || attribute.name.startsWith("data-");
          const isVideoLink = attribute.name === "href" && attribute.value.includes("/video/");
          const match = (isIdAttribute || isVideoLink) && /(?:^|\D)(7\d{18})(?:\D|$)/.exec(attribute.value);
          if (match) {
            videoId = match[1];
            break;
          }
        }
        if (videoId) break;
      }
    }
    if (videoId) {
      const author = [...card.querySelectorAll('a[href*="/@"]')]
        .map((link) => /\/@([\w.-]+)\/?(?:\?.*)?$/.exec(link.getAttribute("href")))
        .find(Boolean);
      found = `https://www.tiktok.com/@${author ? author[1] : ""}/video/${videoId}`;
    }
  }

  return {
    postUrl: found || postUrl(location.href),
    directSrc: /^https?:/.test(video.currentSrc) ? video.currentSrc : null,
    frameUrl: location.href,
    playing,
    area,
    // Kratak opis stranice kad objava nije nađena, da se problem može popraviti.
    debug: found ? null : {
      videos: document.querySelectorAll("video").length,
      card: `${card.tagName.toLowerCase()}#${card.id || ""}[${card.getAttribute("data-e2e") || ""}]`,
      numbers: [...new Set([card, ...card.querySelectorAll("*")].flatMap((element) => [...element.attributes]
        .filter((attribute) => /\d{15,}/.test(attribute.value))
        .map((attribute) => `${attribute.name}=${attribute.value.slice(0, 60)}`)))].slice(0, 5),
      links: [...card.querySelectorAll("a[href]")].map((link) => link.getAttribute("href").slice(0, 60)).slice(0, 6),
    },
  };
}
