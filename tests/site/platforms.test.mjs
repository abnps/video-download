import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import vm from "node:vm";

const source = await readFile(new URL("../../site/assets/site.js", import.meta.url), "utf8");

function page(userAgent = "Windows", hash = "") {
  const node = (dataset = {}, attributes = {}) => ({
    dataset, attributes, hidden: false, handlers: {}, textContent: "Download", href: "",
    classList: { add() {}, remove() {}, toggle() {} },
    setAttribute(key, value) { this.attributes[key] = String(value); },
    getAttribute(key) { return this.attributes[key]; },
    addEventListener(key, handler) { this.handlers[key] = handler; },
    focus() { this.focused = true; },
  });
  const names = ["win", "mac", "android"];
  const choices = names.map((platform) => node({ platform }));
  const links = names.map((platformDownload) => Object.assign(node({ platformDownload }), {
    href: `https://example.org/${platformDownload}`, textContent: `Download ${platformDownload}`,
  }));
  const requirements = names.map((platformRequirements) => node({ platformRequirements }));
  const tabs = names.map((name) => node({}, { href: `#panel-${name}`, "aria-controls": `panel-${name}` }));
  const panels = Object.fromEntries(names.map((name) => [`panel-${name}`, node()]));
  const choice = node(), short = node(), help = node(), events = {};
  const store = node({ platformDownload: "win" });
  const singles = { header: node(), ".tabs": node(), ".platform-choice": choice,
    "[data-download-short]": short, "[data-install-help]": help };
  const groups = { ".tabs a": tabs, "[data-platform]": choices, "a[data-platform-download]": links,
    "[data-platform-download]": [...links, store], "[data-platform-requirements]": requirements };
  const location = { hash };
  vm.runInNewContext(source, {
    document: { documentElement: node(), addEventListener() {},
      querySelector: (selector) => singles[selector] || null,
      querySelectorAll: (selector) => groups[selector] || [], getElementById: (id) => panels[id] },
    window: {}, navigator: { userAgent, platform: userAgent }, location, scrollY: 0,
    matchMedia: () => ({ matches: true }),
    addEventListener: (event, callback) => { events[event] = callback; }, setTimeout() {}, clearTimeout() {},
  });
  return { choices, links, store, requirements, tabs, panels, choice, short, help, location, events };
}

function selected(p, name) {
  assert.equal(p.choice.hidden, false);
  assert.equal(p.links.find((a) => !a.hidden).dataset.platformDownload, name);
  assert.equal(p.links.filter((a) => !a.hidden).length, 1);
  assert.equal(p.requirements.find((a) => !a.hidden).dataset.platformRequirements, name);
  assert.equal(p.choices.find((a) => a.attributes["aria-pressed"] === "true").dataset.platform, name);
  assert.equal(p.short.href, `https://example.org/${name}`);
  assert.equal(p.short.attributes["aria-label"], `Download ${name}`);
  assert.equal(p.help.href, `#panel-${name}`);
  assert.equal(p.panels[`panel-${name}`].hidden, false);
  assert.equal(p.store.hidden, name !== "win");
}

test("glavno i malo dugme nude paket za posjetiočev sistem", () => {
  for (const [ua, name] of [["Windows", "win"], ["MacIntel", "mac"], ["Linux Android", "android"], ["Linux", "win"]]) {
    selected(page(ua), name);
  }
});

test("ručni izbor platforme usklađuje paket i upute bez skrola", () => {
  const p = page("Android");
  p.choices[1].handlers.click();
  selected(p, "mac");
  assert.equal(p.location.hash, "");
  p.tabs[0].handlers.click();
  selected(p, "win");
  let prevented = false;
  p.tabs[0].handlers.keydown({ key: "ArrowRight", preventDefault() { prevented = true; } });
  selected(p, "mac");
  assert.equal(prevented, true);
  assert.equal(p.tabs[1].focused, true);
});

test("direktan link na Android upute ima prednost nad automatskim izborom", () => {
  const p = page("Windows", "#panel-android");
  selected(p, "android");
  p.location.hash = "#panel-mac";
  p.events.hashchange();
  selected(p, "mac");
});
