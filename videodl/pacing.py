"""Zaštita od blokade (Ahmed 2.11.2026): blagi razmaci između preuzimanja s istog strogog sajta, kratak predah
poslije mnogo preuzimanja zaredom i čekanje kad sajt ipak blokira (bez Qt-a; prozor samo pita i prikazuje).

Sajtovi poput YouTubea privremeno blokiraju (HTTP 429, „potvrdi da nisi bot") kad se s jedne adrese skine mnogo
videa zaredom. Razmak se drži u rasporedu (rok kao kod ponovnog pokušaja), ne spavanjem u niti, pa ostali sajtovi
za to vrijeme idu normalno. Pauza nikad ne zavisi od priloga: ista je za sve.
"""

import random
import re
import time
from dataclasses import dataclass

from .achievements import site_of

# Adresa (sajt bez poddomene) → porodica; ostali sajtovi i direktni tokovi iz dodatka idu bez usporavanja.
FAMILIES = {
    "youtube.com": "youtube", "youtu.be": "youtube", "youtube-nocookie.com": "youtube",
    "instagram.com": "instagram", "tiktok.com": "tiktok",
    "facebook.com": "facebook", "fb.watch": "facebook",
    "x.com": "x", "twitter.com": "x",
}
NAMES = {"youtube": "YouTube", "instagram": "Instagram", "tiktok": "TikTok", "facebook": "Facebook", "x": "X"}
SLOW_FAMILIES = {"instagram", "tiktok"}  # blokiraju brže: sva trajanja ×1,5
SLOW_FACTOR = 1.5

IDLE_RESET = 15 * 60  # brojač zaredom se vraća na nulu poslije toliko bez preuzimanja s te porodice
THRESHOLDS = (10, 25, 50)  # od kojeg preuzimanja zaredom kreću razmaci 1., 2. i 3. nivoa
LEARNED_THRESHOLDS = (5, 13, 25)  # poslije blokade u zadnjih 7 dana: ranije
GAPS = ((2.0, 5.0), (5.0, 10.0), (8.0, 15.0))  # razmak po nivou (sekunde, nasumično u rasponu)
BREAK = (30.0, 60.0)  # predah poslije svakih THRESHOLDS[1] zaredom (kartica)
PARALLEL_CAP = 2  # od prvog nivoa najviše toliko istovremeno s iste porodice
LEARN_SECONDS = 7 * 24 * 60 * 60
LEARNED_FACTOR = 1.5
BLOCK_WAITS = (5 * 60, 10 * 60, 15 * 60)  # čekanje kad sajt blokira istu stavku 1., 2. i 3. put; 4. put = greška

# Iste greške kao „rate" i „bot" u widgets._FRIENDLY_ERRORS: sajt traži pauzu.
_BLOCK = re.compile(r"HTTP Error 429|too many requests|confirm you.?re not a bot|not a robot", re.I)


def family_of(url: str) -> str | None:
    return FAMILIES.get(site_of(url or ""))


# Plejlista, kanal ili profil (ne jedan video): čitanje spiska šalje mnogo zahtjeva zaredom.
_COLLECTION = re.compile(r"[?&]list=|/playlist|/@|/channel/|/c/|/user/|/videos(?:[/?#]|$)|/shorts/?$"
                         r"|instagram\.com/[^/]+/?$|tiktok\.com/@", re.I)


def request_sleep(url: str, enabled: bool = True) -> float:
    """Razmak između zahtjeva (yt-dlp sleep_interval_requests) pri čitanju plejliste ili kanala sa strogog sajta.
    Jedan video se čita bez razmaka, da „Zalijepi" ostane brz."""
    return 0.5 if enabled and family_of(url) and _COLLECTION.search(url or "") else 0.0


def is_block_error(message: str) -> bool:
    return bool(_BLOCK.search(message or ""))


@dataclass(frozen=True)
class Pause:
    family: str
    kind: str  # "gap" (statusna traka), "break" i "block" (kartica)
    seconds: float

    @property
    def card(self) -> bool:
        return self.kind != "gap"


@dataclass
class _State:
    streak: int = 0  # preuzimanja pokrenuta zaredom
    breaks: int = 0  # koliko je predaha već bilo u ovom nizu
    last_seen: float | None = None
    ready_at: float = 0.0  # monotono: ništa s ove porodice ne kreće prije
    kind: str = ""  # vrsta pauze koja važi do ready_at ("gap", "break" ili "block")
    seconds: float = 0.0  # njeno puno trajanje (za poruku)


