import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { LANGUAGES, RAW_TEXTS, TEXT_KEYS, pickLanguage, translate } from "../../extension/i18n.js";

const placeholders = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();

test("svaki tekst popupa postoji na svih 5 jezika sa istim mjestima za vrijednosti", () => {
  for (const key of TEXT_KEYS) {
    const texts = RAW_TEXTS[key];
    assert.equal(texts.length, LANGUAGES.length, key);
    for (const text of texts) {
      assert.ok(text.trim(), key);
      assert.deepEqual(placeholders(text), placeholders(texts[0]), key);
    }
  }
});

test("svaki data-i18n ključ iz popup.html i svaka šifra greške iz pozadine ima prevod", () => {
  const html = readFileSync(new URL("../../extension/popup.html", import.meta.url), "utf8");
  for (const [, key] of html.matchAll(/data-i18n="([^"]+)"/g)) assert.ok(TEXT_KEYS.includes(key), key);
  const background = readFileSync(new URL("../../extension/background.js", import.meta.url), "utf8");
  for (const [, code] of background.matchAll(/code: "([\w-]+)"/g)) assert.ok(TEXT_KEYS.includes(`error.${code}`), code);
});

test("jezik i prevod", () => {
  assert.equal(pickLanguage("sr-Cyrl-RS"), "bs");
  assert.equal(pickLanguage("de-AT"), "de");
  assert.equal(pickLanguage("ja"), "en");
  assert.equal(translate("fr", "popup.sent", { url: "https://a" }), "Envoyé : https://a");
  assert.equal(translate("xx", "popup.download"), "Preuzmi");
  assert.equal(translate("en", "nema.kljuca"), "nema.kljuca");
});
