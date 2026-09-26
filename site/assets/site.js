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

  // Pojavljivanje pri skrolu (i „crtanje" linije koraka). Ako posmatranje ne proradi (stari
  // preglednik, pozadinska kartica), sve postaje vidljivo najkasnije poslije 2,5 s.
  const showAll = () => $$("[data-reveal], .steps").forEach((el) => el.classList.add("in"));
  if (!("IntersectionObserver" in window)) { showAll(); return; }
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
      const r = stage.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      app.style.setProperty("--ry", `${x * 12}deg`);
      app.style.setProperty("--rx", `${-y * 10}deg`);
    });
    stage.addEventListener("pointerleave", () => { app.style.removeProperty("--ry"); app.style.removeProperty("--rx"); });
  }

  // Živi demo: „Zalijepi" doda red koji se preuzme kao u pravom programu.
  const rows = $(".rows"), paste = $(".paste");
  const demos = T.demos || [];
  let next = 0, busy = false, idle;
  const svgDone = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 5 5L20 7"/></svg>';
  const addRow = () => {
    if (!rows || busy || !demos.length) return;
    busy = true; paste.classList.remove("pulse");
    const d = demos[next++ % demos.length];
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<div class="thumb" style="--t1:${d.c1};--t2:${d.c2}"><i>${d.len}</i></div>
      <div><div class="t"></div><div class="s"></div><div class="bar-p"><b class="${d.audio ? "audio" : ""}"></b></div></div>
      <div class="ico" aria-hidden="true">■</div>`;
    row.querySelector(".t").textContent = d.title;
    rows.prepend(row);
    while (rows.children.length > 4) rows.lastElementChild.remove();
    const s = row.querySelector(".s"), bar = row.querySelector(".bar-p b"), ico = row.querySelector(".ico");
    const total = d.mb, speed = d.speed;
    let done = 0, last = performance.now();
    const step = (t) => {
      const dt = Math.max(0, Math.min(0.1, (t - last) / 1000)); last = t;  // prvi okvir zna doći „prije" sata
      done = Math.min(total, done + speed * dt * (0.8 + Math.random() * 0.4));
      const pct = Math.round((done / total) * 100), left = Math.max(0, Math.round((total - done) / speed));
      bar.style.width = `${pct}%`;
      s.textContent = `${d.fmt}   ${T.progress.replace("{p}", pct).replace("{v}", num(speed)).replace("{s}", left)}`;
      if (done < total) return requestAnimationFrame(step);
      bar.classList.add("ok");
      s.textContent = `${d.fmt}   ${T.done.replace("{m}", num(total))}`;
      s.classList.add("done");
      ico.className = "ico ok"; ico.innerHTML = svgDone;
      busy = false;
      scheduleIdle();
    };
    if (calm) { done = total - 0.001; }
    requestAnimationFrame(step);
  };
  const scheduleIdle = () => {
    clearTimeout(idle);
    if (!calm) idle = setTimeout(() => { if (!document.hidden) addRow(); scheduleIdle(); }, 6500);
  };
  // Na početku dva već gotova preuzimanja, da prozor izgleda kao pravi program.
  for (const d of (T.finished || [])) {
    const row = document.createElement("div");
    row.className = "row";
    row.style.animation = "none";
    row.innerHTML = `<div class="thumb" style="--t1:${d.c1};--t2:${d.c2}"><i>${d.len}</i></div>
      <div><div class="t"></div><div class="s done"></div><div class="bar-p"><b class="ok" style="width:100%"></b></div></div>
      <div class="ico ok" aria-hidden="true">${svgDone}</div>`;
    row.querySelector(".t").textContent = d.title;
    row.querySelector(".s").textContent = `${d.fmt}   ${T.done.replace("{m}", num(d.mb))}`;
    rows && rows.append(row);
  }
  if (paste) {
    paste.addEventListener("click", () => { clearTimeout(idle); addRow(); });
    setTimeout(addRow, calm ? 0 : 900);
    setTimeout(() => !busy && paste.classList.add("pulse"), 5000);
  }

  // Dodatak: popup se otvori kad sekcija dođe na ekran (i na klik ikone).
  const browser = $(".browser");
  if (browser) {
    new IntersectionObserver(([e], o) => {
      if (e.isIntersecting) { setTimeout(() => browser.classList.add("open"), calm ? 0 : 500); o.disconnect(); }
    }, { threshold: 0.5 }).observe(browser);
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

  // Kartice Windows / Mac u uputstvu za instalaciju (strelice mijenjaju karticu).
  const tabs = $$('[role="tab"]');
  const select = (tab) => {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const to = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      select(to); to.focus();
    });
  });
  // Dugme „Mac" u vrhu stranice otvara Mac karticu uputstva.
  $$("[data-mac]").forEach((a) => a.addEventListener("click", () => tabs[1] && select(tabs[1])));
  // Mac posjetilac odmah vidi Mac uputstvo.
  if (/Mac/.test(navigator.platform || navigator.userAgent) && tabs[1]) select(tabs[1]);
})();
