"""Privatna statistika za autora (Ahmed 4.10.2026): preuzimanja i aktivne instalacije, bez praćenja korisnika.

    python tools/statistika.py          → osvježi podatke i otvori stranicu u browseru
    python tools/statistika.py --no-open

Izvor su GitHub-ovi brojači preuzimanja fajlova iz izdanja (čita se `gh`-om, pa se vide i stara izdanja u nacrtu):
- preuzimanja: instaleri .exe, .dmg i .apk (uključuju i automatska ažuriranja);
- aktivne instalacije: koliko puta je preuzet mali opis izdanja pri dnevnoj provjeri ažuriranja
  (android.json na Androidu; release.json na računaru od 0.9.9, release-macos.json na Macu).
Svako pokretanje upiše snimak u `<Build>/statistika/istorija.json` (van repoa, samo na ovom računaru), pa se iz
razlike dva dana vidi koliko se instalacija javilo tog dana. Stranica je `<Build>/statistika/index.html`.
"""

import argparse
import datetime as dt
import html
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT.parent / "Build" / "statistika"
REPOS = ("abnps/video-download", "abnps/video-download-installers")
# Fajl → vrsta brojača
CHECKS = {"android.json": "android", "release.json": "windows", "release-macos.json": "mac"}


def releases(repo: str) -> list[dict]:
    raw = subprocess.run(["gh", "api", f"repos/{repo}/releases?per_page=100", "--paginate", "--jq", ".[]"],
                         check=True, capture_output=True, text=True, encoding="utf-8").stdout
    return [json.loads(line) for line in raw.splitlines() if line.strip()]  # jedno izdanje po redu


def snapshot() -> dict:
    downloads = {"windows": 0, "mac": 0, "android": 0}
    checks = {"windows": 0, "mac": 0, "android": 0}
    per_release = []
    for repo in REPOS:
        for release in releases(repo):
            row = {"repo": repo, "tag": release.get("tag_name"), "draft": release.get("draft"),
                   "published": release.get("published_at") or release.get("created_at"),
                   "windows": 0, "mac": 0, "android": 0}
            for asset in release.get("assets", []):
                name, count = asset.get("name", ""), int(asset.get("download_count") or 0)
                kind = ("windows" if name.endswith(".exe") else "mac" if name.endswith(".dmg")
                        else "android" if name.endswith(".apk") else None)
                if kind:
                    downloads[kind] += count
                    row[kind] += count
                if repo == REPOS[0] and name in CHECKS:
                    checks[CHECKS[name]] += count
            per_release.append(row)
    return {"time": dt.datetime.now().isoformat(timespec="minutes"), "downloads": downloads, "checks": checks,
            "releases": per_release}