class Pacer:
    def __init__(self, rng: random.Random | None = None, clock=time.monotonic, wall=time.time):
        self.enabled = True  # Postavke → „Zaštita od blokade"; čekanje na stvarnu blokadu radi i bez toga
        self.learned_until = 0.0  # unix vrijeme do kad važe strožiji pragovi (pamti se u podešavanjima)
        self._rng = rng or random.Random()
        self._clock = clock
        self._wall = wall
        self._states: dict[str, _State] = {}

    def _state(self, family: str) -> _State:
        return self._states.setdefault(family, _State())

    def learned(self) -> bool:
        return self._wall() < self.learned_until

    def thresholds(self) -> tuple[int, int, int]:
        return LEARNED_THRESHOLDS if self.learned() else THRESHOLDS

    def _scale(self, family: str) -> float:
        return (LEARNED_FACTOR if self.learned() else 1.0) * (SLOW_FACTOR if family in SLOW_FAMILIES else 1.0)

    # ---------- pitanja rasporeda ----------

    def remaining(self, family: str | None) -> float:
        """Sekundi do kad smije krenuti sljedeće preuzimanje s porodice (0 = odmah)."""
        if family is None or family not in self._states:
            return 0.0
        return max(0.0, self._states[family].ready_at - self._clock())

    def pending(self, family: str | None) -> Pause | None:
        """Pauza koja trenutno drži porodicu (vrsta i puno trajanje); None = ništa ne čeka."""
        if self.remaining(family) <= 0:
            return None
        state = self._states[family]
        return Pause(family, state.kind or "gap", state.seconds)

    def deadline(self, family: str | None) -> float:
        """Monotoni trenutak do kad porodica čeka (0 = ne čeka); razlikuje jednu pauzu od sljedeće."""
        return self._states[family].ready_at if family in self._states else 0.0

    def parallel_cap(self, family: str | None) -> int | None:
        """Najviše istovremenih preuzimanja s porodice; None = bez ograničenja."""
        if not self.enabled or family is None:
            return None
        return PARALLEL_CAP if self._fresh_streak(family) >= self.thresholds()[0] else None

    def _fresh_streak(self, family: str) -> int:
        state = self._states.get(family)
        if state is None or state.last_seen is None or self._clock() - state.last_seen > IDLE_RESET:
            return 0
        return state.streak

    # ---------- događaji ----------

    def started(self, family: str | None) -> None:
        if family is None:
            return
        state = self._state(family)
        if self._fresh_streak(family) == 0:
            state.streak = state.breaks = 0  # 15 min mira (ili prvi put): novi niz
        state.streak += 1
        state.last_seen = self._clock()

    def finished(self, family: str | None) -> Pause | None:
        """Preuzimanje s porodice je završilo: razmak (ili predah) prije sljedećeg; None = bez čekanja."""
        if family is None or family not in self._states:
            return None
        state = self._states[family]
        now = self._clock()
        state.last_seen = now
        if not self.enabled:
            return None
        first, second, third = self.thresholds()
        scale = self._scale(family)
        if state.streak // second > state.breaks:
            state.breaks = state.streak // second
            pause = Pause(family, "break", round(self._rng.uniform(*BREAK) * scale))
        else:
            following = state.streak + 1
            level = 2 if following >= third else 1 if following >= second else 0 if following >= first else None
            if level is None:
                return None
            pause = Pause(family, "gap", round(self._rng.uniform(*GAPS[level]) * scale, 1))
        self._hold(state, now, pause)
        return pause

    @staticmethod
    def _hold(state: _State, now: float, pause: Pause) -> None:
        """Pauza važi samo ako produžava čekanje (kraća ne skraćuje dužu koja već teče, npr. blokadu)."""
        if now + pause.seconds >= state.ready_at:
            state.ready_at, state.kind, state.seconds = now + pause.seconds, pause.kind, pause.seconds

    def blocked(self, family: str, attempt: int) -> Pause | None:
        """Sajt je blokirao stavku `attempt`-ti put (1, 2, 3…): čeka se, pa nastavlja; None = odustati (greška).
        Radi i kad je zaštita isključena: bez čekanja bi preuzimanje samo palo."""
        self.learned_until = self._wall() + LEARN_SECONDS
        if attempt < 1 or attempt > len(BLOCK_WAITS):
            return None
        state = self._state(family)
        now = self._clock()
        state.last_seen = now
        pause = Pause(family, "block", float(BLOCK_WAITS[attempt - 1]))
        self._hold(state, now, pause)
        return pause

    def drop_soft(self) -> None:
        """Zaštita je isključena: razmaci i predasi prestaju odmah; čekanje poslije stvarne blokade ostaje."""
        for state in self._states.values():
            if state.kind != "block":
                state.ready_at = 0.0

    def skip(self, family: str | None = None) -> None:
        """„Nastavi odmah" (jedna porodica) ili „Zaustavi" (sve): čekanje prestaje."""
        for name, state in self._states.items():
            if family is None or name == family:
                state.ready_at = 0.0
