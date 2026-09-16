// Browser E2E: Edge (privremeni profil) + ekstenzija + native host + aplikacija + yt-dlp.
//
// Pokretanje iz foldera projekta:  node tools/e2e_browser/run.mjs [--headed]
// Registruje native host (HKCU), pokreće lokalni test sajt, a na kraju gasi Edge, test sajt i
// test instancu aplikacije. Preuzimanja i podešavanja idu u %TEMP%\videodl-e2e, ne u Videos.
import { execFileSync, spawn } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PROJECT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const EXT_ID = "jfgcekfmjipklibljeacchccmebppklp";
const EDGE = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].find(existsSync);
const SITE = "http://127.0.0.1:8765";
const WORK = process.env.VIDEODL_E2E_DIR || path.join(os.tmpdir(), "videodl-e2e");
const PROFILE = path.join(WORK, "edge-profile");
const DATA = path.join(WORK, "data");
const OUT = path.join(WORK, "out");
// Kopija dodatka sa već datom dozvolom za kolačiće: dijalog browsera se u testu ne može kliknuti.
// Isti "key" u manifestu daje isti ID, pa native host prihvata kopiju.
const EXTENSION = path.join(WORK, "extension");
const HEADLESS = !process.argv.includes("--headed");

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const log = (...args) => console.log(new Date().toTimeString().slice(0, 8), ...args);

async function waitFor(check, timeoutMs, label) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    try {
      last = await check();
      if (last) return last;
    } catch (error) {
      last = error.message;
    }
    await sleep(500);
  }
  throw new Error(`Isteklo: ${label} (zadnje: ${JSON.stringify(last)})`);
}

