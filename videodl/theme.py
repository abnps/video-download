"""Svijetla i tamna tema: sve boje prozora na jednom mjestu (stylesheet, paleta i crtani dijelovi)."""

from pathlib import Path

LIGHT = {
    "bg": "#ffffff", "text": "#202124", "muted": "#7a7a7a", "hint": "#9aa0a6",
    "border": "#e6e6e6", "row_border": "#ececec", "row_hover": "#f7faff", "menu_hover": "#eef3fb",
    "link": "#1a73e8", "icon": "#5f6368", "icon_soft": "#9aa0a6",
    "combo_border": "#cfcfcf", "combo_hover": "#9fbfe8", "selection": "#e8f0fe",
    "warning_bg": "#fff4e5", "warning_fg": "#8a5300", "warning_border": "#f3d9b1",
    "done": "#2e7d32", "failed": "#c62828", "action_hover": "#e8f0fe", "remove_hover": "#eeeeee",
    "convert_bg": "#f5f8ff", "convert_border": "#c7d7f5", "convert_fg": "#1a73e8",
    "banner_bg": "#fff8e1", "banner_border": "#f2d27a", "note": "#5f6368",
    "drop_title": "#5f6368", "status_bg": "#fafafa", "status_fg": "#666666",
    "thumb": "#2f3136", "progress_track": "#e3ecf8", "dash": "#9aa0a6", "arrow": "#7d8288",
    "download_disabled": "#a9cdf2", "support_link": "#c2185b", "alt_base": "#f5f5f5", "button": "#f3f3f3",
}

DARK = {
    "bg": "#202124", "text": "#e8eaed", "muted": "#9aa0a6", "hint": "#80868b",
    "border": "#3c4043", "row_border": "#34373b", "row_hover": "#282c33", "menu_hover": "#313a47",
    "link": "#8ab4f8", "icon": "#bdc1c6", "icon_soft": "#80868b",
    "combo_border": "#5f6368", "combo_hover": "#8ab4f8", "selection": "#394457",
    "warning_bg": "#3a2e17", "warning_fg": "#fbc16c", "warning_border": "#5c4520",
    "done": "#81c995", "failed": "#f28b82", "action_hover": "#313a47", "remove_hover": "#3c4043",
    "convert_bg": "#26303d", "convert_border": "#3d5a80", "convert_fg": "#8ab4f8",
    "banner_bg": "#3a3320", "banner_border": "#6b5a24", "note": "#9aa0a6",
    "drop_title": "#bdc1c6", "status_bg": "#1b1c1e", "status_fg": "#9aa0a6",
    "thumb": "#2f3136", "progress_track": "#33404f", "dash": "#6f7478", "arrow": "#8a8f95",
    "download_disabled": "#2c4a6b", "support_link": "#f48fb1", "alt_base": "#292a2d", "button": "#303134",
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
    return f"""
QMainWindow, QWidget#central, QScrollArea, QWidget#rows, QWidget#dropZone {{ background: {k['bg']}; }}
QMenuBar {{ background: {k['bg']}; border-bottom: 1px solid {k['border']}; padding: 2px 4px; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {k['menu_hover']}; }}
QLabel#cornerLink {{ padding-right: 10px; }}
QFrame#toolbar {{ background: {k['bg']}; border-bottom: 1px solid {k['border']}; }}
QPushButton#pasteButton, QPushButton#downloadButton {{
    color: #ffffff; border: none; border-radius: 3px; padding: 0 18px; min-height: 32px; font-size: 10pt;
}}
QPushButton#pasteButton {{ background: #4caf50; }}
QPushButton#pasteButton:hover {{ background: #43a047; }}
QPushButton#pasteButton:pressed {{ background: #388e3c; }}
QPushButton#downloadButton {{ background: #1e88e5; }}
QPushButton#downloadButton:hover {{ background: #1976d2; }}
QPushButton#downloadButton:pressed {{ background: #1565c0; }}
QPushButton#downloadButton[state="stop"] {{ background: #e53935; }}
QPushButton#downloadButton[state="stop"]:hover {{ background: #d32f2f; }}
QPushButton#downloadButton:disabled {{ background: {k['download_disabled']}; }}
QComboBox#presetCombo {{
    border: 1px solid {k['combo_border']}; border-radius: 3px; padding: 0 10px; min-height: 32px;
    background: {k['bg']}; color: {k['text']}; font-size: 10pt;
}}
QComboBox#presetCombo:hover {{ border-color: {k['combo_hover']}; }}
QComboBox#presetCombo::drop-down {{ border: none; width: 28px; }}
QComboBox#presetCombo::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}
QComboBox#presetCombo QAbstractItemView {{ border: 1px solid {k['combo_border']}; background: {k['bg']};
    color: {k['text']}; selection-background-color: {k['selection']}; selection-color: {k['text']}; }}
QLabel#warning {{ background: {k['warning_bg']}; color: {k['warning_fg']}; padding: 6px 12px;
    border-bottom: 1px solid {k['warning_border']}; }}
QFrame#queueRow {{ background: {k['bg']}; border-bottom: 1px solid {k['row_border']}; }}
QFrame#queueRow:hover {{ background: {k['row_hover']}; }}
QLabel#rowTitle {{ color: {k['text']}; font-size: 10pt; }}
QLabel#rowStatus {{ color: {k['muted']}; }}
QLabel#rowStatus[state="done"] {{ color: {k['done']}; }}
QLabel#rowStatus[state="failed"] {{ color: {k['failed']}; }}
QToolButton#rowAction {{ border: none; border-radius: 17px; background: transparent; }}
QToolButton#rowAction:hover {{ background: {k['action_hover']}; }}
QToolButton#rowRemove {{ border: none; border-radius: 10px; background: transparent; }}
QToolButton#rowRemove:hover {{ background: {k['remove_hover']}; }}
QToolButton#rowConvert {{ border: 1px solid {k['convert_border']}; border-radius: 17px; background: {k['convert_bg']};
    color: {k['convert_fg']}; font-weight: 600; font-size: 12px; }}
QToolButton#rowConvert:hover {{ background: {k['action_hover']}; border-color: {k['convert_fg']}; }}
QFrame#supportBanner {{ background: {k['banner_bg']}; border: 1px solid {k['banner_border']}; border-radius: 8px;
    margin: 0 12px 6px 12px; }}
QPushButton#supportButton {{ background: #c2185b; color: white; border: none; border-radius: 4px; padding: 6px 14px;
    font-weight: 600; }}
QPushButton#supportButton:hover {{ background: #ad1457; }}
QLabel#supportNote {{ color: {k['note']}; font-size: 12px; }}
QLabel#dropTitle {{ color: {k['drop_title']}; font-size: 10pt; }}
QLabel#dropHint {{ color: {k['hint']}; }}
QStatusBar {{ background: {k['status_bg']}; border-top: 1px solid {k['border']}; color: {k['status_fg']}; }}
QStatusBar QLabel {{ color: {k['status_fg']}; padding: 0 6px; }}
QScrollArea {{ border: none; }}
"""
