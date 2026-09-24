"""„Podrži projekat": dobrovoljni prilog preko PayPal-a i pošten podsjetnik (bez Qt-a).

Pravila, da prilog ostane dobrovoljan (a ne kupovina):
- prilog ništa ne otključava; program je isti za sve;
- podsjetnik ništa ne blokira i nema odbrojavanja ni lažne hitnosti;
- „Već sam podržao" može kliknuti svako, bez provjere uplate.
"""

from dataclasses import dataclass

SUPPORT_URL = "https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ"
BANNER_EVERY = 10  # traka iznad liste poslije svakih N novih preuzimanja
DIALOG_INTERVAL = 7 * 24 * 60 * 60  # prozor najviše jednom sedmično
SNOOZE = 90 * 24 * 60 * 60  # „Već sam podržao" gasi podsjetnik na 90 dana


@dataclass
class SupportState:
    downloads: int = 0  # novih preuzimanja ukupno (ne računaju se fajlovi koji su već postojali)
    banner_next: int = BANNER_EVERY
    last_dialog: float = 0.0
    snooze_until: float = 0.0

    def snoozed(self, now: float) -> bool:
        return now < self.snooze_until

    def count_download(self) -> None:
        self.downloads += 1

    def should_show_banner(self, now: float) -> bool:
        return not self.snoozed(now) and self.downloads >= self.banner_next

    def banner_later(self) -> None:
        """„Kasnije": traka se vraća tek poslije sljedećih N preuzimanja."""
        self.banner_next = self.downloads + BANNER_EVERY

    def should_show_dialog(self, now: float, busy: bool) -> bool:
        """Prozor samo kad ništa ne radi, poslije bar jednog preuzimanja, najviše jednom sedmično."""
        if busy or self.snoozed(now) or self.downloads == 0:
            return False
        if self.last_dialog == 0.0:
            # Prvi put tek poslije nekoliko preuzimanja, ne odmah nakon prvog videa.
            return self.downloads >= BANNER_EVERY // 2
        return now - self.last_dialog >= DIALOG_INTERVAL

    def dialog_shown(self, now: float) -> None:
        self.last_dialog = now

    def already_supported(self, now: float) -> None:
        self.snooze_until = now + SNOOZE
        self.banner_next = self.downloads + BANNER_EVERY