class Cdp {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.nextId = 1;
    this.pending = new Map();
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      const waiter = this.pending.get(message.id);
      if (!waiter) return;
      this.pending.delete(message.id);
      message.error ? waiter.reject(new Error(JSON.stringify(message.error))) : waiter.resolve(message.result);
    };
  }

  open() {
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });
  }

  send(method, params = {}, sessionId, timeoutMs = 10000) {
    const id = this.nextId++;
    this.ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP timeout: ${method}`));
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (value) => { clearTimeout(timer); resolve(value); },
        reject: (error) => { clearTimeout(timer); reject(error); },
      });
    });
  }

  async evaluate(sessionId, expression) {
    const result = await this.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }, sessionId);
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || "JS greška");
    return result.result.value;
  }

  async openPage(url) {
    const { targetId } = await this.send("Target.createTarget", { url });
    const { sessionId } = await this.send("Target.attachToTarget", { targetId, flatten: true });
    return sessionId;
  }
}

function filesIn(folder) {
  if (!existsSync(folder)) return [];
  return readdirSync(folder, { withFileTypes: true, recursive: true })
    .filter((entry) => entry.isFile())
    .map((entry) => path.join(entry.parentPath, entry.name));
}

// fs.cpSync u Node 24 ruši proces (0xC0000409) na putanji projekta sa ćirilicom u OneDrive-u.
function copyTree(source, target) {
  mkdirSync(target, { recursive: true });
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const from = path.join(source, entry.name);
    const to = path.join(target, entry.name);
    if (entry.isDirectory()) copyTree(from, to);
    else copyFileSync(from, to);
  }
}

function killTree(pid) {
  if (!pid) return;
  try {
    execFileSync("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "ignore" });
  } catch {
    // proces je već ugašen
  }
}

async function startServer() {
  const server = spawn("python", [path.join(PROJECT, "tools", "e2e_browser", "server.py"), WORK], {
    stdio: ["ignore", "pipe", "inherit"],
  });
  await new Promise((resolve, reject) => {
    server.stdout.on("data", (chunk) => chunk.toString().includes("ready") && resolve());
    server.on("exit", (code) => reject(new Error(`Test sajt se ugasio (${code})`)));
  });
  return server;
}

async function popupResult(cdp, popup, previous) {
  return waitFor(async () => {
    const text = await cdp.evaluate(popup, `document.getElementById("result").textContent`);
    return text && text !== previous && !text.startsWith("Šaljem") ? text : null;
  }, 60000, "odgovor popupa");
}

async function run(cdp, report) {
  await waitFor(async () => {
    const { targetInfos } = await cdp.send("Target.getTargets");
    return targetInfos.some((t) => t.type === "service_worker" && t.url.startsWith(`chrome-extension://${EXT_ID}/`));
  }, 15000, "ekstenzija učitana");
  // Service worker se gasi kad miruje; stanje se čita sa stranice ekstenzije (isti API-ji).
  const helper = await cdp.openPage(`chrome-extension://${EXT_ID}/popup.html?helper=1`);
  await waitFor(() => cdp.evaluate(helper, `typeof chrome.storage?.session?.get === "function"`), 10000, "pomoćna stranica");
  const tabState = (url, ready) => waitFor(() => cdp.evaluate(helper, `(async () => {
    const tab = (await chrome.tabs.query({})).find((t) => t.url === ${JSON.stringify(url)});
    if (!tab) return null;
    const state = (await chrome.storage.session.get("tab:" + tab.id))["tab:" + tab.id];
    return state && (${ready})(state) ? { tabId: tab.id, state, badge: await chrome.action.getBadgeText({ tabId: tab.id }) } : null;
  })()`), 20000, `stanje taba ${url}`);

  // 1) Stranica sa <video> MP4 i HLS zahtjevom
  await cdp.send("Target.createTarget", { url: `${SITE}/` });
  const page = await tabState(`${SITE}/`, "(s) => s.media.length >= 2");
  report.detected = page.state.media.map(({ kind, label, size, referer }) => ({ kind, label, size, referer }));
  report.badge = page.badge;
  log("Prepoznato:", report.detected.map((m) => m.kind).join(", "), "| badge", page.badge);

  // 2) Popup za taj tab
  const popup = await cdp.openPage(`chrome-extension://${EXT_ID}/popup.html?tabId=${page.tabId}`);
  report.appStatusBefore = await waitFor(() => cdp.evaluate(popup,
    `document.querySelectorAll("#media-list li").length === 2 && document.getElementById("app-status").textContent`), 15000, "popup");
  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 380, height: 420, deviceScaleFactor: 1, mobile: false }, popup);
  const shot = await cdp.send("Page.captureScreenshot", { format: "png" }, popup);
  writeFileSync(path.join(WORK, "popup.png"), Buffer.from(shot.data, "base64"));

  // 3) HLS tok: host pokreće aplikaciju, server bez Referera vraća 403
  await cdp.evaluate(popup, `[...document.querySelectorAll("#media-list li")]
    .find((li) => li.querySelector(".kind").textContent === "HLS").querySelector("button").click()`);
  report.hlsReply = await popupResult(cdp, popup, "");
  const hlsFile = await waitFor(() => filesIn(OUT).find((f) => /^E2E Lekcija 1 \[[0-9a-f]{8}\]\.mp4$/.test(path.basename(f))), 90000, "HLS fajl");
  report.hlsFile = path.relative(OUT, hlsFile);
  log("HLS:", report.hlsReply, "->", report.hlsFile);

  // 4) Cijela stranica preko yt-dlp-a (aplikacija već radi)
  await cdp.evaluate(popup, `document.getElementById("download-page").click()`);
  report.pageReply = await popupResult(cdp, popup, report.hlsReply);
  const pageFile = await waitFor(() => filesIn(OUT).find((f) => f !== hlsFile && f.endsWith(".mp4")), 90000, "fajl sa stranice");
  report.pageFile = path.relative(OUT, pageFile);
  log("Stranica:", report.pageReply, "->", report.pageFile);

  // 5) Feed: „Preuzmi video koji se pušta" mora uzeti objavu videa koji se pušta (222), ne link taba
  const { targetId: feedTarget } = await cdp.send("Target.createTarget", { url: `${SITE}/feed.html` });
  const feed = await tabState(`${SITE}/feed.html`, "() => true");
  const before = new Set(filesIn(OUT));
  const feedPopup = await cdp.openPage(`chrome-extension://${EXT_ID}/popup.html?tabId=${feed.tabId}`);
  await waitFor(() => cdp.evaluate(feedPopup, `!document.getElementById("download-playing").disabled`), 10000, "dugme za video koji se pušta");
  // Pravi popup stoji iznad vidljive stranice; skriveni tab ne pušta video.
  await cdp.send("Target.activateTarget", { targetId: feedTarget });
  await sleep(2500);
  await cdp.evaluate(feedPopup, `document.getElementById("download-playing").click()`);
  report.playingReply = await popupResult(cdp, feedPopup, "");
  const playingFile = await waitFor(() => filesIn(OUT).find((f) => !before.has(f) && path.basename(f).startsWith("Objava 222")), 90000, "fajl objave 222");
  report.playingFile = path.relative(OUT, playingFile);
  log("Video koji se pušta:", report.playingReply, "->", report.playingFile);

  // 6) Iza prijave: objava i video bez kolačića sesije vraćaju 403
  const { targetId: privateTarget } = await cdp.send("Target.createTarget", { url: `${SITE}/privatno.html` });
  const privateTab = await tabState(`${SITE}/privatno.html`, "() => true");
  const beforePrivate = new Set(filesIn(OUT));
  const privatePopup = await cdp.openPage(`chrome-extension://${EXT_ID}/popup.html?tabId=${privateTab.tabId}`);
  await waitFor(() => cdp.evaluate(privatePopup, `!document.getElementById("download-playing").disabled`), 10000, "popup privatno");
  await cdp.send("Target.activateTarget", { targetId: privateTarget });
  await sleep(2500);
  await cdp.evaluate(privatePopup, `document.getElementById("download-playing").click()`);
  report.privateReply = await popupResult(cdp, privatePopup, "");
  const privateFile = await waitFor(() => filesIn(OUT).find((f) => !beforePrivate.has(f) && path.basename(f).startsWith("Privatna 333")), 90000, "fajl iza prijave");
  report.privateFile = path.relative(OUT, privateFile);
  const serverLog = readFileSync(path.join(WORK, "server.log"), "utf8");
  report.privateForbidden = (serverLog.match(/"GET \/privatno\/[^"]*" 403/g) || []).length;
  log("Iza prijave:", report.privateReply, "->", report.privateFile, "| 403:", report.privateForbidden);
  if (report.privateForbidden) throw new Error("Server je odbio zahtjev bez kolačića sesije");

  // 7) DRM stranica
  await cdp.send("Target.createTarget", { url: `${SITE}/drm.html` });
  const drm = await tabState(`${SITE}/drm.html`, "(s) => s.drm");
  report.drmBadge = drm.badge;
  const drmPopup = await cdp.openPage(`chrome-extension://${EXT_ID}/popup.html?tabId=${drm.tabId}`);
  report.drmNotice = await waitFor(() => cdp.evaluate(drmPopup, `!document.getElementById("drm").hidden`), 10000, "DRM poruka");
  log("DRM:", report.drmBadge);
}

