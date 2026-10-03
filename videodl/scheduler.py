"""Raspored preuzimanja bez Qt-a (plan 1.0, tačka 11; izdvojeno iz gui.py bez promjene ponašanja, 3.10.2026).

Dvije odluke koje su ranije bile u prozoru:
- `output_key`: šta određuje ime izlaznog fajla (isti ključ = isti fajl, pa dva takva posla ne rade zajedno);
- `pick_next`: koja stavka sljedeća kreće (prvo ručno pokrenute, pa redom kad je „Preuzmi sve" u toku).
Prozor (gui.py) samo pokreće izabrano i prikazuje stanje; ovdje se sve može testirati bez prozora.
"""

import os
from collections.abc import Callable, Iterable

from .jobs import ItemStatus, QueueItem
from .presets import DEFAULT_NAME_TEMPLATE, direct_output_name, safe_folder_name, section_label, title_identity


def needs_adult_ok(item) -> bool:
    """18+ bez potvrde za OVO preuzimanje: čeka (ostali idu)."""
    return item.adult and not item.adult_ok


def output_key(item: QueueItem, name_template: str) -> tuple:
    """Šta određuje ime izlaznog fajla, po ISTIM pravilima kao samo ime (presets): folder, format (kvalitet je
    u imenu), isječak i identitet videa. Isti ključ = isti fajl, pa dva takva posla ne rade istovremeno.
    Kad nije sigurno, ključ je radije isti (drugi posao samo sačeka) nego različit (dva pisanja u isti fajl)."""
    subfolder = safe_folder_name(item.subfolder) if item.subfolder else ""
    folder = os.path.normcase(os.path.normpath(os.path.join(item.output_dir, subfolder)))
    if item.filename_title:
        # direktan tok: ime je naslov stranice + otisak toka (parametri koji određuju video su u otisku)
        identity = ("stream", direct_output_name(item.filename_title, item.url).casefold())
    elif item.force_id_name or name_template == DEFAULT_NAME_TEMPLATE:
        # „naslov [id]": dva linka istog videa (npr. kratka i duga adresa) daju isti ID, pa i isto ime
        identity = ("id", item.video_id or item.url)
    else:
        # šablon bez ID-a: ime daje naslov, skraćen kao u imenu fajla (dugi naslovi istog početka = isto ime)
        identity = ("title", title_identity(item.title or item.url))
    return folder, item.preset_key, section_label(item.section), identity


def pick_next(manual: list[int], items: Iterable[QueueItem], get: Callable[[int], QueueItem | None],
              active: Iterable[QueueItem], name_template: str, auto: bool,
              retry_pending: Callable[[QueueItem], bool]) -> tuple[QueueItem | None, list[int]]:
    """Sljedeća stavka za preuzimanje i novi spisak ručno pokrenutih.

    Ručno pokrenute (`manual`, redom) imaju prednost; ona koja bi pisala isti fajl kao posao u toku se odlaže
    (ostaje na početku spiska), a nevažeće (nema je, ne čeka, 18+ bez potvrde, rok za novi pokušaj) se izbacuju.
    Kad ručnih nema, uz `auto` („Preuzmi sve") kreće prva stavka reda koja čeka i nije zauzeta. None = ništa."""
    busy = {output_key(item, name_template) for item in active}

    def free(item: QueueItem) -> bool:
        return output_key(item, name_template) not in busy

    remaining = list(manual)
    postponed = []
    while remaining:
        candidate = get(remaining.pop(0))
        if candidate is None or candidate.status != ItemStatus.WAITING or needs_adult_ok(candidate) \
                or retry_pending(candidate):
            continue
        if not free(candidate):
            postponed.append(candidate.id)  # čeka da isti posao završi, pa kreće
            continue
        return candidate, postponed + remaining
    if auto:
        for candidate in items:
            if candidate.status == ItemStatus.WAITING and free(candidate) and not needs_adult_ok(candidate) \
                    and not retry_pending(candidate):
                return candidate, postponed
    return None, postponed
