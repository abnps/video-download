"""Prozor „Postavke" (Ahmed 3.10.2026, po uzoru na slične programe i našu Android aplikaciju).

Sve opcije koje su bile razbacane po menijima Fajl, Preuzimanja i Pomoć, na jednom mjestu i u grupama.
Meniji ostaju (navika), a prozor koristi ISTE metode prozora, pa su meni i Postavke uvijek usklađeni.
Svaka promjena važi odmah; nema dugmeta „Sačuvaj".
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from . import theme
from .browser import COOKIE_BROWSER_NAMES, COOKIE_BROWSERS
from .i18n import LANGUAGES, get_language, tr
from .widgets import ElidedLabel


def _plain(key: str) -> str:
    """Tekst iz menija bez „&" (prečica) i „…"."""
    return tr(key).replace("&", "").rstrip("…").strip()


class SettingsDialog(QDialog):
    def __init__(self, window, rate_choices, parallel_choices, name_templates):
        super().__init__(window)
        self._window = window
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumWidth(540)
        outer = QVBoxLayout(self)
        # Grupe idu u prostor koji se skroluje: na nižem ekranu (laptop 768/900 px) prozor ostaje čitljiv, a
        # „Zatvori" je uvijek vidljivo.
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        outer.addWidget(scroll, 1)

        # Preuzimanje
        download = QGroupBox(tr("settings.group_download"))
        download_box = QVBoxLayout(download)
        form = QFormLayout()
        download_box.addLayout(form)
        folder_row = QHBoxLayout()
        # Duga putanja se skraćuje po sredini (vide se disk i zadnji folder); cijela je u oblačiću.
        self.folder_label = ElidedLabel(mode=Qt.TextElideMode.ElideMiddle)
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
        self.chapters = self._check(box, "settings.chapters", window._chapters,
                                    lambda on: window._set_option("_chapters", on))
        self.sponsorblock = self._check(box, "settings.sponsorblock", window._sponsorblock,
                                        lambda on: window._set_option("_sponsorblock", on))
        self.sponsorblock.setToolTip(tr("settings.sponsorblock_tip"))
        self.playlist = self._check(box, "menu.whole_playlist", window._whole_playlist,
                                    lambda on: window._set_option("_whole_playlist", on))
        self.number_playlist = self._check(box, "settings.number_playlist", window._number_playlist,
                                           lambda on: window._set_option("_number_playlist", on))
        self.precise_cut = self._check(box, "settings.precise_cut", window._precise_cut,
                                       lambda on: window._set_option("_precise_cut", on))
        self.precise_cut.setToolTip(tr("settings.precise_cut_tip"))
        self.split_chapters = self._check(box, "settings.split_chapters", window._split_chapters,
                                          lambda on: window._set_option("_split_chapters", on))
        self.split_chapters.setToolTip(tr("settings.split_chapters_tip"))
        layout.addWidget(content)

        # Prijava na sajtove: kolačići iz browsera ili cookies.txt (za video iza prijave)
        login = QGroupBox(tr("settings.group_login"))
        login_box = QVBoxLayout(login)
        row = QHBoxLayout()
        row.addWidget(QLabel(_plain("settings.cookies")))
        self.cookies = QComboBox()
        self.cookies.addItem(tr("cookies.none"), "")
        for browser in COOKIE_BROWSERS:
            self.cookies.addItem(COOKIE_BROWSER_NAMES[browser], browser)
        self.cookies.addItem(tr("cookies.file"), "file")
        self._select(self.cookies, window._cookie_browser or ("file" if window._cookie_txt else ""))
        self.cookies.currentIndexChanged.connect(self._change_cookies)
        row.addWidget(self.cookies, 1)
        login_box.addLayout(row)
        self.cookie_file = QLabel(window._cookie_txt)
        self.cookie_file.setObjectName("supportNote")
        self.cookie_file.setWordWrap(True)
        self.cookie_file.setVisible(bool(window._cookie_txt) and not window._cookie_browser)
        login_box.addWidget(self.cookie_file)
        note = QLabel(tr("cookies.note"))
        note.setWordWrap(True)
        note.setObjectName("supportNote")
        login_box.addWidget(note)
        layout.addWidget(login)

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

        close = QPushButton(tr("settings.close"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close)
        outer.addLayout(buttons)
        self._show_folder()
        # Visina po sadržaju, ali najviše koliko ekran dozvoljava (ostatak se skroluje).
        screen = (window.screen() if window is not None else None) or QApplication.primaryScreen()
        wanted = page.sizeHint().height() + close.sizeHint().height() + 48
        available = screen.availableGeometry().height() - 60 if screen else wanted
        self.resize(max(self.minimumWidth(), page.sizeHint().width() + 40), min(wanted, available))

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

    def _change_cookies(self, _index: int) -> None:
        choice = self.cookies.currentData()
        if choice == "file":
            path, _filter = QFileDialog.getOpenFileName(self, tr("cookies.file_title"), "", "cookies.txt (*.txt);;* (*)")
            if not path:
                # Odustao: vraća se prethodni izbor.
                self.cookies.blockSignals(True)
                self._select(self.cookies, self._window._cookie_browser or ("file" if self._window._cookie_txt else ""))
                self.cookies.blockSignals(False)
                return
            self._window.set_cookie_source("", path)
        else:
            self._window.set_cookie_source(choice or "", "")
        self.cookie_file.setText(self._window._cookie_txt)
        self.cookie_file.setVisible(bool(self._window._cookie_txt))

    def _show_folder(self) -> None:
        self.folder_label.setText(self._window.output_dir)
        self.folder_label.setToolTip(self._window.output_dir)

    def _choose_folder(self) -> None:
        self._window._choose_folder()
        self._show_folder()

    def _change_language(self, _index: int) -> None:
        # Jezik mijenja cijeli prozor; Postavke se zatvore i otvore ponovo na novom jeziku.
        code = self.language.currentData()
        self.accept()
        self._window.change_language(code)
        self._window.show_settings()
