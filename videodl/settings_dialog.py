"""Prozor „Postavke" (Ahmed 3.10.2026, po uzoru na slične programe i našu Android aplikaciju).

Sve opcije koje su bile razbacane po menijima Fajl, Preuzimanja i Pomoć, na jednom mjestu i u grupama.
Meniji ostaju (navika), a prozor koristi ISTE metode prozora, pa su meni i Postavke uvijek usklađeni.
Svaka promjena važi odmah; nema dugmeta „Sačuvaj".

Izgled 1.0.8 (Ahmed 3.11.2026, „malo ljepše"): stranice lijevo kao u Postavkama Windowsa 11, desno kartice u
kojima svaki red ima naziv, kratko objašnjenje i kontrolu desno; prekidači umjesto kvadratića.
"""

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from . import theme
from .browser import COOKIE_BROWSER_NAMES, COOKIE_BROWSERS
from .i18n import LANGUAGES, get_language, tr
from .widgets import ElidedLabel

ACCENT = "#1e88e5"
CONTROL_WIDTH = 220
MAX_HEIGHT = 660  # viša stranica se skroluje; prozor ne treba zauzeti cijeli ekran


def _plain(key: str) -> str:
    """Tekst iz menija bez „&" (prečica) i „…"."""
    return tr(key).replace("&", "").rstrip("…").strip()


class ToggleSwitch(QCheckBox):
    """Prekidač (kao na telefonu): isti QCheckBox (isChecked, setChecked, toggled), samo drugačije nacrtan."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.sizeHint())

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        on = self.isChecked()
        track = QColor(ACCENT if on else theme.c("mid"))
        if not self.isEnabled():
            track.setAlpha(110)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        rect = QRectF(1, 2, self.width() - 2, self.height() - 4)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        diameter = rect.height() - 6
        x = rect.right() - diameter - 3 if on else rect.left() + 3
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(x, rect.top() + 3, diameter, diameter))
        if self.hasFocus():
            painter.setPen(QColor(theme.c("combo_hover")))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), rect.height() / 2 + 1, rect.height() / 2 + 1)


def settings_stylesheet() -> str:
    k = theme.c
    chevron = (Path(__file__).parent / "assets" / "chevron-down.svg").as_posix()
    return f"""
QDialog#settings {{ background: {k('bg')}; }}
QListWidget#settingsNav {{ background: {k('alt_base')}; border: none; border-right: 1px solid {k('border')};
    padding: 10px 8px; outline: none; }}
QListWidget#settingsNav::item {{ padding: 9px 12px; border-radius: 6px; margin: 1px 0; color: {k('text')}; }}
QListWidget#settingsNav::item:hover {{ background: {k('menu_hover')}; }}
QListWidget#settingsNav::item:selected {{ background: {k('tab_active_bg')}; color: {k('tab_active_fg')}; }}
QWidget#settingsPage, QScrollArea#settingsScroll {{ background: {k('bg')}; }}
QLabel#pageTitle {{ color: {k('text')}; }}
QFrame#settingsCard {{ background: {k('bg')}; border: 1px solid {k('row_border')}; border-radius: 10px; }}
QFrame#settingsDivider {{ background: {k('row_border')}; border: none; max-height: 1px; min-height: 1px; }}
QLabel#rowTitle {{ color: {k('text')}; background: transparent; }}
QLabel#rowDesc {{ color: {k('muted')}; background: transparent; }}
QLabel#cardNote {{ color: {k('note')}; background: transparent; }}
QFrame#settingsFooter {{ background: {k('bg')}; border-top: 1px solid {k('border')}; }}
QComboBox#settingsCombo {{ border: 1px solid {k('combo_border')}; border-radius: 6px; padding: 4px 10px;
    background: {k('bg')}; color: {k('text')}; min-height: 22px; }}
QComboBox#settingsCombo:hover {{ border-color: {k('combo_hover')}; }}
QComboBox#settingsCombo::drop-down {{ border: none; width: 26px; }}
QComboBox#settingsCombo::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}
QComboBox#settingsCombo QAbstractItemView {{ border: 1px solid {k('combo_border')}; background: {k('bg')};
    selection-background-color: {k('selection')}; selection-color: {k('text')}; }}
