"""Red čekanja preuzimanja, bez zavisnosti od GUI-ja."""

from dataclasses import dataclass, field
from enum import StrEnum


class ItemStatus(StrEnum):
    WAITING = "waiting"
    ACTIVE = "active"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueItem:
    id: int
    url: str
    title: str
    preset_key: str
    output_dir: str
    subfolder: str | None = None
    status: ItemStatus = ItemStatus.WAITING
    message: str = ""
    filepath: str | None = None
    # Stavke iz browsera: zaglavlja koja server toka traži i naslov stranice za ime fajla.
    http_headers: dict[str, str] = field(default_factory=dict)
    filename_title: str | None = None
    thumbnail: str | None = None
    duration: float | None = None
    # Format izabran baš za ovu stavku; promjena glavnog formata ga ne mijenja.
    custom_format: bool = False
    # Koliko puta je aplikacija sama ponovila pokušaj poslije pucanja veze.
    auto_retries: int = 0
    # Kolačići prijave iz browsera: samo u memoriji, nikad u podešavanjima ni na disku.
    cookies: tuple = field(default=(), repr=False)


class DownloadQueue:
    def __init__(self):
        self._items: list[QueueItem] = []
        self._next_id = 1

    def add(self, url: str, title: str, preset_key: str, output_dir: str,
            subfolder: str | None = None, *, http_headers: dict[str, str] | None = None,
            filename_title: str | None = None, thumbnail: str | None = None,
            duration: float | None = None, cookies: tuple = ()) -> QueueItem:
        item = QueueItem(self._next_id, url, title, preset_key, output_dir, subfolder,
                         http_headers=dict(http_headers or {}), filename_title=filename_title,
                         thumbnail=thumbnail, duration=duration, cookies=tuple(cookies))
        self._next_id += 1
        self._items.append(item)
        return item

    def items(self) -> list[QueueItem]:
        return list(self._items)

    def get(self, item_id: int) -> QueueItem | None:
        return next((item for item in self._items if item.id == item_id), None)

    def next_waiting(self) -> QueueItem | None:
        return next((item for item in self._items if item.status == ItemStatus.WAITING), None)

    def active(self) -> QueueItem | None:
        return next((item for item in self._items if item.status == ItemStatus.ACTIVE), None)

    def move_to_front(self, item_id: int) -> bool:
        item = self.get(item_id)
        if item is None:
            return False
        self._items.remove(item)
        self._items.insert(0, item)
        return True

    def remove(self, item_id: int) -> bool:
        item = self.get(item_id)
        if item is None or item.status == ItemStatus.ACTIVE:
            return False
        self._items.remove(item)
        return True

    def retry(self, item_id: int) -> bool:
        item = self.get(item_id)
        if item is None or item.status not in (ItemStatus.FAILED, ItemStatus.CANCELLED):
            return False
        item.status = ItemStatus.WAITING
        item.message = ""
        return True

    def set_preset(self, item_id: int, preset_key: str) -> bool:
        """Format za jednu stavku. Već preuzeta ili neuspjela stavka se vraća u red."""
        item = self.get(item_id)
        if item is None or item.status == ItemStatus.ACTIVE:
            return False
        item.preset_key = preset_key
        item.custom_format = True
        if item.status != ItemStatus.WAITING:
            item.status = ItemStatus.WAITING
            item.message = ""
            item.filepath = None
        return True

    def apply_preset_to_waiting(self, preset_key: str) -> list[int]:
        changed = []
        for item in self._items:
            if item.status == ItemStatus.WAITING and not item.custom_format and item.preset_key != preset_key:
                item.preset_key = preset_key
                changed.append(item.id)
        return changed

    def clear_finished(self) -> list[int]:
        removed = [item.id for item in self._items if item.status == ItemStatus.DONE]
        self._items = [item for item in self._items if item.status != ItemStatus.DONE]
        return removed
