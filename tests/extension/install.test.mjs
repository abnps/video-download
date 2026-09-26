import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { TEXT_KEYS } from "../../extension/i18n.js";
import { detectBrowser, shouldWelcome, siteUrl } from "../../extension/install.js";

const read = (name) => readFileSync(new URL(`../../extension/${name}`, import.meta.url), "utf8");

test("dobrodošlica samo pri prvoj instalaciji, ne pri ažuriranju dodatka ili browsera", () => {
  assert.equal(shouldWelcome({ reason: "install" }), true);
  assert.equal(shouldWelcome({ reason: "update", previousVersion: "0.5.2" }), false);
  assert.equal(shouldWelcome({ reason: "chrome_update" }), false);
  assert.equal(shouldWelcome({ reason: "shared_module_update" }), false);
  assert.equal(shouldWelcome(undefined), false);
});

test("uputstvo za kačenje ikone prema browseru", () => {
  const chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";
  assert.equal(detectBrowser(chrome), "chrome");
  assert.equal(detectBrowser(`${chrome} Edg/140.0.0.0`), "edge");
  assert.equal(detectBrowser(chrome, [{ brand: "Microsoft Edge", version: "140" }]), "edge");
  assert.equal(detectBrowser("Mozilla/5.0 (Windows NT 10.0; rv:150.0) Gecko/20100101 Firefox/150.0"), "firefox");
  for (const browser of ["chrome", "edge", "firefox"]) assert.ok(TEXT_KEYS.includes(`welcome.pin_${browser}`), browser);
});

test("linkovi na sajt na jeziku stranice", () => {
  assert.equal(siteUrl("en"), "https://abnps.github.io/video-download/");
  assert.equal(siteUrl("de", "extension.html"), "https://abnps.github.io/video-download/de/extension.html");
});

test("stranica dobrodošlice: svaki tekst ima prevod, otvara je pozadina, ništa ne učitava s interneta", () => {
  const html = read("welcome.html");
  for (const [, key] of html.matchAll(/data-i18n="([^"]+)"/g)) assert.ok(TEXT_KEYS.includes(key), key);
  for (const [, key] of read("welcome.js").matchAll(/t\("([\w.]+)"/g)) assert.ok(TEXT_KEYS.includes(key), key);
  assert.doesNotMatch(html + read("welcome.css"), /<script[^>]+src="https?:|@import|url\(https?:/);
  assert.doesNotMatch(read("welcome.js"), /fetch\(|XMLHttpRequest/);
  const background = read("background.js");
  assert.match(background, /shouldWelcome\(details\)/);
  assert.match(background, /getURL\("welcome\.html"\)/);
});
