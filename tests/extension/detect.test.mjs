import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MAX_MEDIA_PER_TAB,
  MIN_FILE_BYTES,
  addMedia,
  classifyResponse,
  formatSize,
  kindLabel,
} from "../../extension/detect.js";

const response = (url, contentType, extra = {}) => ({
  url,
  type: "xmlhttprequest",
  statusCode: 200,
  responseHeaders: contentType ? [{ name: "Content-Type", value: contentType }] : [],
  ...extra,
});

test("HLS i DASH se prepoznaju po tipu i po ekstenziji", () => {
  assert.equal(classifyResponse(response("https://cdn.a.ba/v/master", "application/vnd.apple.mpegurl")).kind, "hls");
  assert.equal(classifyResponse(response("https://cdn.a.ba/v/index.m3u8?t=1", "application/octet-stream")).kind, "hls");
  assert.equal(classifyResponse(response("https://cdn.a.ba/v/manifest.mpd", "text/plain")).kind, "dash");
  assert.equal(classifyResponse(response("https://cdn.a.ba/v/stream", "application/dash+xml; charset=utf-8")).kind, "dash");
  const withLength = response("https://cdn.a.ba/v/index.m3u8", "application/x-mpegurl");
  withLength.responseHeaders.push({ name: "Content-Length", value: "221" });
  assert.equal(classifyResponse(withLength).size, null);
});

test("segmenti, slike i stranice nisu video tokovi", () => {
  assert.equal(classifyResponse(response("https://cdn.a.ba/v/seg1.ts", "video/mp2t")), null);
  assert.equal(classifyResponse(response("https://cdn.a.ba/v/chunk.m4s", "application/octet-stream")), null);
  assert.equal(classifyResponse(response("https://a.ba/slika.jpg", "image/jpeg")), null);
  assert.equal(classifyResponse(response("https://a.ba/video.mp4", "text/html")), null);
  assert.equal(classifyResponse(response("https://a.ba/x.m3u8", "application/vnd.apple.mpegurl", { statusCode: 403 })), null);
});

test("MP4 se prihvata samo kad ga video element učitava direktno i nije premali", () => {
  const big = [
    { name: "Content-Type", value: "video/mp4" },
    { name: "Content-Range", value: `bytes 0-1023/${10 * MIN_FILE_BYTES}` },
  ];
  const direct = classifyResponse({ url: "https://a.ba/film.mp4", type: "media", statusCode: 206, responseHeaders: big });
  assert.equal(direct.kind, "file");
  assert.equal(direct.size, 10 * MIN_FILE_BYTES);
  assert.equal(direct.label, "a.ba · film.mp4");

  // Komadi koje player skida preko fetch/XHR (MSE) se ne nude.
  assert.equal(classifyResponse({ url: "https://a.ba/film.mp4", type: "xmlhttprequest", statusCode: 206, responseHeaders: big }), null);

  const small = [{ name: "Content-Type", value: "video/mp4" }, { name: "Content-Length", value: "1000" }];
  assert.equal(classifyResponse({ url: "https://a.ba/reklama.mp4", type: "media", statusCode: 200, responseHeaders: small }), null);
});

test("YouTube komadi se ignorišu jer se YouTube preuzima preko stranice", () => {
  const headers = [{ name: "Content-Type", value: "video/mp4" }];
  assert.equal(
    classifyResponse({ url: "https://rr1---sn-x.googlevideo.com/videoplayback?id=1", type: "media", statusCode: 200, responseHeaders: headers }),
    null,
  );
});

test("isti tok sa drugim potpisom zamjenjuje stari, a lista ima granicu", () => {
  const first = { kind: "hls", url: "https://cdn.a.ba/v/index.m3u8?token=1", size: null, label: "x", referer: "https://a.ba/" };
  const again = { ...first, url: "https://cdn.a.ba/v/index.m3u8?token=2" };
  let list = addMedia([], first);
  list = addMedia(list, again);
  assert.equal(list.length, 1);
  assert.equal(list[0].url, again.url);

  for (let i = 0; i < MAX_MEDIA_PER_TAB + 5; i += 1) {
    list = addMedia(list, { kind: "file", url: `https://a.ba/${i}.mp4`, size: null, label: String(i) });
  }
  assert.equal(list.length, MAX_MEDIA_PER_TAB);
});

test("oznake i veličine za prikaz", () => {
  assert.equal(kindLabel({ kind: "hls", url: "https://a.ba/x.m3u8" }), "HLS");
  assert.equal(kindLabel({ kind: "file", url: "https://a.ba/x.webm" }), "WEBM");
  assert.equal(formatSize(null), "");
  assert.equal(formatSize(3.5 * 1024 * 1024), "3,5 MB");
  assert.equal(formatSize(2048), "2 KB");
});

test("neispravni i ne-http linkovi se odbijaju", () => {
  assert.equal(classifyResponse(response("blob:https://a.ba/123", "video/mp4")), null);
  assert.equal(classifyResponse(response("nije link", "video/mp4")), null);
});
