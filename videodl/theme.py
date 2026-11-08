"""Svijetla i tamna tema: sve boje prozora na jednom mjestu (stylesheet, paleta i crtani dijelovi)."""

from pathlib import Path

LIGHT = {
    "bg": "#f7f9fc", "text": "#111827", "muted": "#5b6474", "hint": "#9aa0a6",
    "border": "#e3e7ee", "row_border": "#edf0f5", "row_hover": "#f3f6fc", "menu_hover": "#eef3fb",
    "link": "#1a73e8", "icon": "#5f6368", "icon_soft": "#9aa0a6",
    "combo_border": "#cfcfcf", "combo_hover": "#9fbfe8", "selection": "#e8f0fe",
    "warning_bg": "#fff4e5", "warning_fg": "#8a5300", "warning_border": "#f3d9b1",
    "done": "#2e7d32", "failed": "#c62828", "action_hover": "#e8f0fe", "remove_hover": "#eeeeee",
    "convert_bg": "#f5f8ff", "convert_border": "#c7d7f5", "convert_fg": "#1a73e8",
    "banner_bg": "#fff8e1", "banner_border": "#f2d27a", "note": "#5f6368",
    "drop_title": "#5f6368", "status_bg": "#f7f9fc", "status_fg": "#666666",
    "thumb": "#2f3136", "progress_track": "#e6ebf5", "dash": "#9aa0a6", "arrow": "#7d8288",
    "download_disabled": "#a9cdf2", "support_link": "#c2185b", "alt_base": "#f1f4f9", "button": "#f3f3f3",
    "pill_bg": "#eef1f5", "pill_fg": "#3c4043", "tab_active_bg": "#e8f0fe", "tab_active_fg": "#1a73e8",
    "light": "#ffffff", "midlight": "#ededed", "mid": "#b8b8b8", "dark": "#8f8f8f", "shadow": "#6b6b6b",
    "check_border": "#8a8f95",
    "card": "#ffffff", "accent": "#1a73e8", "accent2": "#7c4dff", "accent3": "#d81b60", "shield": "#1e8e3e",
    "bloom1": "#7aa7ff", "bloom2": "#b69cff", "bloom3": "#ff9fc9",
}

DARK = {
    "bg": "#0b0e14", "text": "#e6e9ef", "muted": "#9aa3b2", "hint": "#80868b",
    "border": "#262c38", "row_border": "#1f2530", "row_hover": "#1a202b", "menu_hover": "#1d2533",
    "link": "#8ab4f8", "icon": "#bdc1c6", "icon_soft": "#80868b",
    "combo_border": "#5f6368", "combo_hover": "#8ab4f8", "selection": "#394457",
    "warning_bg": "#3a2e17", "warning_fg": "#fbc16c", "warning_border": "#5c4520",
    "done": "#81c995", "failed": "#f28b82", "action_hover": "#1d2533", "remove_hover": "#232b3a",
    "convert_bg": "#26303d", "convert_border": "#3d5a80", "convert_fg": "#8ab4f8",
    "banner_bg": "#3a3320", "banner_border": "#6b5a24", "note": "#9aa0a6",
    "drop_title": "#bdc1c6", "status_bg": "#0b0e14", "status_fg": "#9aa0a6",
    "thumb": "#2f3136", "progress_track": "#232b3a", "dash": "#6f7478", "arrow": "#8a8f95",
    "download_disabled": "#2c4a6b", "support_link": "#f48fb1", "alt_base": "#141922", "button": "#1a202b",
    "pill_bg": "#33363b", "pill_fg": "#c4c7cc", "tab_active_bg": "#394457", "tab_active_fg": "#8ab4f8",
    "light": "#4a4d52", "midlight": "#3c4043", "mid": "#5f6368", "dark": "#141517", "shadow": "#000000",
    "check_border": "#9aa0a6",
    "card": "#141922", "accent": "#8ab4f8", "accent2": "#b39dff", "accent3": "#ff8ab6", "shield": "#81c995",
    "bloom1": "#3a5bd9", "bloom2": "#6a4fd8", "bloom3": "#b8457a",
}

