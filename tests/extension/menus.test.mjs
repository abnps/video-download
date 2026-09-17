import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { TEXT_KEYS, translate } from "../../extension/i18n.js";
import { MENU_ITEMS, MENU_LINK, MENU_PAGE, MENU_VIDEO, menuTarget } from "../../extension/menus.js";

test("desni klik na link šalje taj link, a ne stranicu", () => {
  assert.deepEqual(menuTarget({ menuItemId: MENU_LINK, linkUrl: "https://x.com/a/status/1" }),
    { kind: "url", url: "https://x.com/a/status/1" });
  // javascript:, mailto: i slično nisu video
  assert.equal(menuTarget({ menuItemId: MENU_LINK, linkUrl: "javascript:void(0)" }), null);
  assert.equal(menuTarget({ menuItemId: MENU_LINK }), null);
});

test("desni klik na video: direktan tok ide odmah, blob traži objavu", () => {
  assert.deepEqual(menuTarget({ menuItemId: MENU_VIDEO, srcUrl: "https://c.test/clip.mp4" }),
    { kind: "media", url: "https://c.test/clip.mp4" });
  for (const srcUrl of ["blob:https://x.com/1234", "data:video/mp4;base64,AA", undefined]) {
    assert.deepEqual(menuTarget({ menuItemId: MENU_VIDEO, srcUrl }), { kind: "playing" });
  }
});

test("desni klik na stranicu traži video koji se pušta", () => {
  assert.deepEqual(menuTarget({ menuItemId: MENU_PAGE }), { kind: "playing" });
  assert.equal(menuTarget({ menuItemId: "nesto-drugo" }), null);
});

test("svaka stavka menija ima prevod i koristi se u pozadinskoj skripti", () => {
  const background = readFileSync(new URL("../../extension/background.js", import.meta.url), "utf8");
  assert.match(background, /MENU_ITEMS/);
  for (const item of MENU_ITEMS) {
    assert.ok(TEXT_KEYS.includes(item.key), item.key);
    assert.ok(translate("bs", item.key).trim(), item.key);
    assert.ok(item.contexts.length, item.id);
  }
});
