"""Red i istorija preuzimanja na disku (bez Qt-a).

Red se pamti da se pri zatvaranju ili padu ne izgubi ono što čeka, a istorija služi da se vidi
šta je i kada preuzeto. Kolačići prijave se NIKAD ne upisuju — ostaju samo u memoriji.
"""

import contextlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .jobs import ItemStatus, QueueItem

MAX_HISTORY = 500
FORMAT = 1  # verzija formata fajlova; noviji format se čita koliko se može, ali se ne prepisuje slijepo
_QUEUE_FIELDS = ("url", "title", "preset_key", "output_dir", "subfolder", "status", "message", "filepath",
                 "http_headers", "filename_title", "thumbnail", "duration", "custom_format", "section")
# Stanja koja nema smisla pamtiti: gotovo ide u istoriju, a prekinuto se ne vraća samo od sebe.
_KEEP_STATUSES = (ItemStatus.WAITING, ItemStatus.ACTIVE, ItemStatus.FAILED)


@dataclass(frozen=True)
class HistoryEntry:
    url: str
    title: str
    filepath: str
    size: int
    finished_at: float

    @property
    def exists(self) -> bool:
        return bool(self.filepath) and os.path.isfile(self.filepath)


def queue_path(data_dir: Path) -> Path:
    return data_dir / "queue.json"


def history_path(data_dir: Path) -> Path:
    return data_dir / "history.json"


def save_queue(items, path: Path) -> bool:
    """Upisuje red; False kad upis nije uspio (npr. pun disk) — prozor to javlja korisniku."""
    rows = []
    for item in items:
        if item.status not in _KEEP_STATUSES:
            continue
        row = {field: getattr(item, field) for field in _QUEUE_FIELDS}
        row["status"] = str(ItemStatus.WAITING)  # prekinuto pri zatvaranju čeka novi pokušaj
        row["message"] = ""
        rows.append(row)
    return _write(path, {"format": FORMAT, "items": rows})


def load_queue(path: Path) -> list[dict]:
    """Redovi za `DownloadQueue.add`. Svako polje se provjerava posebno: loše polje se izostavi,
    loš red se preskoči, a ostali redovi se čuvaju."""
    rows = []
    for row in _rows(_read(path), "items"):
        url = row.get("url")
        if not isinstance(url, str) or not url:
            continue
        clean = {"url": url}
        for field in ("title", "preset_key", "output_dir", "status", "message"):
            if isinstance(row.get(field), str):
                clean[field] = row[field]
        for field in ("subfolder", "filepath", "filename_title", "thumbnail"):
            if row.get(field) is None or isinstance(row.get(field), str):
                if field in row:
                    clean[field] = row[field]
        headers = row.get("http_headers")
        if isinstance(headers, dict):
            clean["http_headers"] = {k: v for k, v in headers.items() if isinstance(k, str) and isinstance(v, str)}
        duration = _number(row.get("duration"))
        if duration is not None:
            clean["duration"] = duration
        if isinstance(row.get("custom_format"), bool):
            clean["custom_format"] = row["custom_format"]
        section = row.get("section")
        if isinstance(section, (list, tuple)) and len(section) == 2:
            start, end = _number(section[0]), _number(section[1])
            if start is not None and end is not None and 0 <= start < end:
                clean["section"] = [start, end]
        rows.append(clean)
    return rows


def append_history(item: QueueItem, path: Path, size: int | None = None, now: float | None = None) -> bool:
    entries = [entry for entry in load_history(path) if entry.filepath != (item.filepath or "")]
    entries.insert(0, HistoryEntry(item.url, item.title, item.filepath or "",
                                   int(size or 0), now if now is not None else time.time()))
    return _write(path, {"format": FORMAT, "entries": [vars(entry) for entry in entries[:MAX_HISTORY]]})


def load_history(path: Path) -> list[HistoryEntry]:
    """Istorija; zapis s pogrešnim tipom polja dobija podrazumijevanu vrijednost ili se preskače,
    ali nikad ne obara učitavanje ostalih."""
    entries = []
    for row in _rows(_read(path), "entries"):
        url = row.get("url")
        if not isinstance(url, str):
            continue
        title, filepath = row.get("title"), row.get("filepath")
        entries.append(HistoryEntry(url, title if isinstance(title, str) else "",
                                    filepath if isinstance(filepath, str) else "",
                                    int(_number(row.get("size")) or 0), float(_number(row.get("finished_at")) or 0)))
    return entries


def clear_history(path: Path) -> None:
    path.unlink(missing_ok=True)


# ---------- interno ----------

def _number(value) -> float | None:
    """Broj iz JSON-a; bool, tekst i ostalo nisu broj."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value == value else None  # NaN nije broj


def _rows(data: dict, key: str) -> list[dict]:
    rows = data.get(key)
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _read(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}  # nema fajla: počinje se od praznog
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        _keep_damaged(path)
        return {}
    return data


def _keep_damaged(path: Path) -> None:
    """Oštećen fajl se sačuva sa strane (…json.ostecen) prije nego ga sljedeći upis zamijeni,
    da se podaci mogu ručno spasiti."""
    try:
        os.replace(path, path.with_name(path.name + ".ostecen"))
    except OSError:
        pass


def _write(path: Path, data: dict) -> bool:
    temporary = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporary, path)  # prekid usred pisanja ne smije ostaviti pola fajla
        return True
    except OSError:
        # Na Macu brisanje u nepostojećem folderu javlja „nije folder" (ne FileNotFoundError):
        # čišćenje ne smije srušiti program, samo se javi da čuvanje nije uspjelo.
        with contextlib.suppress(OSError):
            temporary.unlink(missing_ok=True)
        return False