async function main() {
  if (!EDGE) throw new Error("Microsoft Edge nije pronađen.");
  for (const folder of [PROFILE, OUT]) rmSync(folder, { recursive: true, force: true });
  rmSync(path.join(DATA, "bridge.json"), { force: true });
  mkdirSync(PROFILE, { recursive: true });
  mkdirSync(DATA, { recursive: true });
  rmSync(EXTENSION, { recursive: true, force: true });
  copyTree(path.join(PROJECT, "extension"), EXTENSION);
  const manifestPath = path.join(EXTENSION, "manifest.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  manifest.permissions.push("cookies");
  delete manifest.optional_permissions;
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  writeFileSync(path.join(DATA, "settings.ini"),
    `[General]\r\noutput_dir=${OUT.replaceAll("\\", "\\\\")}\r\npreset_key=best\r\n`);
  execFileSync("python", ["-m", "videodl.native_messaging"], { cwd: PROJECT, stdio: "ignore" });

  const server = await startServer();
  const edge = spawn(EDGE, [
    `--user-data-dir=${PROFILE}`,
    `--load-extension=${EXTENSION}`,
    `--disable-extensions-except=${EXTENSION}`,
    "--remote-debugging-port=0",
    "--no-first-run",
    "--no-default-browser-check",
    "--autoplay-policy=no-user-gesture-required",
    ...(HEADLESS ? ["--headless=new"] : []),
    "about:blank",
  ], { env: { ...process.env, VIDEODL_DATA_DIR: DATA }, stdio: "ignore" });

  const report = {};
  let cdp;
  try {
    const portFile = path.join(PROFILE, "DevToolsActivePort");
    const [port, wsPath] = await waitFor(() => existsSync(portFile) && readFileSync(portFile, "utf8").trim().split("\n"), 20000, "DevTools port");
    cdp = new Cdp(`ws://127.0.0.1:${port}${wsPath}`);
    await cdp.open();
    await run(cdp, report);
    report.ok = true;
  } catch (error) {
    report.ok = false;
    report.error = error.message;
  } finally {
    const bridge = existsSync(path.join(DATA, "bridge.json")) ? JSON.parse(readFileSync(path.join(DATA, "bridge.json"), "utf8")) : null;
    await cdp?.send("Browser.close").catch(() => {});
    killTree(edge.pid);
    killTree(bridge?.pid);
    killTree(server.pid);
  }
  writeFileSync(path.join(WORK, "report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (!report.ok) process.exitCode = 1;
}

main().catch((error) => {
  console.error("E2E greška:", error.message);
  process.exitCode = 1;
});
