"""Dostignuća (Ahmed 19.10.2026): male čestitke za način korištenja programa (bez Qt-a).

Sve se računa i čuva samo na ovom računaru (podešavanja programa); ništa se ne šalje.
Brojač preuzimanja i čestitke na 10, 50, 100… su u `support.py`; ovdje su ostala dostignuća.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

GB = 1024 ** 3
DAY = 24 * 60 * 60

# (ključ, ikona) redom kojim se prikazuju u „Moja dostignuća"; nazivi i opisi su u i18n („badge.<ključ>").
BADGES = (
    ("audio", "🎵"), ("playlist", "📚"), ("clip", "✂️"), ("uhd", "🔭"), ("browser", "🧩"), ("car", "🚗"),
    ("subtitles", "💬"), ("marathon", "🎬"), ("parallel", "⚡"), ("comeback", "🔁"), ("night", "🦉"),
    ("sites5", "🌍"), ("sites25", "🗺️"), ("gb1", "💾"), ("gb10", "💽"), ("gb100", "🗄️"),
    ("streak7", "📅"), ("anniversary", "🎂"),
)
ICONS = dict(BADGES)
PLAYLIST_MIN = 10  # „Kolekcionar": cijela lista od bar toliko videa
PARALLEL_MIN = 4  # „Multitasker": toliko preuzimanja istovremeno
MARATHON_SECONDS = 2 * 60 * 60
SUPPORT_NOTE_EVERY = DAY  # poruka za prilog u čestitki najviše jednom dnevno (više dostignuća prvog dana)


@dataclass
class Download:
    """Jedno novo, uspješno preuzimanje: samo ono što dostignuća trebaju."""
    url: str = ""
    audio: bool = False
    car: bool = False
    clip: bool = False
    height: int | None = None
    size: int = 0
    from_browser: bool = False
    subtitles: bool = False
    duration: float | None = None
    retried: bool = False
    running_together: int = 1  # koliko je preuzimanja radilo istovremeno (s ovim)
    when: datetime = field(default_factory=datetime.now)


# Česti drugi nivoi ispod države (bbc.co.uk, abc.com.au): sajt su tada zadnja tri dijela adrese.
SECOND_LEVEL = {"co", "com", "org", "net", "gov", "edu", "ac", "or", "ne", "go", "gob", "nic"}


def site_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


@dataclass
class AchievementState:
    earned: dict = field(default_factory=dict)  # ključ -> vrijeme osvajanja (unix)
    pending: list = field(default_factory=list)  # osvojena, a još nečestitana
    total_bytes: int = 0
    sites: list = field(default_factory=list)
    first_day: str = ""  # ISO datum prvog preuzimanja otkad postoje dostignuća
    last_day: str = ""
    streak: int = 0
    best_streak: int = 0
    last_support_note: float = 0.0

    # ---------- čuvanje (JSON u podešavanjima) ----------

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str | None) -> "AchievementState":
        try:
            data = json.loads(text or "{}")
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        # Pokvarena ili tuđa vrijednost u podešavanjima ne smije spriječiti pokretanje: loše polje = početno.
        state = cls()
        for key, value in data.items():
            default = getattr(state, key, None)
            if key in cls.__dataclass_fields__ and type(value) is type(default):
                setattr(state, key, value)
            elif key in cls.__dataclass_fields__ and isinstance(default, float) and isinstance(value, int):
                setattr(state, key, float(value))
        state.earned = {k: v for k, v in state.earned.items() if isinstance(v, (int, float))}
        state.pending = [k for k in state.pending if k in ICONS]
        state.sites = [s for s in state.sites if isinstance(s, str)]
        try:
            date.fromisoformat(state.first_day or "2000-01-01")
            date.fromisoformat(state.last_day or "2000-01-01")
        except ValueError:
            state.first_day = state.last_day = ""
        return state

    # ---------- osvajanje ----------

    def _earn(self, key: str, now: float) -> None:
        if key not in self.earned:
            self.earned[key] = now
            self.pending.append(key)

    def record(self, download: Download, now: float | None = None) -> None:
        now = time.time() if now is None else now
        earn = lambda key: self._earn(key, now)  # noqa: E731
        if download.audio:
            earn("audio")
        if download.clip:
            earn("clip")
        if download.height and download.height >= 2160:
            earn("uhd")
        if download.from_browser:
            earn("browser")
        if download.car:
            earn("car")
        if download.subtitles and not download.audio:
            earn("subtitles")
        if download.duration and download.duration >= MARATHON_SECONDS:
            earn("marathon")
        if download.running_together >= PARALLEL_MIN:
            earn("parallel")
        if download.retried:
            earn("comeback")
        if 0 <= download.when.hour < 4:
            earn("night")
        site = site_of(download.url)
        if site and site not in self.sites:
            self.sites.append(site)
        for count, key in ((5, "sites5"), (25, "sites25")):
            if len(self.sites) >= count:
                earn(key)
        self.total_bytes += max(0, download.size)
        for size, key in ((1, "gb1"), (10, "gb10"), (100, "gb100")):
            if self.total_bytes >= size * GB:
                earn(key)
        self._count_day(download.when.date(), earn)

    def _count_day(self, today: date, earn) -> None:
        day = today.isoformat()
        if not self.first_day:
            self.first_day = day
        if self.last_day != day:
            yesterday = (today - timedelta(days=1)).isoformat()
            self.streak = self.streak + 1 if self.last_day == yesterday else 1
            self.last_day = day
            self.best_streak = max(self.best_streak, self.streak)
        if self.streak >= 7:
            earn("streak7")
        if (today - date.fromisoformat(self.first_day)).days >= 365:
            earn("anniversary")

    def record_playlist(self, done_in_playlist: int, total: int | None = None, now: float | None = None) -> None:
        """Cijela lista: sve njene stavke uspjele (lista s neuspjelom stavkom se ne računa)."""
        if done_in_playlist >= PLAYLIST_MIN and (total is None or done_in_playlist >= total):
            self._earn("playlist", time.time() if now is None else now)

    # ---------- čestitka ----------

    def take_pending(self) -> list:
        """Dostignuća za čestitku (i briše ih s liste)."""
        pending, self.pending = self.pending, []
        return pending

    def support_note_allowed(self, now: float) -> bool:
        """Poruka za prilog u čestitki najviše jednom dnevno (prvi dan zna donijeti više dostignuća)."""
        if now - self.last_support_note < SUPPORT_NOTE_EVERY:
            return False
        self.last_support_note = now
        return True
