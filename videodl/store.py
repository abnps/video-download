"""Red i istorija preuzimanja na disku (bez Qt-a).

Red se pamti da se pri zatvaranju ili padu ne izgubi ono što čeka, a istorija služi da se vidi
šta je i kada preuzeto. Kolačići prijave se NIKAD ne upisuju — ostaju samo u memoriji.
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .jobs import ItemStatus, QueueItem

MAX_HISTORY = 500
_QUEUE_FIELDS = ("url", "title", "preset_key", "output_dir", "subfolder", "status", "message", "filepath",
                 "http_headers", "filename_title", "thumbnail", "duration", "custom_format")
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


def save_queue(items, path: Path) -> None:
    rows = []
    for item in items:
        if item.status not in _KEEP_STATUSES:
            continue
        row = {field: getattr(item, field) for field in _QUEUE_FIELDS}
        row["status"] = str(ItemStatus.WAITING)  # prekinuto pri zatvaranju čeka novi pokušaj
        row["message"] = ""
        rows.append(row)
    _write(path, {"items": rows})


def load_queue(path: Path) -> list[dict]:
    """Redovi za `DownloadQueue.add`; nepoznata ili oštećena datoteka daje prazan red."""
    data = _read(path)
    rows = []
    for row in data.get("items") or []:
        if isinstance(row, dict) and isinstance(row.get("url"), str) and row.get("url"):
            rows.append({field: row.get(field) for field in _QUEUE_FIELDS if field in row})
    return rows


def append_history(item: QueueItem, path: Path, size: int | None = None, now: float | None = None) -> None:
    entries = [entry for entry in load_history(path) if entry.filepath != (item.filepath or "")]
    entries.insert(0, HistoryEntry(item.url, item.title, item.filepath or "",
                                   int(size or 0), now if now is not None else time.time()))
    _write(path, {"entries": [vars(entry) for entry in entries[:MAX_HISTORY]]})


def load_history(path: Path) -> list[HistoryEntry]:
    entries = []
    for row in _read(path).get("entries") or []:
        if isinstance(row, dict) and isinstance(row.get("url"), str):
            entries.append(HistoryEntry(row.get("url") or "", row.get("title") or "", row.get("filepath") or "",
                                        int(row.get("size") or 0), float(row.get("finished_at") or 0)))
    return entries


def clear_history(path: Path) -> None:
    path.unlink(missing_ok=True)


# ---------- interno ----------

def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}  # nema fajla ili je oštećen: počinje se od praznog
    return data if isinstance(data, dict) else {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporary, path)  # prekid usred pisanja ne smije ostaviti pola fajla
    except OSError:
        temporary.unlink(missing_ok=True)