"""


class SettingsDialog(QDialog):
    def __init__(self, window, rate_choices, parallel_choices, name_templates):
        super().__init__(window)
        self._window = window
        self.setObjectName("settings")
        self.setWindowTitle(tr("settings.title"))
        self.setStyleSheet(settings_stylesheet())
        self.setMinimumSize(720, 460)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setAccessibleName(tr("settings.title"))
        self.nav.setFixedWidth(210)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.addWidget(self.nav)
        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)
        self.nav.currentRowChanged.connect(self._show_page)

        # ---------- Preuzimanje ----------
        page = self._page("⬇", tr("settings.group_download"))
        card = self._card(page)
        self.folder_label = ElidedLabel(mode=Qt.TextElideMode.ElideMiddle)
        self.folder_label.setObjectName("rowDesc")
        change = QPushButton(tr("settings.change"))
        change.clicked.connect(self._choose_folder)
        self._row(card, tr("settings.folder"), tr("settings.desc.folder"), change, extra=self.folder_label)
        self.parallel = self._combo([(str(count), count) for count in parallel_choices], window._parallel)
        self.parallel.currentIndexChanged.connect(lambda _i: window.set_parallel(self.parallel.currentData()))
        self._row(card, _plain("menu.parallel"), tr("settings.desc.parallel"), self.parallel)
        self.rate = self._combo([(tr("rate.value", value=value) if value else tr("rate.none"), value)
                                 for value in rate_choices], window._rate_limit)
        self.rate.currentIndexChanged.connect(lambda _i: window._set_option("_rate_limit", self.rate.currentData()))
        self._row(card, _plain("menu.rate_limit"), tr("settings.desc.rate"), self.rate)
        self.name = self._combo([(tr(f"name.{key}"), key) for key in name_templates], window._name_template)
        self.name.currentIndexChanged.connect(lambda _i: window._set_option("_name_template", self.name.currentData()))
        self._row(card, _plain("menu.file_name"), tr("settings.desc.name"), self.name)
        # Kao „Smart Mode" kod drugih programa: izabrani format važi dalje.
        self._note(page, tr("settings.format_hint"))

        # ---------- Uz video ----------
        page = self._page("🎬", tr("settings.group_content"))
        card = self._card(page)
        self.subtitles = self._switch(card, _plain("menu.subtitles"), "settings.desc.subtitles", window._subtitles,
                                      lambda on: window._set_option("_subtitles", on))
        # Titl u slici (Ahmed 12.11.2026): izbor uz titlove; bez titlova nema šta da se upiše.
        self.burn = self._switch(card, tr("settings.burn"), "settings.desc.burn", window._subtitles_burn,
                                 lambda on: window._set_option("_subtitles_burn", on))
        self.burn.setEnabled(window._subtitles)
        self.subtitles.toggled.connect(self.burn.setEnabled)
        self.thumbnail = self._switch(card, _plain("menu.thumbnail"), "settings.desc.thumbnail", window._thumbnail_cover,
                                      lambda on: window._set_option("_thumbnail_cover", on))
        self.chapters = self._switch(card, _plain("settings.chapters"), "settings.desc.chapters", window._chapters,
                                     lambda on: window._set_option("_chapters", on))
        self.sponsorblock = self._switch(card, _plain("settings.sponsorblock"), "settings.desc.sponsorblock",
                                         window._sponsorblock, lambda on: window._set_option("_sponsorblock", on),
                                         tip="settings.sponsorblock_tip")
        card = self._card(page)
        self.playlist = self._switch(card, _plain("menu.whole_playlist"), "settings.desc.playlist", window._whole_playlist,
                                     lambda on: window._set_option("_whole_playlist", on))
        self.number_playlist = self._switch(card, _plain("settings.number_playlist"), "settings.desc.number",
                                            window._number_playlist, lambda on: window._set_option("_number_playlist", on))
        self.precise_cut = self._switch(card, _plain("settings.precise_cut"), "settings.desc.precise", window._precise_cut,
                                        lambda on: window._set_option("_precise_cut", on), tip="settings.precise_cut_tip")
        self.split_chapters = self._switch(card, _plain("settings.split_chapters"), "settings.desc.split",
                                           window._split_chapters, lambda on: window._set_option("_split_chapters", on),
                                           tip="settings.split_chapters_tip")

        # ---------- Prijava na sajtove: kolačići iz browsera ili cookies.txt (za video iza prijave) ----------
        page = self._page("🔑", tr("settings.group_login"))
        card = self._card(page)
        self.cookies = QComboBox()
        self.cookies.setObjectName("settingsCombo")
        self.cookies.setFixedWidth(CONTROL_WIDTH)
        self.cookies.addItem(tr("cookies.none"), "")
        for browser in COOKIE_BROWSERS:
            self.cookies.addItem(COOKIE_BROWSER_NAMES[browser], browser)
        self.cookies.addItem(tr("cookies.file"), "file")
        self._select(self.cookies, window._cookie_browser or ("file" if window._cookie_txt else ""))
        self.cookies.currentIndexChanged.connect(self._change_cookies)
        self.cookie_file = QLabel(window._cookie_txt)
        self.cookie_file.setObjectName("rowDesc")
        self.cookie_file.setWordWrap(True)
        self.cookie_file.setVisible(bool(window._cookie_txt) and not window._cookie_browser)
        self._row(card, _plain("settings.cookies"), None, self.cookies, extra=self.cookie_file)
        self._note(page, tr("cookies.note"))

        # ---------- Ponašanje ----------
        page = self._page("⚙", tr("settings.group_behavior"))
        card = self._card(page)
        self.clipboard = self._switch(card, _plain("menu.watch_clipboard"), "settings.desc.clipboard",
                                      window._watch_clipboard, window.set_watch_clipboard)
        self.notify = self._switch(card, _plain("menu.notify_done"), "settings.desc.notify", window._notify_done,
                                   lambda on: window._set_option("_notify_done", on))
        card = self._card(page)
        # Zaštita od blokade i mjesečni pregled (Ahmed 2.11.2026): oboje uključeno dok se ne isključi.
        self.pacing_note = QLabel(tr("settings.pacing_off_note"))
        self.pacing_note.setObjectName("warning")
        self.pacing_note.setWordWrap(True)
        self.pacing_note.setVisible(not window._pacer.enabled)
        self.pacing = self._switch(card, tr("settings.row.pacing"), "settings.desc.pacing", window._pacer.enabled,
                                   self._change_pacing, tip="settings.pacing_tip", extra=self.pacing_note)
        self.recap = self._switch(card, _plain("settings.recap"), "settings.desc.recap", window._recap_enabled,
                                  window.set_recap_enabled)

        # ---------- Izgled i jezik ----------
        page = self._page("🎨", tr("settings.group_look"))
        card = self._card(page)
        self.theme = self._combo([(tr(f"theme.{name}"), name) for name in theme.THEMES], window._theme)
        self.theme.currentIndexChanged.connect(self._change_theme)
        self._row(card, _plain("menu.theme"), tr("settings.desc.theme"), self.theme)
        self.language = self._combo(list((name, code) for code, name in LANGUAGES.items()), get_language())
        self.language.currentIndexChanged.connect(self._change_language)
        self._row(card, _plain("menu.language"), tr("settings.desc.language"), self.language)

        for index in range(self.pages.count()):
            self.pages.widget(index).widget().layout().addStretch(1)
        # Meni lijevo širok koliko treba najdužem naslovu (duži prevodi, veća slova u Windowsu).
        metrics = self.nav.fontMetrics()
        longest = max(metrics.horizontalAdvance(self.nav.item(i).text()) for i in range(self.nav.count()))
        self.nav.setFixedWidth(max(210, longest + 60))

        footer = QFrame()
        footer.setObjectName("settingsFooter")
        buttons = QHBoxLayout(footer)
        buttons.setContentsMargins(16, 10, 16, 10)
        buttons.addStretch(1)
        close = QPushButton(tr("settings.close"))
        close.setDefault(True)
        close.setMinimumWidth(110)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        outer.addWidget(footer)

        self._show_folder()
        start = getattr(window, "_settings_page", 0)
        self.nav.setCurrentRow(start if 0 <= start < self.nav.count() else 0)
        # Visina po najvišoj stranici, ali najviše koliko ekran dozvoljava (ostatak se skroluje).
        screen = (window.screen() if window is not None else None) or QApplication.primaryScreen()
        tallest = max(self.pages.widget(i).widget().sizeHint().height() for i in range(self.pages.count()))
        wanted = tallest + footer.sizeHint().height() + 8
        available = screen.availableGeometry().height() - 80 if screen else wanted
        self.resize(780, max(self.minimumHeight(), min(wanted, MAX_HEIGHT, available)))

    # ---------- građa stranice ----------

    def _page(self, emoji: str, title: str) -> QVBoxLayout:
        """Nova stranica: stavka u meniju lijevo i naslov gore; vraća raspored u koji idu kartice."""
        item = QListWidgetItem(f"{emoji}   {title}")
        item.setSizeHint(QSize(0, 38))
        self.nav.addItem(item)
        page = QWidget()
        page.setObjectName("settingsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        font = QFont(heading.font())
        font.setPointSize(font.pointSize() + 6)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        self.pages.addWidget(scroll)
        return layout

    @staticmethod
    def _card(layout: QVBoxLayout) -> QVBoxLayout:
        card = QFrame()
        card.setObjectName("settingsCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        layout.addWidget(card)
        return box

    @staticmethod
    def _note(layout: QVBoxLayout, text: str) -> None:
        note = QLabel(text)
        note.setObjectName("cardNote")
        note.setWordWrap(True)
        note.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(note)

    @staticmethod
    def _row(card: QVBoxLayout, title: str, description: str | None, control: QWidget,
             extra: QWidget | None = None, tip: str | None = None) -> None:
        """Red kartice: naziv i opis lijevo, kontrola desno; `extra` ide ispod (npr. putanja, upozorenje)."""
        if card.count():
            divider = QFrame()
            divider.setObjectName("settingsDivider")
            card.addWidget(divider)
        row = QWidget()
        box = QVBoxLayout(row)
        box.setContentsMargins(16, 12, 16, 12)
        box.setSpacing(6)
        line = QHBoxLayout()
        line.setSpacing(16)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        name = QLabel(title)
        name.setObjectName("rowTitle")
        name.setWordWrap(True)
        texts.addWidget(name)
        if description:
            desc = QLabel(description)
            desc.setObjectName("rowDesc")
            desc.setWordWrap(True)
            texts.addWidget(desc)
        line.addLayout(texts, 1)
        line.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        # Čitač ekrana: izbor dobije naziv reda (prekidač ga već ima, dugme ima svoj tekst), a sve kontrole opis.
        if isinstance(control, QComboBox) and not control.accessibleName():
            control.setAccessibleName(title)
        if description:
            control.setAccessibleDescription(description)
        box.addLayout(line)
        if extra is not None:
            box.addWidget(extra)
        if tip:
            row.setToolTip(tip)
            control.setToolTip(tip)
        card.addWidget(row)

    def _switch(self, card: QVBoxLayout, title: str, description_key: str, checked: bool, on_change,
                tip: str | None = None, extra: QWidget | None = None) -> ToggleSwitch:
        switch = ToggleSwitch()
        switch.setChecked(bool(checked))
        switch.setAccessibleName(title)
        switch.toggled.connect(on_change)
        self._row(card, title, tr(description_key), switch, extra=extra, tip=tr(tip) if tip else None)
        return switch

    def _combo(self, items, current) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("settingsCombo")
        combo.setFixedWidth(CONTROL_WIDTH)
        for text, data in items:
            combo.addItem(text, data)
        self._select(combo, current)
        return combo

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self._window._settings_page = index  # Postavke se sljedeći put otvaraju na istoj stranici

    @staticmethod
    def _select(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    # ---------- radnje ----------

    def _change_pacing(self, on: bool) -> None:
        """Isključivanje zaštite od blokade traži potvrdu: YouTube tada može blokirati dalje preuzimanje."""
        if not on and not self._window.confirm_pacing_off():
            self.pacing.blockSignals(True)
            self.pacing.setChecked(True)
            self.pacing.blockSignals(False)
            self.pacing.update()
            return
        self._window.set_pacing(on)
        self.pacing_note.setVisible(not on)

    def _change_theme(self, _index: int) -> None:
        self._window.set_theme(self.theme.currentData())
        self.setStyleSheet(settings_stylesheet())  # i ovaj prozor odmah u novoj temi
        for switch in self.findChildren(ToggleSwitch):
            switch.update()

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
        # Jezik mijenja cijeli prozor; Postavke se zatvore i otvore ponovo na novom jeziku (ista stranica).
        code = self.language.currentData()
        self.accept()
        self._window.change_language(code)
        self._window.show_settings()
