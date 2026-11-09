"""PitBoss-Optik fuer RaceRoom Results Companion (Dark Theme, RaceRoom-Rot-Akzent).

Palettenelemente und Stil entsprechen dem dunklen PitBoss-R3E-Theme:
dunkle Panels (#0c0c0e/#131316), RaceRoom-Rot #e8212b als Akzent,
Schrift Montserrat/Segoe UI, eckige (radius-0) Steuerelemente.
"""
RR_RED = "#e8212b"
RR_RED_H = "#ff3a45"
RR_RED_D = "#a81119"

_PAL = {
    "BG": "#0c0c0e", "PANEL": "#131316", "PANEL2": "#1a1a1f", "INPUT": "#15151a",
    "LINE": "#26262c", "LINE2": "#34343c", "TEXT": "#f1f1f3", "MUTED": "#8f8f99",
    "BAR": "#101013", "HOVER": "#1c1c21", "ACC": RR_RED, "ACC_H": RR_RED_H,
    "ACC_D": RR_RED_D, "SCROLL": "#34343c", "ACC_TXT": "#ff5a63",
    "SEL": "rgba(232,33,43,0.85)", "CARD": "rgba(12,12,15,0.74)",
    "NAV": "rgba(52,51,56,0.92)", "NAV_H": "rgba(80,79,86,0.96)",
    "BTN": "rgba(52,51,56,0.92)", "BTN_H": "rgba(80,79,86,0.96)",
    "BTN_B": "rgba(255,255,255,0.07)",
}

_QSS = """
QWidget { font-family: "Montserrat", "Segoe UI", "Inter", sans-serif; font-size: 13px; color: @TEXT@; }
QMainWindow, QWidget { background: @BG@; }
QLabel { background: transparent; color: @TEXT@; }
QLabel[plain="true"] { background: transparent; }
QLabel#brandTitle { font-size: 19px; font-weight: 800; color: @TEXT@; background: transparent; }
QLabel#brandSub, QLabel#hint, QLabel#statusLine { color: @MUTED@; background: transparent; font-size: 12px; }
QLabel#sectionTitle { font-size: 11px; font-weight: 800; color: @MUTED@; background: transparent; }
QTabWidget::pane { border: none; border-top: 1px solid @LINE@; background: transparent; top: -1px; }
QTabBar::tab { background: transparent; color: @MUTED@; padding: 9px 18px; margin-right: 2px; border: none; border-bottom: 2px solid transparent; font-weight: 700; }
QTabBar::tab:hover { color: @TEXT@; }
QTabBar::tab:selected { color: @TEXT@; border-bottom: 2px solid @ACC@; }
QPushButton { background: @BTN@; color: @TEXT@; border: 1px solid @BTN_B@; padding: 8px 16px; border-radius: 0; font-weight: 700; }
QPushButton:hover { border-color: @ACC@; background: @BTN_H@; }
QPushButton:pressed { background: @BG@; }
QPushButton:disabled { color: @MUTED@; background: @PANEL@; border-color: @LINE@; }
QPushButton#primary { background: @ACC@; color: #ffffff; border: 1px solid @ACC@; padding: 9px 20px; }
QPushButton#primary:hover { background: @ACC_H@; border-color: @ACC_H@; }
QPushButton#primary:pressed { background: @ACC_D@; }
QTextEdit, QLineEdit, QComboBox, QSpinBox { background: @INPUT@; color: @TEXT@; border: 1px solid @LINE@; border-radius: 2px; selection-background-color: @ACC@; selection-color: #ffffff; }
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus { border: 1px solid @ACC@; }
QComboBox { padding: 3px 30px 3px 10px; min-height: 30px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: right center; width: 26px; border: none; border-left: 1px solid @LINE@; background: @PANEL2@; }
QComboBox::drop-down:hover { background: @ACC@; }
QComboBox::down-arrow { image: none; width: 1px; }
QComboBox QAbstractItemView { background: @PANEL@; color: @TEXT@; selection-background-color: @ACC@; selection-color: #ffffff; outline: 0; border: 1px solid @LINE2@; padding: 2px; }
QTableView, QTableWidget { background: @INPUT@; color: @TEXT@; gridline-color: @LINE@; alternate-background-color: @PANEL@; border: 1px solid @LINE@; border-radius: 2px; selection-background-color: @SEL@; selection-color: #ffffff; }
QTableView::item, QTableWidget::item { padding: 4px 6px; }
QTableView::item:selected, QTableWidget::item:selected { background: @SEL@; color: #ffffff; }
QHeaderView::section { background: @PANEL2@; color: @MUTED@; padding: 7px 8px; border: none; border-bottom: 1px solid @LINE2@; font-weight: 700; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: @SCROLL@; border-radius: 2px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: @ACC@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 9px; margin: 2px; }
QScrollBar::handle:horizontal { background: @SCROLL@; border-radius: 2px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: @ACC@; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QMenu { background: @PANEL@; color: @TEXT@; border: 1px solid @LINE2@; padding: 4px; }
QMenu::item { padding: 8px 24px; border-radius: 0; }
QMenu::item:selected { background: @ACC@; color: #ffffff; }
QMenu::separator { height: 1px; background: @LINE@; margin: 4px 8px; }
QGroupBox { border: 1px solid @BTN_B@; border-radius: 0; margin-top: 14px; padding: 12px; font-weight: 700; background: @CARD@; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: @MUTED@; }
QStatusBar { background: @BAR@; color: @MUTED@; }
QStatusBar::item { border: none; }
QToolTip { background: @PANEL@; color: @TEXT@; border: 1px solid @LINE2@; padding: 5px; }
QMessageBox { background: @BG@; }
QMessageBox QLabel { color: @TEXT@; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid @LINE2@; background: @INPUT@; border-radius: 2px; }
QCheckBox::indicator:checked { background: @ACC@; border-color: @ACC@; }
"""


def dark_qss() -> str:
    q = _QSS
    for k, v in _PAL.items():
        q = q.replace("@%s@" % k, v)
    return q


def apply_dark_theme(app):
    """Fusion-Stil + PitBoss-Dark-Stylesheet auf die Anwendung anwenden."""
    app.setStyle("Fusion")
    app.setStyleSheet(dark_qss())
