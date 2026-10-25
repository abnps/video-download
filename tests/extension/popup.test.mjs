import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import vm from "node:vm";

import { formatSize, kindLabel } from "../../extension/detect.js";
import { pickLanguage, translate } from "../../extension/i18n.js";

const source = (await readFile(new URL("../../extension/popup.js", import.meta.url), "utf8"))
  .replace(/^import .*;\r?\n/gm, "");

async function popup() {
  const elements = new Map();
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      textContent: "", className: "", disabled: false, hidden: false,
      addEventListener() {}, replaceChildren() {},
    });
    return elements.get(id);
  };
  const buttons = ["download-page", "download-playing", "download-playing-mp3"].map(element);
  const runtime = {
    getManifest: () => ({ version: "1.0.3" }),
    sendMessage: async ({ type }) => type === "get-state" ? { media: [], drm: false } : { ok: true },
  };
  const context = vm.createContext({
    document: {
      documentElement: {}, getElementById: element,
      querySelectorAll: (selector) => selector === "button" ? buttons : [],
    },
    navigator: { language: "en" }, location: { search: "" }, URLSearchParams,
    chrome: {
      runtime, permissions: { request: async () => false },
      tabs: { query: async () => [{ id: 1, url: "https://example.org/video", title: "Video" }] },
    },
    formatSize, kindLabel, pickLanguage, translate,
  });
  vm.runInContext(source + "\nglobalThis.actions = { send, main };", context);
  await new Promise(setImmediate);
  return { ...context.actions, runtime, element, buttons };
}

test("neuspjelo slanje pokaže grešku i vrati dugmad za novi pokušaj", async () => {
  const ui = await popup();
  ui.runtime.sendMessage = async () => { throw new Error("Extension context invalidated"); };
  await ui.send(1, null);
  assert.equal(ui.element("result").textContent, translate("en", "popup.failed"));
  assert.equal(ui.element("result").className, "result error");
  assert.ok(ui.buttons.every((button) => !button.disabled));
  ui.runtime.sendMessage = async () => ({ ok: true });
  await ui.send(1, null);
  assert.match(ui.element("result").textContent, /Added to the download queue/);
});

test("nedostupna pozadina ne ostavlja prazan status pri otvaranju popupa", async () => {
  const ui = await popup();
  ui.runtime.sendMessage = async () => { throw new Error("Could not establish connection"); };
  await ui.main();
  assert.equal(ui.element("app-status").textContent, translate("en", "status.offline"));
  assert.ok(ui.buttons.every((button) => !button.disabled));
});
