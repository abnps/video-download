"""Mjesečni i godišnji pregled (Ahmed 2.11.2026): „Tvoj oktobar u Video Downloadu" (bez Qt-a).

Bilježe se samo brojke po mjesecu (broj, veličina, trajanje, sajtovi, dani u sedmici); naslovi i linkovi se ne pamte
i ništa se ne šalje. Prikazuje se prvog pokretanja u novom mjesecu (u januaru godišnji umjesto decembarskog).
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime

from .achievements import site_of

MIN_DOWNLOADS = 10  # pregled samo za mjesec/godinu s bar toliko preuzimanja
KEEP_MONTHS = 14  # januarski godišnji pregled treba cijelu prošlu godinu


def _empty() -> dict:
    return {"count": 0, "bytes": 0, "seconds": 0.0, "longest": 0.0, "sites": {}, "weekdays": [0] * 7}


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def previous_month(day: date) -> date:
    return date(day.year - 1, 12, 1) if day.month == 1 else date(day.year, day.month - 1, 1)


@dataclass(frozen=True)
class Summary:
    period: str  # "2026-10" (mjesec) ili "2026" (godina)
    yearly: bool
    count: int
    bytes: int
    seconds: float
    longest: float
    top_site: str
    busiest_weekday: int  # 0 = ponedjeljak


@dataclass
class RecapState:
    months: dict = field(default_factory=dict)  # "2026-10" -> brojke
    last_shown: str = ""  # period zadnjeg prikazanog pregleda
    day: str = ""  # današnji dan (za „Danas si preuzeo…" na kartici pauze)
    day_count: int = 0
    day_bytes: int = 0

    # ---------- čuvanje ----------

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str | None) -> "RecapState":
        try:
            data = json.loads(text or "{}")
        except (TypeError, ValueError):
            data = {}
        state = cls()
        if not isinstance(data, dict):
            return state
        # Oštećeno polje = početna vrijednost; ostala polja se čuvaju.
        for key in ("last_shown", "day"):
            if isinstance(data.get(key), str):
                setattr(state, key, data[key])
        for key in ("day_count", "day_bytes"):
            if type(data.get(key)) is int and data[key] >= 0:
                setattr(state, key, data[key])
        months = data.get("months")
        if isinstance(months, dict):
            for key, value in months.items():
                clean = _clean_month(value)
                if isinstance(key, str) and len(key) == 7 and clean is not None:
                    state.months[key] = clean
        return state

    # ---------- bilježenje ----------

    def record(self, url: str, size: int, duration: float | None, when: datetime | None = None) -> None:
        when = when or datetime.now()
        month = self.months.setdefault(month_key(when.date()), _empty())
        month["count"] += 1
        month["bytes"] += max(0, int(size or 0))
        seconds = float(duration) if duration and duration > 0 else 0.0
        month["seconds"] += seconds
        month["longest"] = max(month["longest"], seconds)
        site = site_of(url)
        if site:
            month["sites"][site] = month["sites"].get(site, 0) + 1
        month["weekdays"][when.weekday()] += 1
        today = when.date().isoformat()
        if self.day != today:
            self.day, self.day_count, self.day_bytes = today, 0, 0
        self.day_count += 1
        self.day_bytes += max(0, int(size or 0))
        for old in sorted(self.months)[:-KEEP_MONTHS]:
            del self.months[old]

    def today(self, day: date) -> tuple[int, int]:
        """(broj, bajtovi) preuzetih danas."""
        return (self.day_count, self.day_bytes) if self.day == day.isoformat() else (0, 0)

    # ---------- prikaz ----------

    def due(self, today: date) -> Summary | None:
        """Pregled koji treba pokazati danas (jednom po periodu); None = ništa."""
        if today.month == 1:
            year = str(today.year - 1)
            summary = self.summary(year)
            return summary if summary and self.last_shown != year else None
        key = month_key(previous_month(today))
        summary = self.summary(key)
        return summary if summary and self.last_shown != key else None

    def summary(self, period: str) -> Summary | None:
        yearly = len(period) == 4
        parts = [value for key, value in self.months.items() if key[:4] == period] if yearly \
            else [self.months[period]] if period in self.months else []
        total = _empty()
        for month in parts:
            total["count"] += month["count"]
            total["bytes"] += month["bytes"]
            total["seconds"] += month["seconds"]
            total["longest"] = max(total["longest"], month["longest"])
            for site, count in month["sites"].items():
                total["sites"][site] = total["sites"].get(site, 0) + count
            total["weekdays"] = [a + b for a, b in zip(total["weekdays"], month["weekdays"])]
        if total["count"] < MIN_DOWNLOADS:
            return None
        top_site = max(sorted(total["sites"]), key=lambda site: total["sites"][site], default="")
        busiest = max(range(7), key=lambda day: (total["weekdays"][day], -day))
        return Summary(period, yearly, total["count"], total["bytes"], total["seconds"], total["longest"],
                       top_site, busiest)

    def shown(self, period: str) -> None:
        self.last_shown = period


def _clean_month(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    month = _empty()
    for key in ("count", "bytes"):
        if type(value.get(key)) is int and value[key] >= 0:
            month[key] = value[key]
    for key in ("seconds", "longest"):
        if type(value.get(key)) in (int, float) and 0 <= value[key] < 1e12:
            month[key] = float(value[key])
    sites = value.get("sites")
    if isinstance(sites, dict):
        month["sites"] = {k: v for k, v in sites.items() if isinstance(k, str) and type(v) is int and v > 0}
    weekdays = value.get("weekdays")
    if isinstance(weekdays, list) and len(weekdays) == 7 and all(type(n) is int and n >= 0 for n in weekdays):
        month["weekdays"] = list(weekdays)
    return month
