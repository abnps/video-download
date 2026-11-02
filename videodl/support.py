"""„Podrži projekat": dobrovoljni prilog preko PayPal-a i pošten podsjetnik (bez Qt-a).

Pravila, da prilog ostane dobrovoljan (a ne kupovina):
- prilog ništa ne otključava; program je isti za sve;
- podsjetnik ništa ne blokira i nema odbrojavanja ni lažne hitnosti;
- „Već sam podržao" može kliknuti svako, bez provjere uplate.
Odbrojavanje na kartici pauze (pacing.py) pripada zaštiti od blokade, ne prilogu: traje isto za sve.
"""

import json
from dataclasses import dataclass, field
from datetime import date

SUPPORT_URL = "https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ"
# Drugi kanal (Ahmed 3.10.2026): karticom i bez PayPal naloga; Ko-fi ne uzima proviziju na priloge.
KOFI_URL = "https://ko-fi.com/abnps"
# Direktno karticom, Apple Payem ili Google Payem (Stripe Payment Link, iznos bira podržavalac; samo Stripeova provizija).
STRIPE_URL = "https://buy.stripe.com/14A4gA9GnfcSgjVdAV8Vi00"
BANNER_EVERY = 10  # traka iznad liste poslije svakih N novih preuzimanja
DIALOG_INTERVAL = 7 * 24 * 60 * 60  # prozor najviše jednom sedmično
SNOOZE = 90 * 24 * 60 * 60  # „Već sam podržao" gasi podsjetnik na 90 dana
# Red o podršci na kartici pauze, poruci 50/50 i mjesečnom pregledu (Ahmed 2.11.2026): najviše jednom sedmično,
# a dvaput sedmično kad se program koristi često; nikad prije NOTE_MIN_DOWNLOADS preuzimanja.
NOTE_INTERVAL = DIALOG_INTERVAL
NOTE_INTERVAL_FREQUENT = DIALOG_INTERVAL / 2
NOTE_MIN_DOWNLOADS = 10
WEEK = 7 * 24 * 60 * 60
FREQUENT_DAYS = 3  # „često": preuzimanja u bar toliko različitih dana u zadnjih 7…
FREQUENT_DOWNLOADS = 30  # …ili bar toliko novih preuzimanja u zadnjih 7 dana
RECENT_MAX = 60  # pamti se vrijeme samo zadnjih N preuzimanja (za „često")
# Dostignuća (Ahmed 19.10.2026): čestitka na 10, 50, 100… novih preuzimanja; podsjetnik za prilog ostaje kakav je.
MILESTONES = (10, 50, 100, 250, 500, 1000, 2500, 5000, 10000)


def passed_milestone(downloads: int) -> int:
    """Najveće dostignuće do kojeg je broj već stigao (0 ako nijedno)."""
    return max((m for m in MILESTONES if m <= downloads), default=0)


@dataclass
class SupportState:
    downloads: int = 0  # novih preuzimanja ukupno (ne računaju se fajlovi koji su već postojali)
    banner_next: int = BANNER_EVERY
    last_dialog: float = 0.0
    snooze_until: float = 0.0
    milestone_shown: int = 0  # zadnje čestitano dostignuće
    last_note: float = 0.0  # zadnji red o podršci na kartici (pauza, 50/50, pregled)
    recent: list = field(default_factory=list)  # unix vremena zadnjih novih preuzimanja (samo za „često")

    def snoozed(self, now: float) -> bool:
        return now < self.snooze_until

    def count_download(self, now: float | None = None) -> None:
        self.downloads += 1
        if now is not None:
            self.recent = (self.recent + [now])[-RECENT_MAX:]

    def frequent(self, now: float) -> bool:
        """Program se koristi često: u zadnjih 7 dana preuzimanja u bar 3 dana ili bar 30 preuzimanja."""
        week = [when for when in self.recent if 0 <= now - when < WEEK]
        days = {date.fromtimestamp(when) for when in week}
        return len(days) >= FREQUENT_DAYS or len(week) >= FREQUENT_DOWNLOADS

    def _last_ask(self) -> float:
        return max(self.last_dialog, self.last_note)

    def note_allowed(self, now: float) -> bool:
        """Smije li kartica (pauza, 50/50, pregled) imati red o podršci; isti rok važi i za sedmični prozor."""
        if self.snoozed(now) or self.downloads < NOTE_MIN_DOWNLOADS:
            return False
        interval = NOTE_INTERVAL_FREQUENT if self.frequent(now) else NOTE_INTERVAL
        return now - self._last_ask() >= interval

    def note_shown(self, now: float) -> None:
        self.last_note = now

    def recent_json(self) -> str:
        return json.dumps(self.recent)

    @staticmethod
    def recent_from_json(text: str | None) -> list:
        try:
            data = json.loads(text or "[]")
        except (TypeError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        return [float(x) for x in data if type(x) in (int, float) and 0 < x < 1e11][-RECENT_MAX:]

    def should_show_banner(self, now: float) -> bool:
        return not self.snoozed(now) and self.downloads >= self.banner_next

    def banner_later(self) -> None:
        """„Kasnije": traka se vraća tek poslije sljedećih N preuzimanja."""
        self.banner_next = self.downloads + BANNER_EVERY

    def should_show_dialog(self, now: float, busy: bool) -> bool:
        """Prozor samo kad ništa ne radi, poslije bar jednog preuzimanja, najviše jednom sedmično."""
        if busy or self.snoozed(now) or self.downloads == 0:
            return False
        if self._last_ask() == 0.0:
            # Prvi put tek poslije nekoliko preuzimanja, ne odmah nakon prvog videa.
            return self.downloads >= BANNER_EVERY // 2
        # Red o podršci na kartici se računa kao poziv: prozor ne dolazi odmah poslije njega.
        return now - self._last_ask() >= DIALOG_INTERVAL

    def dialog_shown(self, now: float) -> None:
        self.last_dialog = now

    def already_supported(self, now: float) -> None:
        self.snooze_until = now + SNOOZE
        self.banner_next = self.downloads + BANNER_EVERY

    def milestone_due(self, busy: bool) -> int:
        """Dostignuće za čestitku, tek kad ništa ne radi (lista se ne prekida usred preuzimanja); 0 ako nema."""
        reached = passed_milestone(self.downloads)
        return reached if not busy and reached > self.milestone_shown else 0

    def milestone_seen(self, milestone: int) -> None:
        self.milestone_shown = max(self.milestone_shown, milestone)
