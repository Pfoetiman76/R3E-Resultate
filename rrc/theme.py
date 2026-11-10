"""Dark-Optik fuer RaceRoom Results Companion (RaceRoom-Rot-Akzent, 0.4.3).

Struktur: Reiter oben, Filterzeilen darunter, kompakte Tabellen mit feinen
Gitterlinien (kein Zebra), technische Schrift (Consolas) fuer Zeitwerte,
gelbe Hervorhebung fuer Rekordwerte, Statusleiste unten. Akzentfarbe ist
durchgaengig RaceRoom-Rot #e8212b (aktiver Reiter, Primaer-Button,
Zielauswahl, Statuspunkt).
"""
RR_RED = "#e8212b"
RR_RED_H = "#ff3a45"
RR_RED_D = "#b31b24"
REC_YELLOW = "#e8c34a"

_PAL = {
    "BG": "#131318", "PANEL": "#1a1a20", "PANEL2": "#202027", "INPUT": "#141419",
    "LINE": "#33333d", "LINE2": "#3d3d48", "TEXT": "#e8e8ec", "MUTED": "#9a9aa4",
    "BAR": "#0e0e12", "HOVER": "#22222a", "ACC": RR_RED, "ACC_H": RR_RED_H,
    "ACC_D": RR_RED_D, "SCROLL": "#34343c", "ACC_TXT": "#ff5a63",
    "SEL": "#3a2220", "CARD": "#16161c", "HEAD": "#2a2a32",
    "BTN": "#23232b", "BTN_H": "#2b2b34", "BTN_B": "#33333d",
}

_QSS = """
QWidget { font-family: "Segoe UI", "Inter", "Montserrat", sans-serif; font-size: 13px; color: @TEXT@; }
QMainWindow, QWidget { background: @BG@; }
QLabel { background: transparent; color: @TEXT@; }
QLabel[plain="true"] { background: transparent; }
QLabel#brandTitle { font-size: 19px; font-weight: 800; color: @TEXT@; background: transparent; }
QLabel#brandSub, QLabel#hint, QLabel#statusLine { color: @MUTED@; background: transparent; font-size: 12px; }
QLabel#sectionTitle { font-size: 12px; font-weight: 700; color: @MUTED@; background: transparent; }
QTabWidget::pane { border: none; border-top: 2px solid @LINE@; background: transparent; top: -1px; }
QTabBar { background: @BAR@; }
QTabBar::tab { background: transparent; color: @MUTED@; padding: 8px 16px; margin-right: 2px; border: 1px solid transparent; border-bottom: none; font-weight: 700; }
QTabBar::tab:hover { color: @TEXT@; }
QTabBar::tab:selected { color: @TEXT@; background: @BG@; border-color: @LINE@; border-top: 3px solid @ACC@; padding-top: 5px; }
QPushButton { background: @BTN@; color: @TEXT@; border: 1px solid @BTN_B@; padding: 7px 14px; border-radius: 2px; font-weight: 700; }
QPushButton:hover { border-color: #4a4a55; background: @BTN_H@; }
QPushButton:pressed { background: @BG@; }
QPushButton:disabled { color: @MUTED@; background: @PANEL@; border-color: @LINE@; }
QPushButton#primary { background: @ACC@; color: #ffffff; border: 1px solid @ACC_D@; padding: 8px 18px; }
QPushButton#primary:hover { background: @ACC_H@; border-color: @ACC_H@; }
QPushButton#primary:pressed { background: @ACC_D@; }
QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: @INPUT@; color: @TEXT@; border: 1px solid @LINE@; border-radius: 2px; selection-background-color: @ACC@; selection-color: #ffffff; }
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid @ACC_D@; }
QDateEdit, QTimeEdit { background: @INPUT@; color: #ffffff; border: 1px solid @LINE@; border-radius: 2px; padding: 3px 10px; selection-background-color: @ACC@; selection-color: #ffffff; }
QDateEdit:focus, QTimeEdit:focus { border: 1px solid @ACC_D@; }
QDateEdit::up-button, QDateEdit::down-button, QTimeEdit::up-button, QTimeEdit::down-button { background: @PANEL2@; border: none; width: 18px; }
QDateEdit::up-button:hover, QDateEdit::down-button:hover, QTimeEdit::up-button:hover, QTimeEdit::down-button:hover { background: @ACC@; }
QCalendarWidget { background: @PANEL@; }
QCalendarWidget #qt_calendar_navigationbar { background: @HEAD@; }
QCalendarWidget #qt_calendar_prevbutton, QCalendarWidget #qt_calendar_nextbutton { background: transparent; }
QCalendarWidget #qt_calendar_monthbutton, QCalendarWidget #qt_calendar_yearbutton { background: transparent; color: @TEXT@; }
QCalendarWidget #qt_calendar_calendarview { background: @PANEL@; color: #ffffff; alternate-background-color: @PANEL2@; selection-background-color: @SEL@; selection-color: #ff5a63; }
QComboBox { padding: 3px 30px 3px 10px; min-height: 28px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: right center; width: 26px; border: none; border-left: 1px solid @LINE@; background: @PANEL2@; }
QComboBox::drop-down:hover { background: @ACC@; }
QComboBox::down-arrow { image: none; width: 1px; }
QComboBox QAbstractItemView { background: @PANEL@; color: @TEXT@; selection-background-color: @ACC@; selection-color: #ffffff; outline: 0; border: 1px solid @LINE2@; padding: 2px; }
QTableView, QTableWidget { background: @PANEL@; color: @TEXT@; gridline-color: @LINE@; border: 1px solid @LINE@; border-radius: 0; selection-background-color: @SEL@; selection-color: @TEXT@; }
QTableView::item, QTableWidget::item { padding: 4px 10px; border: 0; }
QTableView::item:hover, QTableWidget::item:hover { background: @HOVER@; }
QTableView::item:selected, QTableWidget::item:selected { background: @SEL@; color: @TEXT@; }
QHeaderView::section { background: @HEAD@; color: @TEXT@; padding: 6px 10px; border: none; border-right: 1px solid @LINE@; border-bottom: 1px solid @LINE@; font-size: 11.5px; font-weight: 700; }
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
QStatusBar QLabel { color: @MUTED@; }
QToolTip { background: @PANEL@; color: @TEXT@; border: 1px solid @LINE2@; padding: 5px; }
QMessageBox { background: @BG@; }
QMessageBox QLabel { color: @TEXT@; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid @LINE2@; background: @INPUT@; border-radius: 2px; }
QCheckBox::indicator:checked { background: @ACC@; border-color: @ACC@; }
QDialog { background: @BG@; }
"""


def dark_qss() -> str:
    q = _QSS
    for k, v in _PAL.items():
        q = q.replace("@%s@" % k, v)
    return q


def apply_dark_theme(app):
    """Fusion-Stil + Dark-Stylesheet auf die Anwendung anwenden."""
    app.setStyle("Fusion")
    app.setStyleSheet(dark_qss())
