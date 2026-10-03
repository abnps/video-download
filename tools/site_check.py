"""Svakodnevna provjera sajtova (plan za 1.0, tačka 4): da li najnoviji yt-dlp još čita po jedan javni video.

    python tools/site_check.py          → tabela u konzoli (i u GitHub sažetku), izlaz 1 ako je nešto POKVARENO

Program sam preuzima najnoviji yt-dlp sa PyPI-ja (videodl/ytdlp_update.py), pa se provjerava baš ta verzija.
GitHubovi serveri su u data centrima i sajtovi ih često blokiraju („nisi robot", prijava, 403): to je samo
UPOZORENJE. Pada samo kad sajt promijeni stranicu pa je yt-dlp više ne razumije — tada stiže e-pošta.
Ništa se ne preuzima (samo čitanje podataka o videu).
"""

import os
import re
import sys

# Javni, dugo dostupni videi (provjereni 3.10.2026; dio iz yt-dlp-ovih testova).
SITES = (
    ("YouTube", "https://www.youtube.com/watch?v=jNQXAC9IVRw"),
    ("TikTok", "https://www.tiktok.com/@patroxofficial/video/6742501081818877190"),
    ("Instagram", "https://www.instagram.com/reel/Chunk8-jurw/"),
    ("X", "https://twitter.com/oshtru/status/1577855540407197696"),
    ("Dailymotion", "https://www.dailymotion.com/video/x5kesuj"),
)

# Sajt nije pokvaren nego je odbio server s kog se provjerava (data centar, prijava, zemlja).
_BLOCKED = re.compile(
    r"not a bot|sign in|log ?in|logged-in|cookies|ip address is blocked|your ip|http error (403|429)|"
    r"too many requests|rate.?limit|geo|country|empty media response|unavailable in your",
    re.IGNORECASE)


def classify(error: str) -> str:
    """'blokirano' (upozorenje) ili 'pokvareno' (prava greška yt-dlp-a ili promjena sajta)."""
    return "blokirano" if _BLOCKED.search(error or "") else "pokvareno"


def check(url: str) -> tuple[str, str]:
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as error:  # yt-dlp javlja sve kao izuzetak; tekst odlučuje o vrsti
        message = str(error).splitlines()[-1] if str(error) else type(error).__name__
        return classify(message), message[:200]
    formats = info.get("formats") or ([info] if info.get("url") else [])
    if not formats:
        return "pokvareno", "nema nijednog formata"
    return "radi", f"{len(formats)} formata · {(info.get('title') or '')[:50]}"


def main() -> int:
    import yt_dlp

    sys.stdout.reconfigure(errors="replace")  # Windows konzola nema emoji

    rows = [(site, *check(url)) for site, url in SITES]
    lines = [f"## Provjera sajtova · yt-dlp {yt_dlp.version.__version__}", "",
             "| Sajt | Stanje | Detalj |", "|---|---|---|"]
    icons = {"radi": "✅ radi", "blokirano": "⚠️ blokiran server", "pokvareno": "❌ pokvareno"}
    for site, state, detail in rows:
        lines.append(f"| {site} | {icons[state]} | {detail.replace('|', '/')} |")
    report = "\n".join(lines) + "\n"
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(report)
    return 1 if any(state == "pokvareno" for _, state, _ in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
