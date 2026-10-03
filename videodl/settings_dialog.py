"""Prozor „Postavke" (Ahmed 3.10.2026, po uzoru na slične programe i našu Android aplikaciju).

Sve opcije koje su bile razbacane po menijima Fajl, Preuzimanja i Pomoć, na jednom mjestu i u grupama.
Meniji ostaju (navika), a prozor koristi ISTE metode prozora, pa su meni i Postavke uvijek usklađeni.
Svaka promjena važi odmah; nema dugmeta „Sačuvaj".
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from . import theme
from .i18n import LANGUAGES, get_language, tr


def _plain(key: str) -> str:
    """Tekst iz menija bez „&" (prečica) i „…"."""
    return tr(key).replace("&", "").rstrip("…").strip()


class SettingsDialog(QDialog):
    def __init__(self, window, rate_choices, parallel_choices, name_templates):
        super().__init__(window)
        self._window = window
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Preuzimanje
        download = QGroupBox(tr("settings.group_download"))
        download_box = QVBoxLayout(download)
        form = QFormLayout()
        download_box.addLayout(form)
        folder_row = QHBoxLayout()
        self.folder_label = QLabel()
        self.folder_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        folder_row.addWidget(self.folder_label, 1)
        change = QPushButton(tr("settings.change"))
        change.clicked.connect(self._choose_folder)
        folder_row.addWidget(change)
        form.addRow(tr("settings.folder"), folder_row)
        self.parallel = QComboBox()
        for count in parallel_choices:
            self.parallel.addItem(str(count), count)
        self._select(self.parallel, window._parallel)
        self.parallel.currentIndexChanged.connect(lambda _i: window.set_parallel(self.parallel.currentData()))
        form.addRow(_plain("menu.parallel"), self.parallel)
        self.rate = QComboBox()
        for value in rate_choices:
            self.rate.addItem(tr("rate.value", value=value) if value else tr("rate.none"), value)
        self._select(self.rate, window._rate_limit)
        self.rate.currentIndexChanged.connect(
            lambda _i: window._set_option("_rate_limit", self.rate.currentData()))
        form.addRow(_plain("menu.rate_limit"), self.rate)
        self.name = QComboBox()
        for key in name_templates:
            self.name.addItem(tr(f"name.{key}"), key)
        self._select(self.name, window._name_template)
        self.name.currentIndexChanged.connect(
            lambda _i: window._set_option("_name_template", self.name.currentData()))
        form.addRow(_plain("menu.file_name"), self.name)
        # Kao „Smart Mode" kod drugih programa: izabrani format važi dalje (u FormLayout-u bi se tekst odsjekao).
        hint = QLabel(tr("settings.format_hint"))
        hint.setWordWrap(True)
        hint.setObjectName("supportNote")
        download_box.addWidget(hint)
        layout.addWidget(download)

        # Sadržaj uz video
        content = QGroupBox(tr("settings.group_content"))
        box = QVBoxLayout(content)
        self.subtitles = self._check(box, "menu.subtitles", window._subtitles,
                                     lambda on: window._set_option("_subtitles", on))
        self.thumbnail = self._check(box, "menu.thumbnail", window._thumbnail_cover,
                                     lambda on: window._set_option("_thumbnail_cover", on))
        self.playlist = self._check(box, "menu.whole_playlist", window._whole_playlist,
                                    lambda on: window._set_option("_whole_playlist", on))
        layout.addWidget(content)

        # Ponašanje
        behavior = QGroupBox(tr("settings.group_behavior"))
        box = QVBoxLayout(behavior)
        self.clipboard = self._check(box, "menu.watch_clipboard", window._watch_clipboard, window.set_watch_clipboard)
        self.notify = self._check(box, "menu.notify_done", window._notify_done,
                                  lambda on: window._set_option("_notify_done", on))
        layout.addWidget(behavior)

        # Izgled i jezik
        look = QGroupBox(tr("settings.group_look"))
        form = QFormLayout(look)
        self.theme = QComboBox()
        for name in theme.THEMES:
            self.theme.addItem(tr(f"theme.{name}"), name)
        self._select(self.theme, window._theme)
        self.theme.currentIndexChanged.connect(lambda _i: window.set_theme(self.theme.currentData()))
        form.addRow(_plain("menu.theme"), self.theme)
        self.language = QComboBox()
        for code, name in LANGUAGES.items():
            self.language.addItem(name, code)
        self._select(self.language, get_language())
        self.language.currentIndexChanged.connect(self._change_language)
        form.addRow(_plain("menu.language"), self.language)
        layout.addWidget(look)

        # Zaštita
        protection = QGroupBox(tr("settings.group_protection"))
        box = QHBoxLayout(protection)
        parental = QPushButton(tr("menu.parental"))
        parental.clicked.connect(window._show_parental)
        box.addWidget(parental)
        box.addStretch(1)
        layout.addWidget(protection)

        close = QPushButton(tr("settings.close"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self._show_folder()

    @staticmethod
    def _select(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    @staticmethod
    def _check(box, key: str, checked: bool, on_change) -> QCheckBox:
        check = QCheckBox(_plain(key))
        check.setChecked(bool(checked))
        check.toggled.connect(on_change)
        box.addWidget(check)
        return check

    def _show_folder(self) -> None:
        self.folder_label.setText(self._window.output_dir)

    def _choose_folder(self) -> None:
        self._window._choose_folder()
        self._show_folder()

    def _change_language(self, _index: int) -> None:
        # Jezik mijenja cijeli prozor; Postavke se zatvore i otvore ponovo na novom jeziku.
        code = self.language.currentData()
        self.accept()
        self._window.change_language(code)
        self._window.show_settings()