def load_history(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def per_day(history: list[dict]) -> list[tuple[str, dict]]:
    """Posljednji snimak svakog dana, pa razlika prema prethodnom danu = javljanja tog dana."""
    last = {}
    for snap in history:
        last[snap["time"][:10]] = snap
    days = sorted(last)
    rows = []
    for previous, day in zip(days, days[1:]):
        a, b = last[previous]["checks"], last[day]["checks"]
        # Novo izdanje ima nov android.json s brojem od nule: negativna razlika znači „nepoznato", ne minus.
        rows.append((day, {k: (b[k] - a[k]) if b[k] >= a[k] else None for k in b}))
    return rows


def render(snap: dict, days: list[tuple[str, dict]]) -> str:
    d, c = snap["downloads"], snap["checks"]
    esc = html.escape
    day_rows = "".join(
        f"<tr><td>{esc(day)}</td>" + "".join(f"<td>{'—' if v[k] is None else v[k]}</td>" for k in ("windows", "mac", "android"))
        + "</tr>" for day, v in reversed(days[-30:])) or (
        '<tr><td colspan="4" class="muted">Pokreni skriptu i sutra: dnevni broj je razlika dva dana.</td></tr>')
    rel_rows = "".join(
        f"<tr><td>{esc(r['tag'] or '')}{' <span class=muted>(nacrt)</span>' if r['draft'] else ''}"
        f"{' <span class=muted>winget</span>' if r['repo'] != REPOS[0] else ''}</td>"
        f"<td>{esc((r['published'] or '')[:10])}</td><td>{r['windows']}</td><td>{r['mac']}</td><td>{r['android']}</td></tr>"
        for r in snap["releases"])
    return f"""<!doctype html><html lang="bs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Video Download statistika</title>
<style>
:root {{ --bg:#f6f7fb; --card:#fff; --fg:#1d2230; --muted:#6b7385; --line:#e3e6ef; --accent:#5b4ce6; color-scheme:light }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#14161d; --card:#1d2029; --fg:#e8eaf0; --muted:#9aa1b2;
  --line:#2c303c; --accent:#a294ff; color-scheme:dark }} }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 "Segoe UI",system-ui,sans-serif }}
main {{ max-width:900px; margin:0 auto; padding:28px 16px 48px; display:grid; gap:20px }}
h1 {{ margin:0; font-size:26px }} h2 {{ margin:0 0 10px; font-size:17px }}
.muted {{ color:var(--muted) }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px }}
.tile, section {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px }}
.tile b {{ display:block; font-size:28px; color:var(--accent); font-variant-numeric:tabular-nums }}
.scroll {{ overflow-x:auto }}
table {{ width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); white-space:nowrap }}
th {{ color:var(--muted); font-weight:600; font-size:13px }}
</style></head><body><main>
<div><h1>Video Download statistika</h1><p class="muted">Osvježeno {esc(snap['time'].replace('T', ' '))} ·
podaci s GitHub-a, bez praćenja korisnika · <code>python tools/statistika.py</code></p></div>
<div class="tiles">
<div class="tile"><span class="muted">Preuzimanja ukupno</span><b>{sum(d.values())}</b></div>
<div class="tile"><span class="muted">Windows</span><b>{d['windows']}</b></div>
<div class="tile"><span class="muted">Mac</span><b>{d['mac']}</b></div>
<div class="tile"><span class="muted">Android</span><b>{d['android']}</b></div>
</div>
<section><h2>Aktivne instalacije (javljanja pri dnevnoj provjeri)</h2>
<p class="muted">Jedna instalacija se javi najviše jednom dnevno, pa je broj za jedan dan ≈ broj aktivnih korisnika tog dana.
Računar se broji od verzije 0.9.9. Ukupno javljanja za posljednje izdanje: Windows {c['windows']}, Mac {c['mac']},
Android {c['android']}.</p>
<div class="scroll"><table><tr><th>Dan</th><th>Windows</th><th>Mac</th><th>Android</th></tr>{day_rows}</table></div>
</section>
<section><h2>Preuzimanja po izdanju</h2><p class="muted">Uključuju i automatska ažuriranja i probna preuzimanja.</p>
<div class="scroll"><table><tr><th>Izdanje</th><th>Datum</th><th>Windows</th><th>Mac</th><th>Android</th></tr>{rel_rows}</table></div>
</section></main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-open", action="store_true", help="ne otvaraj stranicu u browseru")
    parser.add_argument("--history", type=Path, help="istorija na drugom mjestu (GitHub: grana statistika)")
    parser.add_argument("--no-page", action="store_true", help="samo dopuni istoriju, bez lokalne stranice")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    snap = snapshot()
    history_path = args.history or OUT / "istorija.json"
    history = load_history(history_path) + [{k: snap[k] for k in ("time", "downloads", "checks")}]
    history_path.write_text(json.dumps(history[-2000:], indent=1), encoding="utf-8")
    d = snap["downloads"]
    print(f"Preuzimanja: {sum(d.values())} (Windows {d['windows']}, Mac {d['mac']}, Android {d['android']})")
    if args.no_page:
        return 0
    page = OUT / "index.html"
    page.write_text(render(snap, per_day(history)), encoding="utf-8")
    print(f"Stranica: {page}")
    if not args.no_open and os.name == "nt":
        os.startfile(page)  # noqa: S606 - lokalni fajl autora
    return 0


if __name__ == "__main__":
    sys.exit(main())
