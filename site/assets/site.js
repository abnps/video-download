// Video Download — animacije i živi demo (bez biblioteka, bez praćenja). Ako korisnik ne želi pokret, sve je statično.
(() => {
  "use strict";
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const T = window.VD_TEXT || {};
  const num = (x) => x.toFixed(1).replace(".", T.decimal || ".");  // 8,4 MB/s na jezicima sa zarezom

  // Zaglavlje: staklo poslije prvog skrola, malo dugme za preuzimanje kad hero nestane.
  const header = $("header"), hero = $(".hero");
  const onScroll = () => {
    header.classList.toggle("scrolled", scrollY > 8);
    header.classList.toggle("past-hero", hero && scrollY > hero.offsetHeight - 80);
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // „Na vrh": vidljivo tek poslije dva ekrana (PatternFly/Red Hat); vraća na vrh bez #top u adresi.
  const toTop = $(".to-top");
  if (toTop) {
    const showTop = () => toTop.classList.toggle("show", scrollY > innerHeight * 2);
    addEventListener("scroll", showTop, { passive: true });
    showTop();
    toTop.addEventListener("click", (e) => {
      e.preventDefault();
      scrollTo({ top: 0, behavior: calm ? "instant" : "smooth" });
      $(".brand")?.focus({ preventScroll: true });  // tastatura nastavlja od vrha, ne od dna stranice
    });
  }

  // Meni na telefonu (☰): otvara iste linkove; zatvara se na link, Esc ili kad se prozor raširi.
  const menuBtn = $(".menu-btn"), menu = $("#mobile-nav");
  if (menuBtn && menu) {
    const setMenu = (open) => { menu.hidden = !open; menuBtn.setAttribute("aria-expanded", open); };
    menuBtn.addEventListener("click", () => setMenu(menu.hidden));
    menu.addEventListener("click", (e) => e.target.closest("a") && setMenu(false));
    addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !menu.hidden) { setMenu(false); menuBtn.focus(); }
    });
    matchMedia("(min-width: 1041px)").addEventListener("change", (e) => e.matches && setMenu(false));
  }

  // Pauza animacije (demo, pozadina, sjaj). Sajt ništa ne pamti u pregledniku, pa važi dok je stranica otvorena.
  const toggle = $(".anim-toggle");
  let paused = false;
  const setPaused = (on) => {
    paused = on;
    document.documentElement.classList.toggle("paused", on);
    if (!toggle) return;
    toggle.setAttribute("aria-pressed", on);
    $("span", toggle).textContent = on ? toggle.dataset.play : toggle.dataset.pause;
  };
  if (toggle && calm) toggle.hidden = true;  // ko ne želi pokret, ionako ništa ne teče samo

  // Pojavljivanje pri skrolu (i „crtanje" linije koraka). Ako posmatranje ne proradi (stari
  // preglednik, pozadinska kartica), sve postaje vidljivo najkasnije poslije 2,5 s.
  const showAll = () => $$("[data-reveal], .steps").forEach((el) => el.classList.add("in"));
  const canObserve = "IntersectionObserver" in window;
  if (!canObserve) showAll();
  if (canObserve) {
  setTimeout(() => { const first = $(".hero [data-reveal]"); if (first && !first.classList.contains("in")) showAll(); }, 2500);
  const seen = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); seen.unobserve(e.target); }
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
  $$("[data-reveal], .steps").forEach((el) => (calm ? el.classList.add("in") : seen.observe(el)));

  // Brojevi koji odbroje do vrijednosti kad se pojave.
  const count = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      count.unobserve(e.target);
      const el = e.target, end = Number(el.dataset.count), suffix = el.dataset.suffix || "", t0 = performance.now();
      const fmt = (n) => n.toLocaleString(document.documentElement.lang) + suffix;
      if (calm) { el.textContent = fmt(end); continue; }
      const tick = (t) => {
        const k = Math.min(1, (t - t0) / 1200), eased = 1 - Math.pow(1 - k, 3);
        el.textContent = fmt(Math.round(end * eased));
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  }, { threshold: 0.6 });
  $$("[data-count]").forEach((el) => count.observe(el));
  }

  // Svjetlo na pločicama prati miša.
  $$(".tile").forEach((tile) => tile.addEventListener("pointermove", (e) => {
    const r = tile.getBoundingClientRect();
    tile.style.setProperty("--x", `${e.clientX - r.left}px`);
    tile.style.setProperty("--y", `${e.clientY - r.top}px`);
  }));

  // Prozor programa se lagano naginje prema mišu.
  const stage = $(".stage"), app = $(".app");
  if (stage && app && !calm && matchMedia("(pointer: fine)").matches) {
    stage.addEventListener("pointermove", (e) => {
      if (paused) return;
      const r = stage.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      app.style.setProperty("--ry", `${x * 12}deg`);
      app.style.setProperty("--rx", `${-y * 10}deg`);
    });
    stage.addEventListener("pointerleave", () => { app.style.removeProperty("--ry"); app.style.removeProperty("--rx"); });
  }

  // Živi demo: „Zalijepi" doda red koji se preuzme kao u pravom programu.
  const rows = $(".rows"), paste = $(".paste"), announce = $("[data-announce]");
  const demoGo = $(".app-tools .go");
  const demos = T.demos || [];
  const filters = $$(".demo-filter"), summary = $("[data-summary]");
  const updateCounts = () => {
    if (!rows) return;
    const all = $$(".row", rows), done = $$(".done-row", rows).length;
    for (const filter of filters) {
      const count = { all: all.length, active: all.length - done, waiting: 0, done, failed: 0 }[filter.dataset.filter];
      filter.textContent = filter.dataset.template.replace("{count}", count);
    }
    if (summary) summary.textContent = (T.summary_done || "").replace("{count}", done);
  };
  // Čitaču ekrana javljamo samo ono što je posjetilac sam pokrenuo (bez procenata i bez samostalnih redova).
  const say = (text, title) => { if (announce && text) announce.textContent = text.replace("{t}", title); };
  let next = 0, busy = false, idle, progressFrame = 0, resumeProgress = null;
  const svgFolder = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h6l2 2h10v11H3z"/></svg>';
  const rowMarkup = (d, finished) => `<div class="thumb" style="--t1:${d.c1};--t2:${d.c2}"><i>${d.len}</i></div>
      <div class="row-main"><div class="t"></div><div class="row-detail"><span class="format-pill"></span><span class="s${finished ? " done" : ""}"></span></div>
      <div class="bar-p"${finished ? " hidden" : ""}><b class="${d.audio ? "audio" : ""}"></b></div></div>
      <div class="row-actions"><span class="row-play">▶</span><span class="ico" aria-hidden="true">${finished ? svgFolder : "■"}</span><span class="row-convert">MP3</span><span class="row-remove">×</span></div>`;
  const addRow = (byUser = false) => {
    if (!rows || busy || !demos.length) return;
    busy = true; paste.classList.remove("pulse");
    if (app) app.classList.add("downloading");
    if (demoGo) demoGo.textContent = demoGo.dataset.stop;
    const d = demos[next++ % demos.length];
    const row = document.createElement("div");
    row.className = `row${d.audio ? " audio-row" : ""}`;
    row.innerHTML = rowMarkup(d, false);
    row.querySelector(".t").textContent = d.title;
    row.querySelector(".format-pill").textContent = d.fmt;
    rows.prepend(row);
    if (byUser) say(T.added, d.title);
    while (rows.children.length > 4) rows.lastElementChild.remove();
    updateCounts();
    const s = row.querySelector(".s"), bar = row.querySelector(".bar-p b"), ico = row.querySelector(".ico");
    const total = d.mb, speed = d.speed;
    let done = 0, last = performance.now();
    const step = (t) => {
      if (paused || document.hidden) return;
      const dt = Math.max(0, Math.min(0.1, (t - last) / 1000)); last = t;  // prvi okvir zna doći „prije" sata
      done = Math.min(total, done + speed * dt * (0.8 + Math.random() * 0.4));
      const pct = Math.round((done / total) * 100), left = Math.max(0, Math.round((total - done) / speed));
      bar.style.width = `${pct}%`;
      s.textContent = T.progress.replace("{p}", pct).replace("{v}", num(speed)).replace("{s}", left);
      if (done < total) { progressFrame = requestAnimationFrame(step); return; }
      row.classList.add("done-row");
      row.querySelector(".bar-p").hidden = true;
      s.textContent = T.done.replace("{m}", num(total));
      s.classList.add("done");
      ico.classList.add("ok"); ico.innerHTML = svgFolder;
      if (byUser) say(T.ended, d.title);
      busy = false; resumeProgress = null; progressFrame = 0;
      if (app) app.classList.remove("downloading");
      if (demoGo) demoGo.textContent = demoGo.dataset.download;
      updateCounts();
      scheduleIdle();
    };
    resumeProgress = () => { last = performance.now(); progressFrame = requestAnimationFrame(step); };
    if (calm) done = total;
    if (!paused && !document.hidden) resumeProgress();
  };
  const scheduleIdle = () => {
    clearTimeout(idle);
    if (!calm) idle = setTimeout(() => { if (!document.hidden && !paused) addRow(); scheduleIdle(); }, 6500);
  };
  // Na početku dva već gotova preuzimanja, da prozor izgleda kao pravi program.
  if (rows && demos.length) rows.replaceChildren();
  for (const d of (T.finished || [])) {
    const row = document.createElement("div");
    row.className = `row done-row${d.audio ? " audio-row" : ""}`;
    row.style.animation = "none";
    row.innerHTML = rowMarkup(d, true);
    row.querySelector(".t").textContent = d.title;
    row.querySelector(".format-pill").textContent = d.fmt;
    row.querySelector(".s").textContent = T.done.replace("{m}", num(d.mb));
    row.querySelector(".ico").classList.add("ok");
    rows && rows.append(row);
  }
  updateCounts();
  if (paste) {
    paste.addEventListener("click", () => { clearTimeout(idle); addRow(true); });
    setTimeout(() => (calm || !paused) && addRow(), calm ? 0 : 900);
    setTimeout(() => !busy && paste.classList.add("pulse"), 5000);
  }
  if (toggle) {
    toggle.addEventListener("click", () => {
      setPaused(!paused);
      if (paused && app) { app.style.removeProperty("--ry"); app.style.removeProperty("--rx"); }
      if (paused) { cancelAnimationFrame(progressFrame); clearTimeout(idle); }
      else { if (resumeProgress) resumeProgress(); scheduleIdle(); }
    });
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { cancelAnimationFrame(progressFrame); clearTimeout(idle); }
    else if (!paused) { if (resumeProgress) resumeProgress(); scheduleIdle(); }
  });

  // Dodatak: popup se otvori kad sekcija dođe na ekran (i na klik ikone).
  const browser = $(".browser");
  if (browser) {
    if (canObserve) new IntersectionObserver(([e], o) => {
      if (e.isIntersecting) { setTimeout(() => browser.classList.add("open"), calm ? 0 : 500); o.disconnect(); }
    }, { threshold: 0.5 }).observe(browser);
    else browser.classList.add("open");
    $(".ext", browser).addEventListener("click", () => browser.classList.toggle("open"));
  }

  // „Podijeli": prozor kao u aplikacijama (mreže, kopiranje adrese, „Više…" = dijeljenje sistema).
  $$(".share").forEach((box) => {
    const button = $(".share-btn", box), sheet = $(".share-sheet", box);
    const copy = $("[data-copy]", box), input = $(".sheet-copy input", box), more = $(".sheet-more", box);
    const url = box.dataset.url, title = box.dataset.title;
    if (!sheet || typeof sheet.showModal !== "function") {  // vrlo stari preglednik: bar sistemsko dijeljenje ili adresa
      button.addEventListener("click", () => (navigator.share ? navigator.share({ title, url }).catch(() => {}) : prompt("", url)));
      return;
    }
    button.addEventListener("click", () => sheet.showModal());
    $(".sheet-close", box).addEventListener("click", () => sheet.close());
    // Klik na zamućenu pozadinu (van samog prozora) zatvara; Esc zatvara sam <dialog>.
    sheet.addEventListener("click", (e) => {
      const r = sheet.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) sheet.close();
    });
    if (navigator.share) {
      more.hidden = false;
      more.addEventListener("click", () => navigator.share({ title, url }).catch(() => {}));
    }
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(url);
      } catch (e) {
        input.select();
        document.execCommand("copy");  // stariji preglednici bez clipboard dozvole
      }
      copy.textContent = `${box.dataset.copied} ✓`;
      copy.classList.add("done");
      setTimeout(() => { copy.textContent = copy.dataset.label; copy.classList.remove("done"); }, 2200);
    });
    input.addEventListener("focus", () => input.select());
  });

  // Bez skripte su sve platforme vidljive; kartice i skrivanje uključujemo tek kad su spremne.
  const tabs = $$(".tabs a");
  const select = (tab) => {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
  };
  tabs.forEach((tab, i) => {
    tab.setAttribute("role", "tab");
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      const to = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      select(to); to.focus();
    });
  });
  if (tabs.length) { $(".tabs").setAttribute("role", "tablist"); select(tabs[0]); }
  // Dugme „Mac" u vrhu stranice otvara Mac karticu uputstva.
  $$("[data-mac]").forEach((a) => a.addEventListener("click", () => tabs[1] && select(tabs[1])));
  $$("[data-android]").forEach((a) => a.addEventListener("click", () => tabs[2] && select(tabs[2])));
  // Mac posjetilac odmah vidi Mac uputstvo.
  if (/Mac/.test(navigator.platform || navigator.userAgent) && tabs[1]) select(tabs[1]);
  // Posjetilac s Android telefona odmah vidi Android uputstvo.
  if (/Android/.test(navigator.userAgent) && tabs[2]) select(tabs[2]);
  const selectHash = () => {
    const tab = tabs.find((t) => t.getAttribute("href") === location.hash);
    if (tab) select(tab);
  };
  selectHash();
  addEventListener("hashchange", selectHash);
})();
