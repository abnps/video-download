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


class DownloadQueue:
    def __init__(self):
        self._items: list[QueueItem] = []
        self._next_id = 1

    def add(self, url: str, title: str, preset_key: str, output_dir: str,
            subfolder: str | None = None, *, http_headers: dict[str, str] | None = None,
            filename_title: str | None = None) -> QueueItem:
        item = QueueItem(self._next_id, url, title, preset_key, output_dir, subfolder,
                         http_headers=dict(http_headers or {}), filename_title=filename_title)
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

    def clear_finished(self) -> list[int]:
        removed = [item.id for item in self._items if item.status == ItemStatus.DONE]
        self._items = [item for item in self._items if item.status != ItemStatus.DONE]
        return removed