THEMES = ("light", "dark", "system")
DEFAULT_THEME = "light"

_colors = dict(LIGHT)
_name = "light"


def set_colors(dark: bool) -> None:
    global _name
    _colors.clear()
    _colors.update(DARK if dark else LIGHT)
    _name = "dark" if dark else "light"


def is_dark() -> bool:
    return _name == "dark"


def c(key: str) -> str:
    return _colors[key]


def stylesheet() -> str:
    k = _colors
    chevron = (Path(__file__).parent / "assets" / "chevron-down.svg").as_posix()
    check = (Path(__file__).parent / "assets" / "check.svg").as_posix()
    return f"""
QMainWindow {{ background: {k['bg']}; }}
QScrollArea, QWidget#rows, QWidget#dropZone, QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QFrame#listCard {{ background: {k['card']}; border: 1px solid {k['border']}; border-radius: 14px; }}
QMenuBar {{ background: {k['bg']}; border-bottom: 1px solid {k['border']}; padding: 2px 4px; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {k['menu_hover']}; }}
QLabel#cornerLink {{ padding-right: 10px; }}
QFrame#toolbar {{ background: {k['card']}; border: 1px solid {k['border']}; border-radius: 14px; }}
QPushButton#pasteButton, QPushButton#downloadButton {{
    color: #ffffff; border: none; border-radius: 9px; padding: 0 18px; min-height: 34px; font-size: 10pt;
    font-weight: 600;
}}
QPushButton#pasteButton {{ background: {k['tab_active_bg']}; color: {k['accent']}; }}
QPushButton#pasteButton:hover {{ background: {k['selection']}; }}
QPushButton#pasteButton:pressed {{ background: {k['menu_hover']}; }}
QPushButton#downloadButton {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a73e8, stop:1 #7c4dff); }}
QPushButton#downloadButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1765cc, stop:1 #6f3ff0); }}
QPushButton#downloadButton:pressed {{ background: #1557b0; }}
QPushButton#downloadButton[state="stop"] {{ background: #d81b60; }}
QPushButton#downloadButton[state="stop"]:hover {{ background: #c2185b; }}
QPushButton#downloadButton:disabled {{ background: {k['download_disabled']}; }}
QComboBox#presetCombo {{
    border: 1px solid {k['combo_border']}; border-radius: 9px; padding: 0 10px; min-height: 32px;
    background: {k['bg']}; color: {k['text']}; font-size: 10pt;
    combobox-popup: 0; /* lista uvijek ispod polja; Fusion je centrira na izabranu stavku, pa je išla prema gore */
}}
QComboBox#presetCombo:hover {{ border-color: {k['combo_hover']}; }}
QComboBox#presetCombo::drop-down {{ border: none; width: 28px; }}
QComboBox#presetCombo::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}
QComboBox#presetCombo QAbstractItemView {{ border: 1px solid {k['combo_border']}; background: {k['bg']};
    color: {k['text']}; selection-background-color: {k['selection']}; selection-color: {k['text']}; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {k['check_border']}; border-radius: 3px;
    background: {k['bg']}; }}
QCheckBox::indicator:hover {{ border-color: {k['combo_hover']}; }}
QCheckBox::indicator:checked {{ background: #1e88e5; border-color: #1e88e5; image: url("{check}"); }}
QCheckBox::indicator:disabled {{ background: {k['alt_base']}; border-color: {k['border']}; }}
QCheckBox::indicator:checked:disabled {{ background: {k['hint']}; border-color: {k['hint']}; }}
QLabel#warning {{ background: {k['warning_bg']}; color: {k['warning_fg']}; padding: 6px 12px;
    border-bottom: 1px solid {k['warning_border']}; }}
QFrame#queueRow {{ background: transparent; border-bottom: 1px solid {k['row_border']}; }}
QFrame#queueRow:hover {{ background: {k['row_hover']}; }}
QLabel#rowTitle {{ color: {k['text']}; font-size: 10pt; }}
QLabel#rowStatus {{ color: {k['muted']}; }}
QLabel#pill {{ background: {k['pill_bg']}; color: {k['pill_fg']}; border-radius: 8px;
    padding: 1px 7px; font-size: 11px; font-weight: 600; }}
QToolButton#filterTab {{ border: none; border-radius: 13px; padding: 4px 12px; background: transparent;
    color: {k['muted']}; }}
QToolButton#filterTab:hover {{ background: {k['row_hover']}; color: {k['text']}; }}
QToolButton#filterTab:checked {{ background: {k['tab_active_bg']}; color: {k['tab_active_fg']}; font-weight: 600; }}
QToolButton#filterTab:disabled {{ color: {k['hint']}; }}
QLabel#rowStatus[state="done"] {{ color: {k['done']}; }}
QLabel#rowStatus[state="failed"] {{ color: {k['failed']}; }}
QToolButton#rowAction {{ border: none; border-radius: 17px; background: transparent; }}
QToolButton#rowAction:hover {{ background: {k['action_hover']}; }}
QToolButton#rowRemove {{ border: none; border-radius: 17px; background: transparent; }}
QToolButton#rowRemove:hover {{ background: {k['remove_hover']}; }}
QToolButton#rowConvert {{ border: 1px solid {k['convert_border']}; border-radius: 17px; background: {k['convert_bg']};
    color: {k['convert_fg']}; font-weight: 600; font-size: 12px; }}
QToolButton#rowConvert:hover {{ background: {k['action_hover']}; border-color: {k['convert_fg']}; }}
QFrame#supportBanner {{ background: {k['banner_bg']}; border: 1px solid {k['banner_border']}; border-radius: 8px;
    margin: 0; }}
QPushButton#supportButton {{ background: #c2185b; color: white; border: none; border-radius: 4px; padding: 6px 14px;
    font-weight: 600; }}
QPushButton#supportButton:hover {{ background: #ad1457; }}
QLabel#supportNote {{ color: {k['note']}; font-size: 12px; }}
QLabel#dropTitle {{ color: {k['drop_title']}; font-size: 10pt; }}
QLabel#dropHint {{ color: {k['hint']}; }}
QStatusBar {{ background: transparent; border-top: 1px solid {k['border']}; color: {k['status_fg']}; }}
QLabel#shieldLabel {{ color: {k['shield']}; }}
QLabel#shieldLabel[state="off"] {{ color: {k['warning_fg']}; }}
QFrame#nowPanel {{ background: {k['card']}; border: 1px solid {k['border']}; border-radius: 14px; }}
QLabel#nowChip {{ background: {k['tab_active_bg']}; color: {k['accent']}; border-radius: 8px; padding: 2px 10px;
    font-weight: 600; font-size: 11px; }}
QLabel#nowTitle {{ color: {k['text']}; font-size: 12pt; font-weight: 600; }}
QLabel#nowMuted, QLabel#nowCaption {{ color: {k['muted']}; }}
QLabel#nowCaption {{ font-size: 11px; }}
QLabel#nowValue, QLabel#nowPercent {{ color: {k['text']}; font-weight: 600; }}
QLabel#nowPhase {{ color: {k['hint']}; font-size: 11px; }}
QLabel#nowPhase[state="on"] {{ color: {k['text']}; font-weight: 600; }}
QFrame#nowDivider {{ background: {k['row_border']}; border: none; max-height: 1px; min-height: 1px; }}
QStatusBar QLabel {{ color: {k['status_fg']}; padding: 0 6px; }}
QScrollArea {{ border: none; }}
"""
