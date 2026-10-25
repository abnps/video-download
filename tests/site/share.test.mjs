import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import vm from "node:vm";

const source = await readFile(new URL("../../site/assets/site.js", import.meta.url), "utf8");

function sharing(clipboardWorks, fallbackWorks) {
  const node = () => ({
    textContent: "Copy", dataset: { label: "Copy" }, handlers: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener(name, callback) { this.handlers[name] = callback; },
  });
  const copy = node(), input = { ...node(), selected: false, select() { this.selected = true; }, focus() {} };
  const children = {
    ".share-btn": node(), ".share-sheet": { ...node(), showModal() {} },
    "[data-copy]": copy, ".sheet-copy input": input, ".sheet-more": node(), ".sheet-close": node(),
  };
  const box = { dataset: { url: "https://example.org/app", title: "App", copied: "Copied" },
    querySelector: (selector) => children[selector] };
  const document = {
    documentElement: node(), addEventListener() {}, execCommand: () => fallbackWorks,
    querySelector: (selector) => selector === "header" ? node() : null,
    querySelectorAll: (selector) => selector === ".share" ? [box] : [],
  };
  vm.runInNewContext(source, {
    document, window: {}, scrollY: 0, location: { hash: "" },
    navigator: { clipboard: { writeText: async () => { if (!clipboardWorks) throw new Error("Denied"); } },
      platform: "Windows", userAgent: "Test" },
    matchMedia: () => ({ matches: true }), addEventListener() {}, setTimeout() {}, clearTimeout() {},
  });
  return { copy, input };
}

test("sajt ne tvrdi da je link kopiran kada oba načina zakažu", async () => {
  const { copy, input } = sharing(false, false);
  await copy.handlers.click();
  assert.equal(copy.textContent, "Copy");
  assert.equal(input.selected, true);
});

test("potvrda kopiranja pojavljuje se samo poslije uspješnog upisa", async () => {
  for (const clipboardWorks of [true, false]) {
    const { copy } = sharing(clipboardWorks, true);
    await copy.handlers.click();
    assert.equal(copy.textContent, "Copied ✓");
  }
});
