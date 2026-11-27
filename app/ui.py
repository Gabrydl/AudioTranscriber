"""PySide6 user interface: main window (live feed) + in-game overlay."""
from __future__ import annotations

import datetime as dt
import logging
import threading
import sys
import time
from pathlib import Path

from PySide6.QtCore import (Qt, QObject, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRectF,
                            QPointF, QFileInfo, QSize, QAbstractAnimation, QEvent)
from PySide6.QtGui import (QColor, QPainter, QLinearGradient, QBrush, QPen, QIcon, QPixmap, QFont,
                           QAction)
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QToolButton, QHBoxLayout,
                               QVBoxLayout, QGridLayout, QScrollArea, QComboBox, QCheckBox, QSlider,
                               QSizeGrip, QGraphicsOpacityEffect, QFileIconProvider, QSystemTrayIcon,
                               QMenu, QApplication, QSizePolicy, QMessageBox, QProgressBar, QInputDialog,
                               QPlainTextEdit, QAbstractSpinBox, QListWidget, QListWidgetItem,
                               QAbstractItemView, QLineEdit)
from PySide6.QtGui import QKeySequence, QShortcut
import html as _html
import re as _re

from .config import (Settings, LANGUAGES, WHISPER_MODELS, COMPUTE_MODES, TRANSCRIPTS_DIR, ROOT)
from .audio import list_audio_apps, AppCapture, AppInfo, default_output_id
from .engine import Engine, Line
from .sysinfo import ResourceMonitor, GlobalHotkeys, set_start_with_windows, keep_on_top
from .speakers import SpeakerRegistry
from . import i18n
from .i18n import tr

log = logging.getLogger("ui")

# ----------------------------------------------------------------------------- palette (Carbon Pro)
# matte black, sharp corners, colour only on the main buttons
BG, SURF, SURF2, BORDER = "#0b0b0c", "#121214", "#18181b", "#232327"
RAIL, LINE = "#070708", "#1a1a1d"
TEXT, MUTED, DIM = "#f2f2f3", "#8d8d95", "#63636b"
ACCENT, ACCENT_HI = "#e5484d", "#f2585d"
VIOLET, CYAN, GREEN, AMBER, RED = ACCENT, "#22d3ee", "#c3d1b2", "#dcc79b", "#e5484d"
LANG_COL = {}          # neutral badges (no bright colours outside buttons)
SPK_COL = ["#c3d1b2", "#dcc79b", "#d6b1a7", "#c2b4d2", "#a9c7c7", "#cfcf9e", "#d3b3c3", "#b3c2a3"]
HEAD_FONT = "'Segoe UI Variable Display', 'Segoe UI Semibold', 'Segoe UI', sans-serif"


def spk_color(sid) -> str:
    return SPK_COL[(sid - 1) % len(SPK_COL)] if sid else MUTED


def tint(hex_col: str, amount: float = 0.16, base: str = BG) -> str:
    """hex_col mixed into the background (dark coloured squares behind initials)."""
    a = [int(hex_col[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(base[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(y + (x - y) * amount) for x, y in zip(a, b))


BADGE_FG = "#c8c8ce"

QSS = f"""
* {{ font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; color: {TEXT}; }}
#root {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
#rail {{ background: {RAIL}; border-right: 1px solid {LINE}; border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QToolButton#railbtn {{ background: transparent; border: none; border-radius: 4px; padding: 0; }}
QToolButton#railbtn:hover {{ background: #141416; }}
QToolButton#railbtn:checked {{ background: #1c1c1f; }}
#titlebar {{ background: transparent; }}
#title {{ font-family: {HEAD_FONT}; font-size: 21px; font-weight: 800; }}
#subtitle {{ color: {MUTED}; font-size: 12px; }}
QToolButton#winbtn {{ background: transparent; border: none; border-radius: 4px; padding: 4px 10px; color: {MUTED}; font-size: 14px; }}
QToolButton#winbtn:hover {{ background: {SURF2}; color: {TEXT}; }}
QToolButton#closebtn {{ background: transparent; border: none; border-radius: 4px; padding: 4px 10px; color: {MUTED}; font-size: 14px; }}
QToolButton#closebtn:hover {{ background: {ACCENT}; color: white; }}
#chip {{ background: {SURF}; border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 9px; color: {MUTED}; font-size: 11px; }}
#panel {{ background: {SURF}; border: 1px solid {LINE}; border-radius: 4px; }}
#side {{ background: transparent; border-left: 1px solid {LINE}; }}
#tile {{ background: {SURF}; border: 1px solid {LINE}; border-radius: 4px; }}
#tilelab {{ color: {MUTED}; font-size: 11px; }}
#tileval {{ font-family: {HEAD_FONT}; font-size: 19px; font-weight: 700; }}
#hsep {{ background: {LINE}; }}
QToolButton#app {{ background: {SURF}; border: 1px solid {BORDER}; border-radius: 4px; padding: 5px 11px 5px 7px; font-size: 12px; color: {MUTED}; }}
QToolButton#app:hover {{ border-color: #3a3a40; color: {TEXT}; }}
QToolButton#app:checked {{ background: #1c1c1f; border: 1px solid #5a5a62; color: {TEXT}; }}
QPushButton#start {{ border: none; border-radius: 4px; padding: 10px 24px; font-size: 14px; font-weight: 700; color: white;
   background: {ACCENT}; }}
QPushButton#start:hover {{ background: {ACCENT_HI}; }}
QPushButton#start:disabled {{ background: #3a2224; color: #9a8a8b; }}
QPushButton#start[running="true"] {{ background: {ACCENT}; }}
QPushButton#ghost, QToolButton#ghost {{ background: {SURF}; border: 1px solid {BORDER}; border-radius: 4px; padding: 9px 14px; font-size: 13px; font-weight: 600; color: {TEXT}; }}
QPushButton#ghost:hover, QToolButton#ghost:hover {{ border-color: #4a4a52; }}
QPushButton#ghost:checked, QToolButton#ghost:checked {{ border-color: #6a6a72; background: #1f1f23; }}
QPushButton#ghost:disabled {{ color: {DIM}; }}
#card {{ background: {SURF}; border: 1px solid {LINE}; border-radius: 4px; }}
#card[estimated="true"] {{ border: 1px solid #2f2b22; }}
#card[live="true"] {{ background: #161618; border: 1px solid #2c2c31; }}
#orig {{ color: {MUTED}; font-size: 12px; }}
#tr_it {{ font-size: 17px; font-weight: 600; }}
#tr_en {{ font-size: 14px; color: #bdbdc4; }}
#tag {{ color: {DIM}; font-size: 10px; font-weight: 800; letter-spacing: 1px; }}
#meta {{ color: {MUTED}; font-size: 11px; }}
#est {{ background: transparent; color: #d6c493; border: 1px solid #4a4230; border-radius: 3px; padding: 0 6px; font-size: 9px; font-weight: 800; letter-spacing: .5px; }}
#pending {{ color: {DIM}; font-size: 13px; font-style: italic; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px 2px 2px 0; }}
QScrollBar::handle:vertical {{ background: #3a3a40; border-radius: 3px; min-height: 40px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: #55555c; }}
QScrollBar::handle:vertical:pressed {{ background: #75757c; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
#status {{ color: {MUTED}; font-size: 11px; }}
#sectiontitle {{ color: {MUTED}; font-size: 11px; font-weight: 800; letter-spacing: 1.2px; }}
QComboBox {{ background: {SURF2}; border: 1px solid {BORDER}; border-radius: 4px; padding: 6px 10px; font-size: 12px; }}
QComboBox QAbstractItemView {{ background: {SURF2}; border: 1px solid {BORDER}; selection-background-color: #2e2e33; outline: none; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QCheckBox {{ font-size: 12px; spacing: 7px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid {BORDER}; background: {SURF2}; }}
QCheckBox::indicator:checked {{ background: #e4e4e7; border-color: #e4e4e7; image: url(CHECK_PNG); }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: #8a8a92; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; background: white; }}
QToolTip {{ background: {SURF2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; border-radius: 4px; }}
#empty {{ color: {DIM}; font-size: 13px; }}
QMessageBox, QInputDialog, QDialog {{ background: {SURF}; }}
QMessageBox QLabel, QInputDialog QLabel {{ color: {TEXT}; font-size: 13px; }}
QMessageBox QPushButton, QInputDialog QPushButton {{ background: {SURF2}; border: 1px solid {BORDER}; border-radius: 4px; padding: 6px 16px; color: {TEXT}; min-width: 60px; }}
QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {{ border-color: #5a5a62; }}
QLineEdit {{ background: {SURF2}; border: 1px solid {BORDER}; border-radius: 4px; padding: 6px 8px; color: {TEXT}; }}
QMenu {{ background: {SURF}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 3px; color: {TEXT}; }}
QMenu::item:selected {{ background: #2a2a2f; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QProgressBar {{ background: {SURF2}; border: none; border-radius: 0; }}
QProgressBar::chunk {{ background: {ACCENT}; }}

QPlainTextEdit {{ background: {SURF2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 4px; padding: 6px 8px;
  selection-background-color: #3a3a40; font-size: 13px; }}
QPlainTextEdit:focus {{ border-color: #5a5a62; }}
#catcol {{ background: transparent; border-right: 1px solid {LINE}; }}
QPushButton#catbtn {{ background: transparent; border: none; border-radius: 4px; padding: 10px 12px; text-align: left;
   font-size: 14px; font-weight: 600; color: #b5b5bb; }}
QPushButton#catbtn:hover {{ background: #141416; color: {TEXT}; }}
QPushButton#catbtn:checked {{ background: #1c1c1f; color: {TEXT}; font-weight: 700; border-left: 2px solid {ACCENT}; }}
#setcard {{ background: {SURF}; border: 1px solid #1d1d20; border-radius: 4px; }}
#cardtitle {{ font-size: 14px; font-weight: 700; }}
#pagetitle {{ font-family: {HEAD_FONT}; font-size: 18px; font-weight: 800; }}
QPushButton#advbtn {{ background: transparent; border: none; text-align: left; padding: 8px 0; font-size: 13px; color: #b5b5bb; }}
QPushButton#advbtn:hover {{ color: {TEXT}; }}
"""


def app_icon(size: int = 256) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#f2f2f3"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * .12, size * .12)
    p.setPen(QPen(QColor("#0b0b0c"), size * .085, Qt.SolidLine, Qt.RoundCap))
    bars = [.22, .5, .78, .42, .6, .26]
    w = size / (len(bars) + 2)
    for i, h in enumerate(bars):
        x = w * (i + 1.5)
        p.drawLine(QPointF(x, size / 2 - h * size * .3), QPointF(x, size / 2 + h * size * .3))
    p.end()
    return QIcon(pm)


def rail_icon(kind: str, color: str = "#8d8d95", size: int = 40) -> QIcon:
    """Simple line icons for the left rail (drawn here: no icon files needed)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    k = size / 18.0
    pen = QPen(QColor(color), 1.5 * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    P = lambda x, y: QPointF(x * k, y * k)       # noqa: E731
    if kind == "live":
        p.drawEllipse(P(9, 9), 7 * k, 7 * k)
        p.setBrush(QColor(color))
        p.drawEllipse(P(9, 9), 2.6 * k, 2.6 * k)
    elif kind == "people":
        p.drawEllipse(P(7, 6), 3 * k, 3 * k)
        p.drawArc(QRectF(1.5 * k, 11 * k, 11 * k, 9 * k), 0, 180 * 16)
        p.drawArc(QRectF(9.5 * k, 2.8 * k, 5 * k, 5.6 * k), -90 * 16, 180 * 16)
        p.drawArc(QRectF(11 * k, 11.5 * k, 6 * k, 8 * k), 0, 90 * 16)
    elif kind == "words":
        p.drawPolyline([P(3, 2.5), P(12, 2.5), P(15, 5.5), P(15, 15.5), P(3, 15.5), P(3, 2.5)])
        for y in (7.5, 10.5):
            p.drawLine(P(6, y), P(12, y))
        p.drawLine(P(6, 13.5), P(10, 13.5))
    elif kind == "overlay":
        p.drawRect(QRectF(1.5 * k, 3 * k, 15 * k, 11 * k))
        p.setBrush(QColor(color))
        p.drawRect(QRectF(4 * k, 9 * k, 7 * k, 2.5 * k))
    elif kind in ("lock", "unlock"):
        p.drawRoundedRect(QRectF(3.5 * k, 8 * k, 11 * k, 8 * k), 1.5 * k, 1.5 * k)
        if kind == "lock":
            p.drawArc(QRectF(5.5 * k, 2.5 * k, 7 * k, 10 * k), 0, 180 * 16)
        else:
            p.drawArc(QRectF(5.5 * k, 1.5 * k, 7 * k, 9 * k), 30 * 16, 150 * 16)
    elif kind == "settings":
        p.drawEllipse(P(9, 9), 2.6 * k, 2.6 * k)
        import math
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(P(9 + 4.6 * math.cos(a), 9 + 4.6 * math.sin(a)), P(9 + 7 * math.cos(a), 9 + 7 * math.sin(a)))
    elif kind == "clear":
        p.drawLine(P(3, 4.5), P(15, 4.5))
        p.drawPolyline([P(4.5, 4.5), P(5.5, 15.5), P(12.5, 15.5), P(13.5, 4.5)])
        p.drawPolyline([P(7, 4.5), P(7.5, 2.5), P(10.5, 2.5), P(11, 4.5)])
    p.end()
    return QIcon(pm)


def _check_png() -> str:
    """Small dark check mark for checked checkboxes (generated once into assets/)."""
    from .config import ROOT
    path = ROOT / "assets" / "check.png"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#151517"), 4.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(8, 16.5), QPointF(13.5, 22), QPointF(24, 10)])
        p.end()
        pm.save(str(path))
    return path.as_posix()


# ----------------------------------------------------------------------------- thread bridge
class Bridge(QObject):
    status = Signal(str, str)
    line = Signal(object)
    update = Signal(object)
    metrics = Signal(str, int)
    level = Signal(str, float, bool, float)
    ready = Signal(object)
    captures = Signal(object, object, object)
    toggle_overlay = Signal()
    toggle_lock = Signal()
    toggle_run = Signal()
    toggle_pause = Signal()
    copy_last = Signal()
    discord_status = Signal(str)
    discord_members = Signal()
    discord_connected = Signal(object)


# ----------------------------------------------------------------------------- level meter
class LevelMeter(QWidget):
    """Live waveform of the app's volume (newest on the right). The white line is the speech threshold:
    drag it up or down; sound above it counts as speech."""
    thresholdChanged = Signal(float)
    LO, HI = -75.0, -5.0
    BAR, GAP = 3, 3

    def __init__(self, threshold: float):
        super().__init__()
        self.setFixedHeight(44)
        self.setMinimumWidth(160)
        self.setCursor(Qt.SizeVerCursor)
        self.level = self.LO
        self.peak = self.LO
        self.speaking = False
        self.threshold = threshold
        self.hist: list[tuple[float, bool]] = []
        self.setToolTip(tr("Live volume of the selected app.\nDrag the white line up or down: sound above it counts as speech."))
        t = QTimer(self)
        t.timeout.connect(self._decay)
        t.start(50)

    def _y(self, db, h):
        f = (min(max(db, self.LO), self.HI) - self.LO) / (self.HI - self.LO)
        return h - 4 - f * (h - 8)

    def set_level(self, db, speaking):
        self.level = max(db, self.level * 0.6 + db * 0.4) if db > self.level else self.level
        self.peak = max(self.peak, db)
        self.speaking = speaking

    def _decay(self):
        n = max(8, self.width() // (self.BAR + self.GAP))
        self.hist = (self.hist + [(self.level, self.speaking)])[-n:]
        self.level = max(self.level - 2.0, self.LO)
        self.peak = max(self.peak - 0.5, self.level)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        mid = h / 2
        p.setPen(Qt.NoPen)
        x = w - self.BAR
        for db, sp in reversed(self.hist):
            f = (min(max(db, self.LO), self.HI) - self.LO) / (self.HI - self.LO)
            bh = max(3.0, f * (h - 6))
            above = db > self.threshold
            p.setBrush(QColor("#f2f2f3" if (sp or above) else "#3a3a40"))
            p.drawRoundedRect(QRectF(x, mid - bh / 2, self.BAR, bh), 1, 1)
            x -= self.BAR + self.GAP
            if x < 0:
                break
        # threshold: where a bar of that volume would reach (top half), drawn as a thin line
        f = (min(max(self.threshold, self.LO), self.HI) - self.LO) / (self.HI - self.LO)
        ty = mid - max(3.0, f * (h - 6)) / 2
        p.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.DashLine))
        p.drawLine(QPointF(0, ty), QPointF(w, ty))
        p.setPen(QColor(TEXT if self.speaking else MUTED))
        fnt = QFont(self.font())
        fnt.setPointSizeF(7.5)
        fnt.setBold(True)
        p.setFont(fnt)
        label = tr("SPEECH") if self.speaking else f"{self.threshold:.0f} dB"
        p.fillRect(QRectF(0, ty - 7, 46, 14), QColor(BG))
        p.drawText(QRectF(2, ty - 7, 46, 14), Qt.AlignLeft | Qt.AlignVCenter, label)

    def _set_from_y(self, y):
        h = self.height()
        mid = h / 2
        f = max(0.0, min(1.0, (mid - y) * 2 / max(1.0, h - 6)))
        self.threshold = round(self.LO + f * (self.HI - self.LO), 1)
        self.thresholdChanged.emit(self.threshold)
        self.update()

    def mousePressEvent(self, e):
        self._set_from_y(e.position().y())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._set_from_y(e.position().y())


# ----------------------------------------------------------------------------- feed card
def unsure_html(marked: str) -> str:
    """'word(?)' -> the word in grey (the recogniser wasn't sure about it)."""
    out = []
    for w in marked.split():
        if w.endswith("(?)") and len(w) > 3:
            out.append(f"<span style='color:{DIM}' title='{tr("not sure")}'>{_html.escape(w[:-3])}</span>")
        else:
            out.append(_html.escape(w))
    return " ".join(out)


class Card(QFrame):
    """One sentence: initial square | name · language · time | translation (big) | what was heard (small)."""
    mark_unsure = True

    def __init__(self, line: Line, show_original: bool, on_speaker=None):
        super().__init__()
        self.on_speaker = on_speaker
        self.setObjectName("card")
        self.line = line
        self.show_original = show_original
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(14)

        self.avatar = QToolButton()
        self.avatar.setFixedSize(36, 36)
        self.avatar.setCursor(Qt.PointingHandCursor)
        self.avatar.clicked.connect(lambda: self.on_speaker and self.line.speaker_id is not None and self.on_speaker(self))
        outer.addWidget(self.avatar, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(4)
        outer.addLayout(col, 1)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.spk = QToolButton()
        self.spk.setCursor(Qt.PointingHandCursor)
        self.spk.setToolTip(tr("Who said this – click to rename or correct"))
        self.spk.clicked.connect(lambda: self.on_speaker and self.on_speaker(self))
        self.spk.hide()
        head.addWidget(self.spk)
        self.meta = QLabel()
        self.meta.setObjectName("meta")
        head.addWidget(self.meta)
        self.est = QLabel(tr("GUESSED FROM CONTEXT"))
        self.est.setObjectName("est")
        self.est.setFixedHeight(16)
        self.est.hide()
        head.addWidget(self.est)
        head.addStretch(1)
        self.when = QLabel()                         # time stamp of the sentence
        self.when.setObjectName("meta")
        head.addWidget(self.when)
        self.conf = QLabel()
        head.addWidget(self.conf)
        col.addLayout(head)

        self.tr_tag = QLabel()                      # kept for compatibility (target language), not shown
        self.tr_tag.hide()
        self.tr_txt = QLabel()
        self.tr_txt.setObjectName("tr_it")
        self.tr_txt.setWordWrap(True)
        self.tr_txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.tr_txt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        col.addWidget(self.tr_txt)

        self.orig = QLabel()
        self.orig.setObjectName("orig")
        self.orig.setWordWrap(True)
        self.orig.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.orig.setVisible(show_original)
        col.addWidget(self.orig)
        self.pending = QLabel(tr("translating…"))
        self.pending.setObjectName("pending")
        col.addWidget(self.pending)
        self.refresh()

        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        self._anim = QPropertyAnimation(eff, b"opacity", self)
        self._anim.setDuration(240)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(lambda: self.setGraphicsEffect(None))
        self._anim.start()

    def refresh(self):
        l = self.line
        if l.speaker_id is not None:
            col = spk_color(l.speaker_id)
            name = l.speaker_name or "?"
            self.avatar.setText((name.strip()[:1] or "?").upper())
            self.avatar.setStyleSheet(
                f"QToolButton {{ background: {tint(col, .2)}; color: {col}; border: none; border-radius: 4px;"
                f" font-family: {HEAD_FONT}; font-size: 15px; font-weight: 800; }}"
                f"QToolButton:hover {{ background: {tint(col, .26)}; }}")
            self.avatar.setToolTip(tr("{name} – click to rename or correct").format(name=name))
            self.spk.setText(f"{name}{'  ?' if l.speaker_unsure else ''}")
            self.spk.setStyleSheet(
                f"QToolButton {{ background: transparent; color: {TEXT}; border: none; padding: 0;"
                f" font-size: 13px; font-weight: 700; }} QToolButton:hover {{ color: {col}; }}")
            self.spk.setToolTip(tr("Voice match {p}%").format(p=f"{l.speaker_score * 100:.0f}") + (" – " + tr("not sure") if l.speaker_unsure else "")
                                + "\n" + tr("Click to rename or correct"))
            self.spk.show()
        else:
            self.avatar.setText(l.lang.upper()[:2])
            self.avatar.setStyleSheet(
                f"QToolButton {{ background: {SURF2}; color: {MUTED}; border: none; border-radius: 4px;"
                f" font-size: 11px; font-weight: 800; }}")
            self.avatar.setToolTip("")
            self.spk.hide()
        lat = f" · {(l.asr_ms + l.llm_wait_ms + (l.llm_first_ms or l.llm_ms)) / 1000:.1f}s" if (l.llm_first_ms or l.llm_ms) else ""
        self.meta.setText(f"{lname(l.lang)}{lat}")
        self.when.setText(dt.datetime.fromtimestamp(l.t).strftime("%H:%M:%S"))
        S = lambda ms: f"{ms / 1000:.1f}s"          # noqa: E731
        via = (" (" + tr("online") + ")") if l.via == "online" else (" (" + tr("graphics card") + ")") if l.via == "local" else ""
        tip = (f"{l.source.rsplit('.', 1)[0]} · " + tr("said at {t}").format(t=dt.datetime.fromtimestamp(l.t).strftime("%H:%M:%S")) +
               "\n" + tr("Waited {q} · recognition {w} · voices +{v}").format(q=S(l.q_ms), w=S(l.whisper_ms), v=S(l.voice_ms)) +
               "\n" + tr("Translator") + via + ": " +
               tr("waited {a} · first words {b} · done {c}").format(a=S(l.llm_wait_ms), b=S(l.llm_first_ms), c=S(l.llm_ms)))
        self.meta.setToolTip(tip)
        self.when.setToolTip(tip)
        c = l.confidence
        dot = "#8c8c94" if c > .62 else "#6a6a72" if c > .42 else "#4a4a50"
        self.conf.setText(f"<span style='color:{dot};font-size:12px'>●</span>")
        self.conf.setToolTip(tr("Recognition confidence {p}%").format(p=f"{c * 100:.0f}"))

        shown = l.corrected or l.text
        if self.mark_unsure and l.marked and "(?)" in l.marked and (not l.corrected or l.corrected.strip().lower() == l.text.strip().lower()):
            # heard text as it is, with the words Whisper wasn't sure about in grey
            self.orig.setTextFormat(Qt.RichText)
            self.orig.setText(unsure_html(l.marked))
        else:
            self.orig.setTextFormat(Qt.PlainText)
            self.orig.setText(shown)
        if l.estimated and l.corrected:
            self.orig.setToolTip(tr("Heard: “{text}”").format(text=l.text))
        elif l.marked and "(?)" in l.marked:
            self.orig.setToolTip(tr("Grey words: the recogniser wasn't sure about them"))
        self.est.setVisible(l.estimated)
        self.setProperty("estimated", "true" if l.estimated else "false")
        self.setProperty("live", "true" if l.state in ("transcribed", "streaming") else "false")
        self.style().unpolish(self)
        self.style().polish(self)

        live = l.state in ("streaming", "done")
        k, t = next(((k, v) for k, v in l.tr.items() if v), ("", "")) if live else ("", "")
        self.tr_txt.setText(t + (" …" if l.state == "streaming" else ""))
        self.tr_tag.setText(k.upper())
        self.tr_txt.setVisible(bool(t))
        if l.state == "llm-off":
            self.pending.setText(tr("translation unavailable – is Ollama running?"))
        self.pending.setVisible(l.state == "llm-off" or (l.state in ("transcribed", "streaming") and not any(l.tr.values())))
        # while waiting for the translation always show the heard text
        self.orig.setVisible(self.show_original or l.state != "done")


# translator models in the "AI" menu, light -> heavy
LLM_CHOICES = {
    "qwen2.5:3b": "Light – qwen2.5:3b · ~2.5 GB graphics memory · fastest",
    "gemma3:4b": "Medium – gemma3:4b · ~4 GB graphics memory · fast, good",
    "gemma3:12b": "Heavy – gemma3:12b · ~8 GB graphics memory · best, 10–20 s on 8 GB cards",
}
def lname(code: str) -> str:
    """Language name in the interface language."""
    return tr(LANGUAGES.get(code, code))


LLM_SHORT = {"qwen2.5:3b": "Light", "gemma3:4b": "Medium", "gemma3:12b": "Heavy"}

# translation languages shown in the → menu (native names)
TARGETS = {"en": "English", "it": "Italiano", "pt": "Português", "es": "Español", "de": "Deutsch",
           "fr": "Français", "tl": "Tagalog", "cs": "Čeština", "pl": "Polski", "ceb": "Bisaya",
           "fi": "Suomi", "et": "Eesti", "sr": "Српски", "hr": "Hrvatski", "cnr": "Crnogorski",
           "bs": "Bosanski", "bg": "Български", "ru": "Русский", "el": "Ελληνικά"}


# ----------------------------------------------------------------------------- overlay
class Overlay(QWidget):
    def __init__(self, settings: Settings):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.s = settings
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle("AudioTranscriber overlay")
        x, y, w, h = settings.overlay_geometry
        self.setGeometry(x, y, w, h)
        self.setMinimumSize(320, 120)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 14)
        lay.setSpacing(8)
        # drag bar (shown while unlocked): grab here – or anywhere on the box – to move it
        self.hint = QWidget()
        hb = QHBoxLayout(self.hint)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(8)
        handle = QLabel("⠿  " + tr("Drag to move · corner to resize"))
        handle.setStyleSheet(f"color:{TEXT};font-size:11px;font-weight:700;")
        handle.setCursor(Qt.SizeAllCursor)
        hb.addWidget(handle, 1)
        self.lock_now = QPushButton(tr("Lock"))
        self.lock_now.setCursor(Qt.PointingHandCursor)
        self.lock_now.setToolTip(tr("Lock: clicks go through to the game (Ctrl+Alt+L)"))
        self.lock_now.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: white; border: none; border-radius: 3px;"
                                    f" padding: 3px 12px; font-size: 11px; font-weight: 700; }}"
                                    f"QPushButton:hover {{ background: {ACCENT_HI}; }}")
        self.lock_now.clicked.connect(lambda: self.set_locked(True))
        hb.addWidget(self.lock_now)
        lay.addWidget(self.hint)
        # one text area for all phrases: newest at the bottom, oldest dropped when the window is full
        # (separate boxes per phrase got squeezed and drew over each other)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.RichText)
        self.text.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.text.setStyleSheet("background: transparent;")
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        lay.addWidget(self.text, 1)
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.lines: list[Line] = []
        self._drag = None
        self._temp_unlock = False
        self._last_new = time.time()
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(600)
        self._quiet_timer = QTimer(self)
        self._quiet_timer.timeout.connect(self._tick)
        self._quiet_timer.start(1000)
        self.set_locked(settings.overlay_locked)

    def _tick(self):
        if not self.isVisible():
            return
        keep_on_top(self)                    # games in borderless/windowed mode can cover it otherwise
        hide_after = int(self.s.overlay_autohide_s or 0)
        # fades only after real silence: nothing new AND nothing still being translated
        busy = any(l.state in ("transcribed", "streaming") for l in self.lines[-2:])
        quiet = (hide_after > 0 and self.s.overlay_locked and not busy and self._drag is None
                 and time.time() - self._last_new > hide_after)
        target = 0.0 if quiet else 1.0
        if abs(self.windowOpacity() - target) > 0.01 and self._fade.state() != QAbstractAnimation.State.Running:
            self._fade.setStartValue(self.windowOpacity())
            self._fade.setEndValue(target)
            self._fade.start()

    def wake(self):
        self._last_new = time.time()
        if self.windowOpacity() < 0.99:
            self._fade.stop()
            self.setWindowOpacity(1.0)

    def move_mode(self):
        """'Move overlay' button: unlock for a moment; it locks again by itself after you drop it."""
        was_locked = self.s.overlay_locked
        if not self.isVisible():
            self.show()
        self.set_locked(False)
        self._temp_unlock = was_locked
        self.wake()
        self.raise_()

    def set_locked(self, locked: bool):
        self._temp_unlock = False if locked else self._temp_unlock
        self.s.overlay_locked = locked
        self.hint.setVisible(not locked)
        self.grip.setVisible(not locked)
        if sys.platform == "win32":
            # Qt can't reliably REMOVE "clicks go through" on Windows once set (the box stayed unclickable
            # after unlocking): switch the window's click-through style directly
            self._apply_click_through()
        else:
            vis = self.isVisible()
            self.setWindowFlag(Qt.WindowTransparentForInput, locked)
            if vis:
                self.show()
        self.update()

    def _apply_click_through(self):
        try:
            import ctypes
            u = ctypes.windll.user32
            hwnd = int(self.winId())
            GWL_EXSTYLE, WS_EX_TRANSPARENT, WS_EX_LAYERED = -20, 0x20, 0x80000
            ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex = (ex | WS_EX_TRANSPARENT | WS_EX_LAYERED) if self.s.overlay_locked else (ex & ~WS_EX_TRANSPARENT)
            u.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
            u.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0010 | 0x0020)  # refresh frame
        except Exception:
            log.exception("overlay click-through")

    def showEvent(self, e):
        super().showEvent(e)
        if sys.platform == "win32":
            QTimer.singleShot(0, self._apply_click_through)   # the window handle exists now

    def resizeEvent(self, e):
        self.grip.move(self.width() - 18, self.height() - 18)
        self._save_geo()
        QTimer.singleShot(0, self.render_lines)       # refit the phrases to the new size

    def moveEvent(self, e):
        self._save_geo()

    def _save_geo(self):
        g = self.geometry()
        self.s.overlay_geometry = [g.x(), g.y(), g.width(), g.height()]

    # dragging: done by hand (works from anywhere on the box, also where the system move doesn't)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.s.overlay_locked:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.wake()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            self._save_geo()
            self.s.save()
            if self._temp_unlock:                     # opened with "Move overlay": lock again after the drop
                QTimer.singleShot(2500, lambda: self._temp_unlock and self._drag is None and self.set_locked(True))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        a = int(255 * self.s.overlay_opacity)
        p.setBrush(QColor(11, 11, 12, a))
        pen = QPen(QColor(120, 120, 128, 160 if not self.s.overlay_locked else 40), 1.0)
        p.setPen(pen)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 6, 6)

    def push(self, line: Line):
        if line.state == "skipped":
            self.lines = [l for l in self.lines if l.id != line.id]
        elif not any(l.id == line.id for l in self.lines):
            if self.lines and line.id < self.lines[-1].id:
                return                          # an older line being updated (e.g. speaker fixed): don't bring it back
            self.lines.append(line)
            self.wake()
        elif line.state in ("streaming", "done"):
            self.wake()                                # its translation arrived: keep it visible
        self.lines = self.lines[-self.s.overlay_lines:]
        self.render_lines()

    def _line_html(self, l: Line, fade: float) -> str:
        fs = self.s.overlay_font
        col = MUTED
        stamp = (f"<span style='color:{DIM};font-size:{fs - 5}px'>{dt.datetime.fromtimestamp(l.t).strftime('%H:%M:%S')}</span>&nbsp; "
                 if getattr(self.s, "overlay_time", True) else "")
        who = stamp + ((f"<span style='color:{spk_color(l.speaker_id)};font-weight:700;font-size:{fs - 3}px'>"
                        f"{_html.escape(l.speaker_name)}{'?' if l.speaker_unsure else ''}</span>&nbsp; ")
                       if l.speaker_id else "")
        lang = f"<span style='color:{col};font-weight:800;font-size:{fs - 4}px'>{l.lang.upper()}</span>&nbsp; "
        trans = next((v for v in l.tr.values() if v), "")
        heard = _html.escape(l.corrected or l.text)
        if l.state in ("done", "streaming") and trans:
            est = f" <span style='color:{MUTED};font-size:{fs - 4}px'>≈</span>" if l.estimated else ""
            orig = (f"<span style='color:{MUTED};font-size:{fs - 3}px;font-style:italic'>{heard}</span><br>"
                    if self.s.overlay_show_original else "")
            body = f"{orig}<span style='font-size:{fs}px;font-weight:600'>{_html.escape(trans)}</span>{est}"
        else:
            body = f"<span style='color:{MUTED};font-size:{fs - 1}px;font-style:italic'>{heard}</span>"
        # older phrases fade towards the background (plain colour codes: Qt's text engine handles them reliably)
        a = max(0.0, min(1.0, fade * float(self.s.overlay_text_opacity or 1)))
        c = "#%02x%02x%02x" % tuple(int(14 + (f - 14) * a) for f in (236, 236, 238))
        return f"<div style='color:{c}; margin-bottom:8px;'>{who}{lang}{body}</div>"

    def render_lines(self):
        lines = list(self.lines)
        avail = max(40, self.text.height() or (self.height() - 40))
        w = max(100, self.text.width() or (self.width() - 36))
        while True:
            n = len(lines)
            html = "".join(self._line_html(l, 0.45 + 0.55 * (i + 1) / n) for i, l in enumerate(lines)) if n else ""
            self.text.setText(html)
            if n <= 1 or self.text.heightForWidth(w) <= avail:
                break
            lines = lines[1:]                 # too tall: drop the oldest phrase, keep the newest
        self.update()


# ----------------------------------------------------------------------------- flags
def flag_pixmap(kind: str, w: int = 30, h: int = 20) -> QPixmap:
    """Small flags drawn here (Windows has no flag emoji). Latin America gets a LATAM badge."""
    import math
    sc = 2                                     # drawn at double size for sharp edges
    pm = QPixmap(w * sc, h * sc)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(sc, sc)
    p.setPen(Qt.NoPen)
    W, H = float(w), float(h)

    def rect(x, y, ww, hh, col):
        p.setBrush(QColor(col))
        p.drawRect(QRectF(x, y, ww, hh))

    def vtri(cols):
        for i, c in enumerate(cols):
            rect(W * i / 3, 0, W / 3 + .5, H, c)

    def htri(cols):
        n = len(cols)
        for i, c in enumerate(cols):
            rect(0, H * i / n, W, H / n + .5, c)

    if kind == "it":
        vtri(("#009246", "#ffffff", "#ce2b37"))
    elif kind == "fr":
        vtri(("#0055a4", "#ffffff", "#ef4135"))
    elif kind == "de":
        htri(("#000000", "#dd0000", "#ffce00"))
    elif kind == "pl":
        htri(("#ffffff", "#dc143c"))
    elif kind == "es":
        rect(0, 0, W, H, "#aa151b")
        rect(0, H / 4, W, H / 2, "#f1bf00")
    elif kind == "pt":
        rect(0, 0, W, H, "#ff0000")
        rect(0, 0, W * .4, H, "#006600")
        p.setBrush(QColor("#ffcc00"))
        p.drawEllipse(QPointF(W * .4, H / 2), H * .2, H * .2)
    elif kind == "br":
        rect(0, 0, W, H, "#009c3b")
        p.setBrush(QColor("#ffdf00"))
        from PySide6.QtGui import QPolygonF
        p.drawPolygon(QPolygonF([QPointF(W / 2, H * .1), QPointF(W * .92, H / 2), QPointF(W / 2, H * .9),
                                 QPointF(W * .08, H / 2)]))
        p.setBrush(QColor("#002776"))
        p.drawEllipse(QPointF(W / 2, H / 2), H * .22, H * .22)
    elif kind == "cz":
        htri(("#ffffff", "#d7141a"))
        p.setBrush(QColor("#11457e"))
        from PySide6.QtGui import QPolygonF
        p.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(W * .5, H / 2), QPointF(0, H)]))
    elif kind == "ph":
        htri(("#0038a8", "#ce1126"))
        from PySide6.QtGui import QPolygonF
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(W * .45, H / 2), QPointF(0, H)]))
        p.setBrush(QColor("#fcd116"))
        p.drawEllipse(QPointF(W * .15, H / 2), H * .12, H * .12)
    elif kind == "gb":
        rect(0, 0, W, H, "#012169")
        p.setPen(QPen(QColor("#ffffff"), H * .2))
        p.drawLine(QPointF(0, 0), QPointF(W, H))
        p.drawLine(QPointF(W, 0), QPointF(0, H))
        p.setPen(QPen(QColor("#c8102e"), H * .08))
        p.drawLine(QPointF(0, 0), QPointF(W, H))
        p.drawLine(QPointF(W, 0), QPointF(0, H))
        p.setPen(Qt.NoPen)
        rect(W / 2 - H * .17, 0, H * .34, H, "#ffffff")
        rect(0, H / 2 - H * .17, W, H * .34, "#ffffff")
        rect(W / 2 - H * .1, 0, H * .2, H, "#c8102e")
        rect(0, H / 2 - H * .1, W, H * .2, "#c8102e")
    elif kind == "fi":
        rect(0, 0, W, H, "#ffffff")
        rect(W * .28, 0, H * .28, H, "#002f6c")
        rect(0, H * .36, W, H * .28, "#002f6c")
    elif kind == "ee":
        htri(("#0072ce", "#000000", "#ffffff"))
    elif kind == "ru":
        htri(("#ffffff", "#0039a6", "#d52b1e"))
    elif kind == "rs":
        htri(("#c6363c", "#0c4076", "#ffffff"))
        p.setBrush(QColor("#c6363c"))
        p.drawRoundedRect(QRectF(W * .24, H * .22, W * .18, H * .5), 2, 2)
    elif kind == "hr":
        htri(("#ff0000", "#ffffff", "#171796"))
        for i in range(3):                       # the red and white checks of the shield
            for j in range(3):
                rect(W * .4 + i * W * .067, H * .26 + j * H * .1, W * .067, H * .1,
                     "#ff0000" if (i + j) % 2 == 0 else "#ffffff")
    elif kind == "me":
        rect(0, 0, W, H, "#c40308")
        p.setPen(QPen(QColor("#d4af37"), H * .1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(H * .05, H * .05, W - H * .1, H - H * .1))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#d4af37"))
        p.drawEllipse(QPointF(W / 2, H / 2), H * .2, H * .24)
    elif kind == "ba":
        rect(0, 0, W, H, "#002395")
        from PySide6.QtGui import QPolygonF
        p.setBrush(QColor("#fecb00"))
        p.drawPolygon(QPolygonF([QPointF(W * .28, 0), QPointF(W * .72, 0), QPointF(W * .72, H)]))
        p.setBrush(QColor("#ffffff"))
        for i in range(5):
            p.drawEllipse(QPointF(W * (.22 + i * .1), H * (.08 + i * .21)), H * .05, H * .05)
    elif kind == "bg":
        htri(("#ffffff", "#00966e", "#d62612"))
    elif kind == "gr":
        for i in range(9):
            rect(0, H * i / 9, W, H / 9 + .5, "#0d5eaf" if i % 2 == 0 else "#ffffff")
        rect(0, 0, H * 5 / 9, H * 5 / 9, "#0d5eaf")
        rect(H * 2 / 9, 0, H / 9, H * 5 / 9, "#ffffff")
        rect(0, H * 2 / 9, H * 5 / 9, H / 9, "#ffffff")
    elif kind == "latam":
        rect(0, 0, W, H, "#26262b")
        p.setPen(QColor("#f2f2f3"))
        f = QFont("Segoe UI")
        f.setPixelSize(int(H * .42))
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 0, W, H), Qt.AlignCenter, "LATAM")
    else:
        rect(0, 0, W, H, "#3a3a40")
    p.setPen(QPen(QColor(0, 0, 0, 90), .8))
    p.setBrush(Qt.NoBrush)
    p.drawRect(QRectF(.4, .4, W - .8, H - .8))
    p.end()
    pm.setDevicePixelRatio(sc)
    return pm


def flag_icon(code: str) -> QIcon:
    return QIcon(flag_pixmap(i18n.FLAGS.get(code, "")))


# ----------------------------------------------------------------------------- settings page
class _NoWheelUnlessFocused(QObject):
    """Scrolling over Settings must scroll the page, never change a slider or list by accident.
    A control reacts to the wheel only after it was clicked."""
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel and not obj.hasFocus():
            w = obj.parentWidget()
            while w is not None and not isinstance(w, QScrollArea):
                w = w.parentWidget()
            if w is not None:
                QApplication.sendEvent(w.verticalScrollBar(), ev)   # scroll the page instead
            return True
        return False


class StickyMenu(QMenu):
    """A menu whose tick boxes can be clicked one after another without it closing."""
    def mouseReleaseEvent(self, e):
        a = self.activeAction()
        if a is not None and a.isCheckable() and a.isEnabled():
            a.trigger()
            return
        super().mouseReleaseEvent(e)


class SetCard(QFrame):
    """One box on a settings page: bold title, one grey line, then its controls."""
    def __init__(self, title: str, sub: str = ""):
        super().__init__()
        self.setObjectName("setcard")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 15, 18, 16)
        self.lay.setSpacing(9)
        t = QLabel(title)
        t.setObjectName("cardtitle")
        self.lay.addWidget(t)
        if sub:
            s = QLabel(sub)
            s.setObjectName("status")
            s.setWordWrap(True)
            self.lay.addWidget(s)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

    def add(self, *ws):
        for w in ws:
            (self.lay.addLayout if isinstance(w, (QHBoxLayout, QVBoxLayout, QGridLayout)) else self.lay.addWidget)(w)
        return self


class CardGrid(QWidget):
    """Cards in two columns, or one when the window is narrow."""
    def __init__(self):
        super().__init__()
        self.g = QGridLayout(self)
        self.g.setContentsMargins(0, 0, 0, 0)
        self.g.setSpacing(14)
        self.cards: list[QWidget] = []
        self._cols = 0

    def add(self, card):
        self.cards.append(card)
        self._place(force=True)
        return card

    def _place(self, force=False):
        cols = 2 if self.width() >= 640 else 1
        if cols == self._cols and not force:
            return
        self._cols = cols
        for c in self.cards:
            self.g.removeWidget(c)
        col_h = [0] * cols                        # shortest column first, like a masonry wall
        rows = [0] * cols
        for c in self.cards:
            i = col_h.index(min(col_h))
            self.g.addWidget(c, rows[i], i, Qt.AlignTop)
            rows[i] += 1
            col_h[i] += max(1, c.sizeHint().height())
        for i in range(2):
            self.g.setColumnStretch(i, 1 if i < cols else 0)
        self.g.setRowStretch(max(rows) if rows else 0, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place()


class Advanced(QFrame):
    """Folded box at the bottom of a page: the options you rarely change."""
    def __init__(self):
        super().__init__()
        self.setObjectName("setcard")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 6, 18, 6)
        v.setSpacing(8)
        self.btn = QPushButton()
        self.btn.setObjectName("advbtn")
        self.btn.setCheckable(True)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.toggled.connect(self._toggle)
        v.addWidget(self.btn)
        self.body = QWidget()
        self.bl = QVBoxLayout(self.body)
        self.bl.setContentsMargins(0, 4, 0, 10)
        self.bl.setSpacing(9)
        self.body.hide()
        v.addWidget(self.body)
        self.n = 0
        self._toggle(False)

    def add(self, *ws, count=True):
        for w in ws:
            (self.bl.addLayout if isinstance(w, (QHBoxLayout, QVBoxLayout, QGridLayout)) else self.bl.addWidget)(w)
        if count:
            self.n += 1
        self._toggle(self.btn.isChecked())
        return self

    def _toggle(self, on):
        self.body.setVisible(on)
        self.btn.setText(("▾  " if on else "▸  ") + tr("Advanced") +
                         ("" if on or not self.n else "   ·   " + tr("More options: {n}").format(n=self.n)))


class SettingsPanel(QFrame):
    """Settings as a full page: categories on the left, the chosen category's boxes on the right."""
    applyRequested = Signal()
    changed = Signal()
    llmPicked = Signal(str)                  # translator chosen in the list: switch right away
    langPicked = Signal(str)                 # interface language chosen

    CATS = [("rec", "Recognition", "How speech is heard and turned into text"),
            ("tr", "Translation", "Where and how the lines are translated"),
            ("people", "People", "Who is speaking: voices, names, ignored people"),
            ("discord", "Discord", "Names and calls straight from the Discord app"),
            ("view", "Overlay & display", "The live feed and the overlay on top of the game"),
            ("app", "App", "Language, Windows, reliability and updates")]

    def __init__(self, s: Settings):
        super().__init__()
        self.s = s
        self.setObjectName("setpage")
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        # --- category column
        cat = QFrame()
        cat.setObjectName("catcol")
        cat.setFixedWidth(206)
        cl = QVBoxLayout(cat)
        cl.setContentsMargins(0, 4, 14, 6)
        cl.setSpacing(4)
        self.cat_btns = {}
        from PySide6.QtWidgets import QButtonGroup, QStackedWidget
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        self.stack = QStackedWidget()
        self.pages = {}
        for i, (key, name, _sub) in enumerate(self.CATS):
            b = QPushButton(tr(name).replace("&", "&&"))
            b.setObjectName("catbtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            grp.addButton(b, i)
            cl.addWidget(b)
            self.cat_btns[key] = b
        grp.idClicked.connect(self.stack.setCurrentIndex)
        cl.addStretch(1)
        from .version import VERSION
        ver = QLabel(tr("Version {v}").format(v=VERSION) + "\n" + tr("Updates are checked when the app opens."))
        ver.setObjectName("status")
        ver.setWordWrap(True)
        cl.addWidget(ver)
        hl.addWidget(cat)
        hl.addWidget(self.stack, 1)
        self._wheel_guard = _NoWheelUnlessFocused(self)

        def page(key, apply_btn=False):
            name, sub = next((n, s_) for k, n, s_ in self.CATS if k == key)
            sc = QScrollArea()
            sc.setWidgetResizable(True)
            sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            inner = QWidget()
            sc.setWidget(inner)
            v = QVBoxLayout(inner)
            v.setContentsMargins(22, 2, 12, 16)
            v.setSpacing(14)
            head = QHBoxLayout()
            tc = QVBoxLayout()
            tc.setSpacing(2)
            t = QLabel(tr(name))
            t.setObjectName("pagetitle")
            st_ = QLabel(tr(sub))
            st_.setObjectName("status")
            tc.addWidget(t)
            tc.addWidget(st_)
            head.addLayout(tc, 1)
            if apply_btn:
                a = QPushButton(tr("Apply"))
                a.setObjectName("start")
                a.setToolTip(tr("Loads the chosen models (also while running)."))
                a.clicked.connect(self._apply)
                head.addWidget(a, 0, Qt.AlignTop)
            v.addLayout(head)
            grid = CardGrid()
            v.addWidget(grid)
            adv = Advanced()
            v.addWidget(adv)
            v.addStretch(1)
            self.stack.addWidget(sc)
            self.pages[key] = sc
            return grid, adv

        def status(text="", wrap=True):
            l = QLabel(text)
            l.setObjectName("status")
            l.setWordWrap(wrap)
            return l

        def row(*ws, stretch_first=False):
            r = QHBoxLayout()
            r.setSpacing(8)
            for i, w in enumerate(ws):
                r.addWidget(w, 1 if (stretch_first and i == 0) or (not stretch_first) else 0)
            return r

        def ghost(text):
            b = QPushButton(text)
            b.setObjectName("ghost")
            return b

        # ================= Recognition
        g, adv = page("rec", apply_btn=True)
        self.wm = QComboBox()
        for k, v in WHISPER_MODELS.items():             # short label (never cut off), details on hover
            self.wm.addItem(f"{k} — {tr(v.split(' · ')[0])}", k)
            self.wm.setItemData(self.wm.count() - 1, f"{k} — {tr(v)}", Qt.ToolTipRole)
        self.hw = QComboBox()
        for k, v in COMPUTE_MODES.items():
            self.hw.addItem(tr(v), k)
        self.hw.setToolTip(tr("GPU: fastest, the models must fit on the graphics card (if one doesn't, it is split automatically).\n"
                              "Mix: the translator uses the graphics card as far as it fits and the CPU for the rest.\n"
                              "CPU only: works without a graphics card, much slower."))
        g.add(SetCard(tr("Speech model"), tr("Bigger is more accurate, smaller is faster.")).add(
            self.wm, status(tr("Run on")), self.hw))
        lg = QGridLayout()
        lg.setHorizontalSpacing(12)
        lg.setVerticalSpacing(7)
        self.lang_boxes = {}
        for i, (code, name) in enumerate(LANGUAGES.items()):
            cb = QCheckBox(tr(name))
            cb.toggled.connect(self._langs)
            lg.addWidget(cb, i // 2, i % 2)
            self.lang_boxes[code] = cb
        g.add(SetCard(tr("Languages to recognise"), tr("Only the ticked ones are listened for.")).add(lg))
        self.vc = QCheckBox(tr("Voice detector (ignores noise and clicks)"))
        self.vc.setToolTip(tr("A speech detector decides where a sentence starts and ends, not only the volume.\n"
                              "Noisy mics no longer keep a sentence open, clicks don't become fake lines.\n"
                              "Applies from the next Start."))
        self.vc.toggled.connect(lambda v: self._flag("vad_cut", v))
        self.sil_lab = status()
        self.sil = QSlider(Qt.Horizontal)
        self.sil.setRange(300, 1500)
        self.sil.valueChanged.connect(self._sil)
        g.add(SetCard(tr("Sentences"), tr("When a sentence starts and ends.")).add(self.vc, self.sil_lab, self.sil))
        self.vocab = QPlainTextEdit()
        self.vocab.setPlaceholderText(tr("Names, game terms, slang – one per line or separated by commas\n"
                                         "e.g. Gabry, War Thunder, Bismarck, GG"))
        self.vocab.setFixedHeight(84)
        self.vocab.textChanged.connect(self._vocab)
        self.lol = QCheckBox(tr("League of Legends terms"))
        self.lol.setToolTip(tr("Champions, spells, items, runes and slang (Riot's names in every language).\n"
                               "Recognised better, and kept as the English game word in translations:\n"
                               "Flash stays Flash, Hexflash stays Hexflash, \"destello\" becomes Flash."))
        self.lol.toggled.connect(lambda v: self._flag("league_terms", v))
        g.add(SetCard(tr("Words to know"), tr("Used by the recogniser and the translator, so these words come out right.")).add(
            self.vocab, self.lol))
        self.en = QCheckBox(tr("Noise suppression (hum, hiss, bad mics)"))
        self.en.toggled.connect(self._enh)
        self.dng = QCheckBox(tr("Noise removal on the graphics card"))
        self.dng.setToolTip(tr("Cleans very noisy voices on the graphics card; uses the CPU when the card can't."))
        self.dng.toggled.connect(lambda v: self._flag("denoise_gpu", v))
        self.mu = QCheckBox(tr("Show unsure words in grey"))
        self.mu.toggled.connect(self._mu)
        self.fl = QCheckBox(tr("Skip the language check for people whose language is known"))
        self.fl.setToolTip(tr("Faster: once a person's language is certain, the separate language pass is skipped."))
        self.fl.toggled.connect(lambda v: self._flag("fast_lang", v))
        adv.add(self.en).add(self.dng).add(self.mu).add(self.fl)

        # ================= Translation
        g, adv = page("tr", apply_btn=True)
        self.le = QCheckBox(tr("Translate + fix misheard words"))
        self.tr_gpu = QCheckBox(tr("Graphics card – local, works offline"))
        self.tr_on = QCheckBox(tr("Online – Gemini, when internet is on"))
        self.tr_gpu.setToolTip(tr("The translator model runs on your PC (Ollama). Nothing leaves the PC."))
        self.tr_on.setToolTip(tr("Google's Gemini API translates instead: faster and smarter than what fits on an 8 GB card.\n"
                                 "Both ticked: online first, the graphics card takes over when online can't answer\n"
                                 "(no internet, daily free limit reached, too slow)."))
        g.add(SetCard(tr("Where it runs"), tr("Both ticked: online first, the graphics card as backup.")).add(
            self.le, self.tr_gpu, self.tr_on))
        self.lm = QComboBox()
        for k, v in LLM_CHOICES.items():                  # light -> heavy, with graphics memory use
            self.lm.addItem(" · ".join(tr(x) for x in v.split(" · ")[:2]), k)
            self.lm.setItemData(self.lm.count() - 1, tr(v), Qt.ToolTipRole)
        if s.llm_model not in LLM_CHOICES:               # a model chosen by name earlier stays selectable
            self.lm.addItem(s.llm_model, s.llm_model)
        self.lm.setToolTip(tr("Lighter = less graphics memory and faster · heavier = better translations."))
        self.lm.activated.connect(lambda _i: self.llmPicked.emit(self.lm.currentData() or ""))
        self.lm_hint = status(tr("Switches right away, also while running. Missing models are downloaded automatically."))
        self.local_card = g.add(SetCard(tr("Graphics card model"), tr("Runs on this PC with Ollama.")).add(self.lm, self.lm_hint))
        from .online import MODELS as GEM_MODELS
        self.gm = QComboBox()
        for k, (lab_, _n) in GEM_MODELS.items():
            self.gm.addItem(tr(lab_.split(" – ")[0]), k)
            self.gm.setItemData(self.gm.count() - 1, tr(lab_), Qt.ToolTipRole)
        self.gkey = QLineEdit()
        self.gkey.setPlaceholderText(tr("Gemini API key (free)"))
        self.gkey.setEchoMode(QLineEdit.Password)
        self.gkey_help = ghost(tr("Get a free key"))
        self.g_usage = status()
        self.on_box = g.add(SetCard(tr("Online – Gemini"), tr("Google's translator, used when internet is on.")).add(
            self.gm, row(self.gkey, self.gkey_help, stretch_first=True), self.g_usage))
        self.tr_gpu.toggled.connect(lambda v: self._tr_where("local", v))
        self.tr_on.toggled.connect(lambda v: self._tr_where("online", v))
        self.gm.currentIndexChanged.connect(self._gem_changed)
        self.gkey.editingFinished.connect(self._gem_changed)
        self.gkey_help.clicked.connect(self._gem_help)
        self.ssl = QCheckBox(tr("Don't translate lines already in the translation language"))
        self.ssl.toggled.connect(lambda v: self._flag("skip_same_lang", v))
        self.ip = QCheckBox(tr("Short phrases at once (gg, ok, wait…) without the translator"))
        self.ip.toggled.connect(lambda v: self._flag("instant_phrases", v))
        adv.add(self.ssl).add(self.ip)

        # ================= People
        g, adv = page("people")
        self.sp_en = QCheckBox(tr("Recognise who is speaking"))
        self.sp_en.toggled.connect(self._sp_en)
        self.sp_rem = QCheckBox(tr("Remember voices (stored on this PC only)"))
        self.sp_rem.toggled.connect(self._sp_rem)
        self.asl = QCheckBox(tr("Learn each person's language"))
        self.asl.setToolTip(tr("After a few lines it knows the language each person usually speaks, so short or\n"
                               "unclear sentences are no longer heard in the wrong language.\n"
                               "A clear switch to another language is still recognised."))
        self.asl.toggled.connect(lambda v: self._flag("auto_speaker_lang", v))
        g.add(SetCard(tr("Voices"), tr("Click a name on any line to rename it or fix the person – every fix makes it more accurate.")).add(
            self.sp_en, self.sp_rem, self.asl))
        # every known voice; Ctrl+click / Shift+click selects several, Delete or "Forget selected" removes them
        self.people_list = QListWidget()
        self.people_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.people_list.setToolTip(tr("Ctrl+click: pick several · Shift+click: pick a range · Ctrl+A: all\n"
                                       "Delete key or \"Forget selected\" removes the picked people"))
        self.people_list.setStyleSheet(f"QListWidget {{ background: {SURF2}; border: 1px solid {BORDER}; border-radius: 4px; padding: 2px; }}"
                                       f"QListWidget::item {{ padding: 5px 8px; border-radius: 3px; color: {TEXT}; }}"
                                       f"QListWidget::item:selected {{ background: #34343a; color: {TEXT}; }}")
        self.people_list.itemSelectionChanged.connect(self._people_ticked)
        self.people_del = QShortcut(QKeySequence.Delete, self.people_list)
        self.people_del.setContext(Qt.WidgetShortcut)
        self.sp_count = status(wrap=False)
        self.forget_sel_btn = ghost(tr("Forget selected"))
        self.forget_sel_btn.setEnabled(False)
        self.forget_btn = ghost(tr("Forget all voices"))
        g.add(SetCard(tr("Known people"), tr("Ctrl or Shift + click to pick several.")).add(
            self.sp_count, self.people_list, row(self.forget_sel_btn, self.forget_btn)))
        self.ign_lab = status(wrap=False)
        self.unign_btn = ghost(tr("Show everyone again"))
        g.add(SetCard(tr("Ignored people"), tr("Click a name on any line to ignore that person or to fix the language they always speak.")).add(
            self.ign_lab, self.unign_btn))
        self.sep_lab = status()
        self.sep = QSlider(Qt.Horizontal)
        self.sep.setRange(0, 100)
        self.sep.setToolTip(tr("Left: two people get merged more often · Right: one person gets split more often"))
        self.sep.valueChanged.connect(self._sep)
        adv.add(self.sep_lab, self.sep)

        # ================= Discord
        g, adv = page("discord")
        self.dc_en = QCheckBox(tr("Names and who is talking from Discord"))
        self.dc_en.setToolTip(tr("Uses Discord's own local connection (the Discord app on this PC) – no bot joins\n"
                                 "your servers. Each voice is linked to the person's Discord account, so names are\n"
                                 "right from the first sentence and are kept between sessions."))
        self.dc_id = QLineEdit()
        self.dc_id.setPlaceholderText(tr("Client ID (from discord.com/developers)"))
        self.dc_secret = QLineEdit()
        self.dc_secret.setPlaceholderText(tr("Client Secret"))
        self.dc_secret.setEchoMode(QLineEdit.Password)
        self.dc_connect = QPushButton(tr("Connect"))
        self.dc_connect.setObjectName("start")
        self.dc_help = ghost(tr("How to set it up"))
        self.dc_logout = ghost(tr("Log out"))
        self.dc_status = status(tr("Off"))
        g.add(SetCard(tr("Connection"), tr("Uses the Discord app on this PC – no bot joins your servers.")).add(
            self.dc_en, self.dc_id, self.dc_secret, self.dc_connect, row(self.dc_help, self.dc_logout), self.dc_status))
        self.dc_kind = QComboBox()
        for k, v in (("display", "Display name"), ("nick", "Server nickname"), ("username", "@username")):
            self.dc_kind.addItem(tr(v), k)
        g.add(SetCard(tr("Names"), tr("Which Discord name is shown on each line. A name you type yourself is kept.")).add(
            status(tr("Name shown")), self.dc_kind))
        self.ast = QCheckBox(tr("Start listening when a Discord call starts"))
        self.ast.toggled.connect(lambda v: self._flag("auto_start", v))
        self.asp = QCheckBox(tr("Stop when the call ends (frees the GPU)"))
        self.asp.toggled.connect(lambda v: self._flag("auto_stop", v))
        g.add(SetCard(tr("Calls"), tr("Start and stop together with your Discord calls.")).add(self.ast, self.asp))
        self.dc_help.clicked.connect(self._discord_help)
        adv.hide()

        # ================= Overlay & display
        g, adv = page("view")
        self.so = QCheckBox(tr("Original text in the feed (off = translation only)"))
        self.so.toggled.connect(self._show_orig)
        g.add(SetCard(tr("Live feed"), tr("The lines in this window.")).add(self.so))
        self.oso = QCheckBox(tr("Show original text in the overlay"))
        self.oso.toggled.connect(self._ov_orig)
        self.otime = QCheckBox(tr("Time in front of each line"))
        self.otime.toggled.connect(lambda v: self._flag("overlay_time", v))
        self.fs_lab = status()
        self.fs = QSlider(Qt.Horizontal)
        self.fs.setRange(11, 28)
        self.fs.valueChanged.connect(self._fs)
        self.nl_lab = status()
        self.nl = QSlider(Qt.Horizontal)
        self.nl.setRange(1, 8)
        self.nl.valueChanged.connect(self._nl)
        g.add(SetCard(tr("Overlay text"), tr("What the overlay over the game shows.")).add(
            self.oso, self.otime, self.fs_lab, self.fs, self.nl_lab, self.nl))
        self.op_lab = status()
        self.op = QSlider(Qt.Horizontal)
        self.op.setRange(20, 100)
        self.op.valueChanged.connect(self._op)
        self.to_lab = status()
        self.to = QSlider(Qt.Horizontal)
        self.to.setRange(30, 100)
        self.to.valueChanged.connect(self._to)
        self.ah_lab = status()
        self.ah = QSlider(Qt.Horizontal)
        self.ah.setRange(0, 30)
        self.ah.setToolTip(tr("When the overlay is locked (click-through) it fades away after this many quiet seconds. 0 = never."))
        self.ah.valueChanged.connect(self._ah)
        g.add(SetCard(tr("Overlay look"), tr("It stays above games in windowed or borderless mode (not exclusive full screen).")).add(
            self.op_lab, self.op, self.to_lab, self.to, self.ah_lab, self.ah))
        self.hk_en = QCheckBox(tr("Global hotkeys (work inside games)"))
        self.hk_en.toggled.connect(lambda v: self._flag("hotkeys_enabled", v))
        hk = status(tr("Ctrl+Alt+S start/stop · Ctrl+Alt+P pause · Ctrl+Alt+C copy last translation\n"
                       "Ctrl+Alt+O overlay on/off · Ctrl+Alt+L lock/unlock overlay (click-through)"))
        g.add(SetCard(tr("Hotkeys")).add(self.hk_en, hk))
        adv.hide()

        # ================= App
        g, adv = page("app")
        self.ui_lang = QComboBox()
        for code, name, _f in i18n.LANGS:
            self.ui_lang.addItem(flag_icon(code), name, code)
        self.ui_lang.setIconSize(QSize(24, 16))
        self.ui_lang.activated.connect(lambda _i: self.langPicked.emit(self.ui_lang.currentData() or "en"))
        g.add(SetCard(tr("App language"), tr("Also on the flag button in the left bar. The app restarts to switch.")).add(self.ui_lang))
        self.sww = QCheckBox(tr("Start with Windows (in the tray)"))
        self.sww.toggled.connect(self._sww)
        g.add(SetCard(tr("Windows")).add(self.sww))
        self.dr = QCheckBox(tr("Reconnect when headphones / device change"))
        self.dr.toggled.connect(lambda v: self._flag("device_recover", v))
        self.al = QCheckBox(tr("Switch to a lighter model when it lags"))
        self.al.toggled.connect(lambda v: self._flag("auto_lighter", v))
        self.lag_lab = status()
        self.lag = QSlider(Qt.Horizontal)
        self.lag.setRange(2, 10)
        self.lag.valueChanged.connect(self._lag)
        g.add(SetCard(tr("Reliability"), tr("Keeps it running by itself.")).add(self.dr, self.al, self.lag_lab, self.lag))
        self.export_btn = ghost(tr("Export .txt"))
        self.clear_btn = ghost(tr("Clear feed"))
        g.add(SetCard(tr("Transcript"), tr("Nothing is saved unless you export it.")).add(row(self.export_btn, self.clear_btn)))
        adv.hide()

        for c in self.findChildren(QComboBox):
            c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(12)
        for c in self.findChildren(QSlider) + self.findChildren(QComboBox) + self.findChildren(QAbstractSpinBox):
            c.setFocusPolicy(Qt.StrongFocus)          # the wheel alone doesn't give focus
            c.installEventFilter(self._wheel_guard)
        self.go("rec")
        self.load()

    # ---------------- navigation
    def go(self, key):
        if key in self.pages:
            self.cat_btns[key].setChecked(True)
            self.stack.setCurrentWidget(self.pages[key])

    def show_widget(self, w):
        """Open the category that holds w and scroll it into view."""
        for key, sc in self.pages.items():
            if sc.widget().isAncestorOf(w):
                self.go(key)

                def scroll(sc=sc):
                    y = w.mapTo(sc.widget(), QPointF(0, 0).toPoint()).y()
                    sc.verticalScrollBar().setValue(max(0, y - 60))
                QTimer.singleShot(30, scroll)
                return

    def load(self):
        s = self.s
        self._sel(self.wm, s.whisper_model)
        self._sel(self.hw, getattr(s, "compute", "gpu") or "gpu")
        self._sel(self.lm, s.llm_model)
        self.le.setChecked(s.llm_enabled)
        for cb, v in ((self.tr_gpu, s.translate_local), (self.tr_on, s.translate_online)):
            cb.blockSignals(True)
            cb.setChecked(bool(v))
            cb.blockSignals(False)
        self.gm.blockSignals(True)
        self._sel(self.gm, s.gemini_model or "gemma-3-27b-it")
        self.gm.blockSignals(False)
        self.gkey.setText(s.gemini_key or "")
        self._tr_vis()
        for c, cb in self.lang_boxes.items():
            cb.blockSignals(True)
            cb.setChecked(c in s.languages)
            cb.blockSignals(False)
        self.en.setChecked(s.enhance_audio)
        self.sp_en.setChecked(s.speakers_enabled)
        self.sep.setValue(int(s.speaker_separation * 100))
        self._sep(self.sep.value())
        self.sp_rem.setChecked(s.remember_speakers)
        self.sil.setValue(s.silence_ms)
        self._sil(s.silence_ms)
        self.so.setChecked(s.show_original)
        self.oso.setChecked(s.overlay_show_original)
        self.vocab.blockSignals(True)
        self.vocab.setPlainText("\n".join(s.vocabulary or []))
        self.vocab.blockSignals(False)
        self.mu.setChecked(s.mark_unsure)
        self.to.setValue(int((s.overlay_text_opacity or 1) * 100))
        self._to(self.to.value())
        self.ah.setValue(int(s.overlay_autohide_s or 0))
        self._ah(self.ah.value())
        self.dr.setChecked(s.device_recover)
        self.al.setChecked(s.auto_lighter)
        self.dc_en.blockSignals(True)
        self.dc_en.setChecked(bool(s.discord_enabled))
        self.dc_en.blockSignals(False)
        self.dc_id.setText(s.discord_client_id or "")
        self.dc_secret.setText(s.discord_client_secret or "")
        self.dc_kind.blockSignals(True)
        self._sel(self.dc_kind, s.discord_name or "display")
        self.dc_kind.blockSignals(False)
        for cb, key in ((self.vc, "vad_cut"), (self.asl, "auto_speaker_lang"), (self.lol, "league_terms"),
                        (self.dng, "denoise_gpu"), (self.fl, "fast_lang"), (self.ssl, "skip_same_lang"),
                        (self.ip, "instant_phrases"), (self.otime, "overlay_time")):
            cb.blockSignals(True)
            cb.setChecked(bool(getattr(s, key, True)))
            cb.blockSignals(False)
        self.lag.setValue(int(round(s.lag_limit_s)))
        self._lag(self.lag.value())
        self.ast.setChecked(s.auto_start)
        self.asp.setChecked(s.auto_stop)
        self.sww.blockSignals(True)
        self.sww.setChecked(s.start_with_windows)
        self.sww.blockSignals(False)
        self.hk_en.setChecked(s.hotkeys_enabled)
        self.op.setValue(int(s.overlay_opacity * 100))
        self._op(self.op.value())
        self.fs.setValue(s.overlay_font)
        self._fs(s.overlay_font)
        self.nl.setValue(s.overlay_lines)
        self._nl(s.overlay_lines)
        self._sel(self.ui_lang, i18n.current())

    @staticmethod
    def _sel(combo, value, editable=False):
        i = combo.findData(value)
        if i >= 0:
            combo.setCurrentIndex(i)
        elif editable:
            combo.setEditText(value)

    def set_people(self, people):
        """people: [(id, name, samples, discord)] – rebuilt whenever voices change; the selection is kept."""
        picked = set(self.selected_people())
        lw = self.people_list
        lw.blockSignals(True)
        lw.clear()
        for r in people:
            sid, name, n = r[0], r[1], r[2]
            dc = r[3] if len(r) > 3 else False
            if dc:
                tag = "Discord · " + (tr("voice samples: {n}").format(n=n) if n else tr("no voice yet"))
            else:
                tag = tr("voice samples: {n}").format(n=n)
            it = QListWidgetItem(f"{name}    ·  {tag}")
            it.setData(Qt.UserRole, sid)
            lw.addItem(it)
            it.setSelected(sid in picked)
        lw.blockSignals(False)
        lw.setFixedHeight(min(240, max(36, 26 * len(people) + 10)))
        lw.setVisible(bool(people))
        self._people_ticked()

    def _people_ticked(self, *_):
        n = len(self.people_list.selectedItems())
        self.forget_sel_btn.setEnabled(n > 0)
        self.forget_sel_btn.setText(f"{tr('Forget selected')} ({n})" if n else tr("Forget selected"))

    def selected_people(self) -> list[int]:
        return [it.data(Qt.UserRole) for it in self.people_list.selectedItems()]

    def _discord_help(self):
        box = QMessageBox(self)
        box.setWindowTitle(tr("Discord names – setup (once, about 2 minutes)"))
        box.setTextFormat(Qt.RichText)
        box.setText(tr(
            "<b>1.</b> Open <b>discord.com/developers/applications</b> in your browser and log in.<br>"
            "<b>2.</b> <b>New Application</b> → name it <i>AudioTranscriber</i> → Create.<br>"
            "<b>3.</b> Left menu <b>OAuth2</b>: copy the <b>Client ID</b>. Click <b>Reset Secret</b> and copy the "
            "<b>Client Secret</b>.<br>"
            "<b>4.</b> Still in OAuth2 → <b>Redirects</b> → <b>Add Redirect</b>: <code>http://localhost</code> → "
            "<b>Save Changes</b>.<br>"
            "<b>5.</b> Paste both codes here, tick <i>Names and who is talking from Discord</i> and press <b>Connect</b>.<br>"
            "<b>6.</b> Discord shows a window: click <b>Authorize</b>.<br><br>"
            "Done – it reconnects by itself every time. The codes and the login stay on this PC only "
            "(settings.json and discord_token.json)."))
        box.exec()

    # ---------------- translator: where it runs
    def _tr_where(self, which, v):
        s = self.s
        if which == "local":
            s.translate_local = bool(v)
        else:
            s.translate_online = bool(v)
        if not s.translate_local and not s.translate_online:     # at least one
            other = self.tr_on if which == "local" else self.tr_gpu
            other.blockSignals(True)
            other.setChecked(True)
            other.blockSignals(False)
            if which == "local":
                s.translate_online = True
            else:
                s.translate_local = True
        s.save()
        self._tr_vis()
        self.changed.emit()

    def _tr_vis(self):
        s = self.s
        self.local_card.setVisible(s.translate_local)
        self.on_box.setVisible(s.translate_online)
        self.update_gem_usage()

    def update_gem_usage(self):
        from .online import MODELS as GEM_MODELS, _pacific_day
        s = self.s
        used = int(s.online_used or 0) if s.online_day == _pacific_day() else 0
        lim = GEM_MODELS.get(s.gemini_model, ("", 0))[1]
        mode = (tr("Both: online first, graphics card when online can't answer.") if s.translate_local
                else tr("Online only: if it can't answer, lines stay untranslated."))
        key = "" if (s.gemini_key or "").strip() else tr("Paste a key first.") + " "
        use = (tr("Used today: {used} of about {lim} free").format(used=used, lim=f"{lim:,}") if lim
               else tr("Used today: {used}").format(used=used))
        self.g_usage.setText(f"{key}{use} ({tr('resets at 09:00')}). {mode}")

    def _gem_changed(self, *_):
        self.s.gemini_model = self.gm.currentData() or "gemma-3-27b-it"
        self.s.gemini_key = self.gkey.text().strip()
        self.s.save()
        self.update_gem_usage()

    def _gem_help(self):
        box = QMessageBox(self)
        box.setWindowTitle(tr("Gemini – free key (1 minute)"))
        box.setTextFormat(Qt.RichText)
        box.setText(tr(
            "<b>1.</b> Open <b>aistudio.google.com/apikey</b> and log in with a Google account.<br>"
            "<b>2.</b> Click <b>Create API key</b> and copy it.<br>"
            "<b>3.</b> Paste it here. It stays on this PC (settings.json).<br><br>"
            "<b>Gemma 3 27B</b> has the biggest free daily allowance (about 14,400 sentences). "
            "Gemini Flash-Lite / Flash are smarter but their free allowance is small.<br>"
            "On the free plan Google may use what is sent to improve its products; with billing turned on it doesn't."))
        box.exec()

    def _apply(self):
        s = self.s
        s.compute = self.hw.currentData() or "gpu"
        s.whisper_model = self.wm.currentData()
        s.whisper_device = "cpu" if s.compute == "cpu" else "cuda"
        s.llm_on_gpu = s.compute != "cpu"
        s.llm_model = self.lm.currentData() or "gemma3:4b"
        s.llm_enabled = self.le.isChecked()
        s.save()
        self.applyRequested.emit()

    def _langs(self):
        self.s.languages = [c for c, cb in self.lang_boxes.items() if cb.isChecked()] or ["en"]
        self.changed.emit()

    def _sil(self, v):
        self.s.silence_ms = int(v)
        self.sil_lab.setText(tr("Pause that ends a sentence: {ms} ms").format(ms=v))

    def _sp_en(self, v):
        self.s.speakers_enabled = v
        self.changed.emit()

    def _sep(self, v):
        self.s.speaker_separation = v / 100
        side = tr("merge more") if v < 40 else tr("split more") if v > 60 else tr("balanced")
        self.sep_lab.setText(tr("Speaker separation: {side} ({v})").format(side=side, v=v))
        self.changed.emit()

    def _sp_rem(self, v):
        self.s.remember_speakers = v
        self.changed.emit()

    def _enh(self, v):
        self.s.enhance_audio = v
        self.changed.emit()

    def _show_orig(self, v):
        self.s.show_original = v
        self.changed.emit()

    def _op(self, v):
        self.s.overlay_opacity = v / 100
        self.op_lab.setText(tr("Overlay background opacity: {v}%").format(v=v))
        self.changed.emit()

    def _fs(self, v):
        self.s.overlay_font = v
        self.fs_lab.setText(tr("Overlay text size: {v}px").format(v=v))
        self.changed.emit()

    def _flag(self, k, v):
        setattr(self.s, k, bool(v))
        self.changed.emit()

    def _vocab(self):
        raw = self.vocab.toPlainText()
        self.s.vocabulary = [w.strip() for w in _re.split(r"[\n,;]+", raw) if w.strip()][:120]
        self.changed.emit()

    def _mu(self, v):
        self.s.mark_unsure = v
        Card.mark_unsure = v
        self.changed.emit()

    def _ov_orig(self, v):
        self.s.overlay_show_original = v
        self.changed.emit()

    def _to(self, v):
        self.s.overlay_text_opacity = v / 100
        self.to_lab.setText(tr("Overlay text opacity: {v}%").format(v=v))
        self.changed.emit()

    def _ah(self, v):
        self.s.overlay_autohide_s = int(v)
        self.ah_lab.setText(tr("Overlay hides when quiet: after {v} s (when locked)").format(v=v) if v
                            else tr("Overlay hides when quiet: never"))
        self.changed.emit()

    def _lag(self, v):
        self.s.lag_limit_s = float(v)
        self.lag_lab.setText(tr("…when a sentence takes more than {v} s").format(v=v))
        self.changed.emit()

    def _sww(self, v):
        if set_start_with_windows(v, ROOT):
            self.s.start_with_windows = v
        else:
            self.sww.blockSignals(True)
            self.sww.setChecked(not v)
            self.sww.blockSignals(False)
        self.changed.emit()

    def _nl(self, v):
        self.s.overlay_lines = v
        self.nl_lab.setText(tr("Overlay lines: {v}").format(v=v))
        self.changed.emit()


# ----------------------------------------------------------------------------- main window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Window)
        self.s = Settings.load()
        self._set_language()
        if not self.s.bisaya_added:                     # new language: switched on once, untick it in Settings
            if "ceb" not in self.s.languages:
                self.s.languages = list(self.s.languages) + ["ceb"]
            self.s.bisaya_added = True
            self.s.save()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("AudioTranscriber")
        self.setWindowIcon(app_icon())
        self.resize(1040, 720)
        self.setMinimumSize(760, 520)
        self.setStyleSheet(QSS.replace("CHECK_PNG", _check_png()))

        self.bridge = Bridge()
        self.bridge.status.connect(self._on_status)
        self.bridge.line.connect(self._on_line)
        self.bridge.update.connect(self._on_update)
        self.bridge.metrics.connect(self._on_metrics)
        self.bridge.level.connect(self._on_level)
        self.bridge.ready.connect(self._on_ready)
        self.bridge.captures.connect(self._on_captures)
        self.bridge.toggle_overlay.connect(lambda: self.overlay_btn.toggle())
        self.bridge.toggle_lock.connect(lambda: self.overlay.set_locked(not self.s.overlay_locked))
        self.bridge.toggle_run.connect(self.toggle_run)
        self.bridge.toggle_pause.connect(self.toggle_pause)
        self.bridge.copy_last.connect(self.copy_last)
        Card.mark_unsure = self.s.mark_unsure
        self.paused = False
        self._auto_started = False
        self._call_seen = 0
        self._call_gone = 0
        self._dev_id = ""
        self._recovering = False

        self.engine: Engine | None = None
        self.captures: list[AppCapture] = []
        self.cards: dict[int, Card] = {}
        self.lines: dict[int, Line] = {}
        self.app_buttons: dict[str, QToolButton] = {}
        self.apps: list[AppInfo] = []
        self.metrics = {"asr_ms": 0, "llm_ms": 0}
        self.running = False
        self.state = "idle"
        self._load_t0 = 0.0
        self.registry = SpeakerRegistry(self.s)

        root = QFrame()
        root.setObjectName("root")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)
        hl = QHBoxLayout(root)
        hl.setContentsMargins(1, 1, 1, 1)
        hl.setSpacing(0)

        # --- left rail
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(64)
        rl = QVBoxLayout(rail)
        rl.setContentsMargins(10, 14, 10, 14)
        rl.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(36, 36))
        logo.setAlignment(Qt.AlignCenter)
        logo.mousePressEvent = self._title_press
        rl.addWidget(logo, 0, Qt.AlignHCenter)
        rl.addSpacing(14)

        def rail_btn(kind, tip, checkable=False):
            b = QToolButton()
            b.setObjectName("railbtn")
            b.setIcon(rail_icon(kind))
            b.setIconSize(QSize(20, 20))
            b.setFixedSize(44, 44)
            b.setCheckable(checkable)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            rl.addWidget(b, 0, Qt.AlignHCenter)
            return b

        self.live_btn = rail_btn("live", tr("Live – the conversation"), True)
        self.live_btn.setChecked(True)
        self.people_btn = rail_btn("people", tr("People – names, voices, Discord"))
        self.words_btn = rail_btn("words", tr("Words to know – names, game terms, slang"))
        self.overlay_btn = rail_btn("overlay", tr("Overlay on top of the game – Ctrl+Alt+O"), True)
        self.lock_btn = rail_btn("unlock", tr("Lock overlay (clicks go through to the game) – Ctrl+Alt+L"))
        self.lock_btn.clicked.connect(lambda: self.bridge.toggle_lock.emit())
        self.clear_btn = rail_btn("clear", tr("Clear the whole chat (also the overlay)"))
        self.clear_btn.clicked.connect(self.clear_feed)
        rl.addStretch(1)
        self.flag_btn = QToolButton()
        self.flag_btn.setObjectName("railbtn")
        self.flag_btn.setFixedSize(44, 36)
        self.flag_btn.setIcon(flag_icon(i18n.current()))
        self.flag_btn.setIconSize(QSize(24, 16))
        self.flag_btn.setCursor(Qt.PointingHandCursor)
        self.flag_btn.setToolTip(tr("App language") + ": " + i18n.NAMES.get(i18n.current(), "English"))
        self.flag_btn.setPopupMode(QToolButton.InstantPopup)
        fm = QMenu(self.flag_btn)
        for code, name, _f in i18n.LANGS:
            act = fm.addAction(flag_icon(code), name)
            act.setCheckable(True)
            act.setChecked(code == i18n.current())
            act.setData(code)
        fm.triggered.connect(lambda a: self._pick_language(a.data()))
        self.flag_btn.setMenu(fm)
        self.flag_btn.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0; }")
        rl.addWidget(self.flag_btn, 0, Qt.AlignHCenter)
        self.set_btn = rail_btn("settings", tr("Settings"), True)
        hl.addWidget(rail)

        # --- main column
        main = QWidget()
        lay = QVBoxLayout(main)
        lay.setContentsMargins(26, 12, 18, 10)
        lay.setSpacing(12)
        hl.addWidget(main, 1)

        # title bar: session name, chips, window buttons (drag the empty part to move the window)
        tb = QWidget()
        tb.setObjectName("titlebar")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(0, 0, 0, 0)
        tbl.setSpacing(8)
        tcol = QVBoxLayout()
        tcol.setSpacing(2)
        t = QLabel(tr("Live session"))
        self.title_lab = t
        t.setObjectName("title")
        st = QLabel()
        st.setObjectName("subtitle")
        self.subtitle = st
        tcol.addWidget(t)
        tcol.addWidget(st)
        tbl.addLayout(tcol)
        tbl.addStretch(1)
        self.chips = {}
        for k in ("gpu", "vram", "cpu", "ram", "lat"):        # values shown in the side panel tiles
            c = QLabel("–")
            c.setObjectName("chip")
            c.hide()
            self.chips[k] = c
        for txt, slot, name in (("—", self.showMinimized, "winbtn"), ("✕", self.close, "closebtn")):
            b = QToolButton()
            b.setText(txt)
            b.setObjectName(name)
            b.clicked.connect(slot)
            tbl.addWidget(b, 0, Qt.AlignTop)
        tb.mousePressEvent = self._title_press
        tb.mouseDoubleClickEvent = lambda e: self.showNormal() if self.isMaximized() else self.showMaximized()
        lay.addWidget(tb)

        # control row: waveform | auto | pause | language | start
        self.live_top = QWidget()
        lt = QVBoxLayout(self.live_top)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.setSpacing(12)
        lay.addWidget(self.live_top)
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.meter = LevelMeter(self.s.threshold_db)
        self.meter.thresholdChanged.connect(self._threshold)
        row2.addWidget(self.meter, 1)
        self.auto_btn = QPushButton(tr("Auto"))
        self.auto_btn.setObjectName("ghost")
        self.auto_btn.setCheckable(True)
        self.auto_btn.setChecked(self.s.auto_threshold)
        self.auto_btn.setToolTip(tr("Auto threshold: follows each speaker's background noise\n"
                                    "(helps with hissy / noisy microphones). Drag the line to set it by hand."))
        self.auto_btn.toggled.connect(self._auto)
        row2.addWidget(self.auto_btn)
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setObjectName("ghost")
        self.pause_btn.setFixedWidth(44)
        self.pause_btn.setToolTip(tr("Pause / resume listening – Ctrl+Alt+P\n(models stay loaded, nothing is transcribed)"))
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        row2.addWidget(self.pause_btn)
        # quick switch of the languages listened for (the same ticks as Settings > Recognition)
        self.langs_btn = QPushButton()
        self.langs_btn.setObjectName("ghost")
        self.langs_btn.setCursor(Qt.PointingHandCursor)
        self.langs_menu = StickyMenu(self.langs_btn)
        self.langs_menu.aboutToShow.connect(self._fill_langs_menu)
        self.langs_btn.setMenu(self.langs_menu)
        row2.addWidget(self.langs_btn)
        self.target_btn = QPushButton()
        self.target_btn.setObjectName("ghost")
        self.target_btn.setCursor(Qt.PointingHandCursor)
        self.target_menu = QMenu(self.target_btn)
        for code, label in TARGETS.items():
            act = self.target_menu.addAction(label)
            act.setCheckable(True)
            act.setData(code)
        self.target_menu.triggered.connect(lambda a: self._set_target(a.data()))
        self.target_btn.setMenu(self.target_menu)
        row2.addWidget(self.target_btn)
        self.llm_btn = QPushButton()
        self.llm_btn.setObjectName("ghost")
        self.llm_menu = QMenu(self.llm_btn)
        for code, label in LLM_CHOICES.items():
            act = self.llm_menu.addAction(label)
            act.setCheckable(True)
            act.setData(code)
        self.llm_menu.triggered.connect(lambda a: self._set_llm(a.data()))
        self.llm_btn.setMenu(self.llm_menu)
        self.llm_btn.hide()                     # the translator is chosen in Settings
        self.start_btn = QPushButton("▶  " + tr("Start"))
        self.start_btn.setObjectName("start")
        self.start_btn.setMinimumWidth(112)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.toggle_run)
        row2.addWidget(self.start_btn)
        lt.addLayout(row2)
        self._show_target()
        self._show_llm()

        # apps to listen to
        row = QHBoxLayout()
        row.setSpacing(8)
        lab = QLabel(tr("LISTEN TO"))
        lab.setObjectName("sectiontitle")
        row.addWidget(lab)
        self.app_row = QHBoxLayout()
        self.app_row.setSpacing(6)
        self.app_row.setContentsMargins(0, 0, 0, 0)
        app_wrap = QWidget()
        app_wrap.setLayout(self.app_row)
        app_scroll = QScrollArea()
        app_scroll.setWidget(app_wrap)
        app_scroll.setWidgetResizable(True)
        app_scroll.setFixedHeight(40)
        app_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        app_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        row.addWidget(app_scroll, 1)
        ref = QToolButton()
        ref.setText("⟳")
        ref.setObjectName("ghost")
        ref.setToolTip(tr("Refresh app list"))
        ref.clicked.connect(self.refresh_apps)
        row.addWidget(ref)
        lt.addLayout(row)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)                 # indeterminate "working" animation
        self.loading_bar.setFixedHeight(2)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.hide()
        lay.addWidget(self.loading_bar)
        sep = QFrame()
        sep.setObjectName("hsep")
        sep.setFixedHeight(1)
        lt.addWidget(sep)

        # --- feed | side panel (performance + people) or settings
        mid = QHBoxLayout()
        mid.setSpacing(14)
        self.feed_scroll = QScrollArea()
        self.feed_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.feed_scroll.setWidgetResizable(True)
        feed_w = QWidget()
        self.feed = QVBoxLayout(feed_w)
        self.feed.setContentsMargins(0, 2, 8, 0)
        self.feed.setSpacing(10)
        self.empty = QLabel(tr("Pick an app above (Discord is selected automatically) and press Start.\n"
                               "Lines appear here as people talk – what was said and its translation."))
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignCenter)
        self.feed.addWidget(self.empty)
        self.feed.addStretch(1)
        self.feed_scroll.setWidget(feed_w)
        self.feed_scroll.verticalScrollBar().rangeChanged.connect(self._autoscroll)
        mid.addWidget(self.feed_scroll, 1)

        self.side = QFrame()
        self.side.setObjectName("side")
        self.side.setFixedWidth(262)
        sl = QVBoxLayout(self.side)
        sl.setContentsMargins(16, 2, 0, 0)
        sl.setSpacing(10)
        h1 = QLabel(tr("PERFORMANCE"))
        h1.setObjectName("sectiontitle")
        sl.addWidget(h1)
        tg = QGridLayout()
        tg.setSpacing(8)
        self.tiles = {}
        for i, (k, lab_) in enumerate((("lat", tr("Delay")), ("gpu", "GPU"), ("vram", "VRAM"), ("cpu", "CPU"),
                                       ("ram", tr("RAM app")), ("lines", tr("Lines")))):
            f = QFrame()
            f.setObjectName("tile")
            fl = QVBoxLayout(f)
            fl.setContentsMargins(12, 8, 12, 9)
            fl.setSpacing(0)
            l1 = QLabel(lab_)
            l1.setObjectName("tilelab")
            l2 = QLabel("–")
            l2.setObjectName("tileval")
            fl.addWidget(l1)
            fl.addWidget(l2)
            tg.addWidget(f, i // 2, i % 2)
            self.tiles[k] = l2
            self.tiles[k + "_box"] = f
        sl.addLayout(tg)
        sl.addSpacing(8)
        h2 = QLabel(tr("PEOPLE"))
        h2.setObjectName("sectiontitle")
        sl.addWidget(h2)
        self.people_col = QVBoxLayout()
        self.people_col.setSpacing(8)
        sl.addLayout(self.people_col)
        self.people_empty = QLabel(tr("Names appear here as people talk."))
        self.people_empty.setObjectName("status")
        self.people_empty.setWordWrap(True)
        sl.addWidget(self.people_empty)
        sl.addStretch(1)
        self.side_overlay = QPushButton(tr("Show overlay in game"))
        self.side_overlay.setObjectName("ghost")
        self.side_overlay.setCheckable(True)
        self.side_overlay.toggled.connect(lambda on: self.overlay_btn.setChecked(on))
        self.overlay_btn.toggled.connect(lambda on: (self.side_overlay.blockSignals(True), self.side_overlay.setChecked(on),
                                                    self.side_overlay.setText(tr("Hide overlay") if on else tr("Show overlay in game")),
                                                    self.side_overlay.blockSignals(False)))
        sl.addWidget(self.side_overlay)
        self.side_move = QPushButton(tr("Move overlay"))
        self.side_move.setObjectName("ghost")
        self.side_move.setToolTip(tr("Unlocks the overlay so you can drag it; it locks again by itself after you drop it"))
        self.side_move.clicked.connect(self._move_overlay)
        sl.addWidget(self.side_move)
        mid.addWidget(self.side)
        self.overlay_btn.toggled.connect(self._toggle_overlay)

        self.settings_panel = SettingsPanel(self.s)
        self.settings_panel.hide()
        self.settings_panel.applyRequested.connect(self._apply_models)
        self.settings_panel.llmPicked.connect(self._set_llm)
        self.settings_panel.langPicked.connect(self._pick_language)
        self.settings_panel.changed.connect(self._display_changed)
        self.settings_panel.export_btn.clicked.connect(self.export)
        self.settings_panel.clear_btn.clicked.connect(self.clear_feed)
        self.settings_panel.forget_btn.clicked.connect(self.forget_voices)
        self.settings_panel.forget_sel_btn.clicked.connect(self._forget_selected)
        self.settings_panel.unign_btn.clicked.connect(self._unignore_all)
        self.settings_panel.people_del.activated.connect(self._forget_selected)
        sp_ = self.settings_panel
        sp_.dc_connect.clicked.connect(self._discord_connect)
        sp_.dc_logout.clicked.connect(self._discord_logout)
        sp_.dc_en.toggled.connect(self._discord_toggle)
        sp_.dc_kind.currentIndexChanged.connect(self._discord_kind)
        self.bridge.discord_status.connect(self._discord_status)
        self.bridge.discord_members.connect(self._discord_members)
        self.bridge.discord_connected.connect(self._discord_connected)
        self.discord = None
        if self.s.discord_enabled and self.s.discord_client_id:
            self._discord_start()
        self._update_voice_count()
        self._update_ignored()
        self.set_btn.toggled.connect(self._show_settings)
        self.live_btn.clicked.connect(lambda: (self.set_btn.setChecked(False), self.live_btn.setChecked(True)))
        self.people_btn.clicked.connect(lambda: self._open_settings_at(sp_.sp_en))
        self.words_btn.clicked.connect(lambda: self._open_settings_at(sp_.vocab))
        self.settings_panel.dc_en.setProperty("cat", "discord")
        mid.addWidget(self.settings_panel)
        lay.addLayout(mid, 1)

        # --- status bar
        sb = QHBoxLayout()
        self.st_asr = QLabel("Whisper: " + tr("idle"))
        self.st_asr.setObjectName("status")
        self.st_llm = QLabel(tr("Translator") + ": " + tr("idle"))
        self.st_llm.setObjectName("status")
        self.st_spk = QLabel("")
        self.st_spk.setObjectName("status")
        sb.addWidget(self.st_asr)
        sb.addSpacing(18)
        sb.addWidget(self.st_llm)
        sb.addSpacing(18)
        sb.addWidget(self.st_spk)
        sb.addStretch(1)
        grip = QSizeGrip(self)
        sb.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        lay.addLayout(sb)

        # --- overlay, tray, monitors, hotkeys
        self.overlay = Overlay(self.s)
        self.overlay_btn.setChecked(self.s.overlay_enabled)
        self._sync_lock_btn()
        self.monitor = ResourceMonitor()
        self.mon_timer = QTimer(self)
        self.mon_timer.timeout.connect(self._sample)
        self.mon_timer.start(1500)
        self._sample()
        self.hotkeys = None
        self._start_hotkeys()
        # headphones changed, Discord restarted…: capture comes back by itself
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._health)
        self.health_timer.start(2000)
        # Discord call started / ended
        self.call_timer = QTimer(self)
        self.call_timer.timeout.connect(self._watch_call)
        self.call_timer.start(3000)
        self._stick_bottom = True
        self.feed_scroll.verticalScrollBar().valueChanged.connect(self._scrolled)
        self.refresh_apps()
        self.app_timer = QTimer(self)
        self.app_timer.timeout.connect(self._refresh_apps_quiet)
        self.app_timer.start(8000)

        # tray
        self.tray = QSystemTrayIcon(app_icon(), self)
        m = QMenu()
        a1 = QAction(tr("Show window"), self)
        a1.triggered.connect(self.showNormal)
        a2 = QAction(tr("Toggle overlay"), self)
        a2.triggered.connect(lambda: self.overlay_btn.toggle())
        a2b = QAction(tr("Move overlay"), self)
        a2b.triggered.connect(self._move_overlay)
        a3 = QAction(tr("Quit"), self)
        a3.triggered.connect(self.close)
        for a in (a1, a2, a2b, a3):
            m.addAction(a)
        self.tray.setContextMenu(m)
        self.tray.setToolTip("AudioTranscriber")
        self.tray.show()

    # ---------------------------------------------------------------- window chrome
    def _title_press(self, e):
        if e.button() == Qt.LeftButton and self.windowHandle():
            self.windowHandle().startSystemMove()

    # ---------------------------------------------------------------- apps
    def _refresh_apps_quiet(self):
        if not self.running:
            self.refresh_apps()

    def refresh_apps(self):
        try:
            apps = list_audio_apps()
        except Exception as e:
            log.exception("list apps")
            apps = []
        prev_checked = {n for n, b in self.app_buttons.items() if b.isChecked()} or set(self.s.last_apps)
        if [a.name for a in apps] == [a.name for a in self.apps] and self.app_buttons:
            for a in apps:
                self._style_app_button(self.app_buttons[a.name], a)
            self.apps = apps
            return
        self.apps = apps
        while self.app_row.count():
            it = self.app_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.app_buttons = {}
        prov = QFileIconProvider()
        for a in apps:
            b = QToolButton()
            b.setObjectName("app")
            b.setCheckable(True)
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            b.setIcon(prov.icon(QFileInfo(a.exe)))
            b.setIconSize(QSize(20, 20))
            b.setChecked(a.name in prev_checked)
            self._style_app_button(b, a)
            b.toggled.connect(lambda _on: self._update_subtitle())
            self.app_row.addWidget(b)
            self.app_buttons[a.name] = b
        if not apps:
            l = QLabel(tr("No app is playing audio – join a Discord call, then ⟳"))
            l.setObjectName("status")
            self.app_row.addWidget(l)
        self.app_row.addStretch(1)

    @staticmethod
    def _style_app_button(b, a: AppInfo):
        dot = "  🟢" if a.active else ""
        b.setText(f"{a.label}{dot}")
        b.setToolTip(f"{a.exe}\nPID {a.pid} (+ {tr('child processes')})\n" +
                     (tr("Playing audio now") if a.active else tr("Not playing audio right now")))

    def _selected_apps(self) -> list[AppInfo]:
        return [a for a in self.apps if a.name in self.app_buttons and self.app_buttons[a.name].isChecked()]

    # ---------------------------------------------------------------- run / stop
    def toggle_run(self):
        self._auto_started = False
        if self.state == "idle":
            self.start_capture()
        else:
            self.stop_capture()

    def _set_state(self, state: str):
        self.state = state
        self.running = state != "idle"
        txt = {"idle": "▶  " + tr("Start"), "loading": "■  " + tr("Loading…"), "running": "■  " + tr("Stop")}[state]
        self.start_btn.setText(txt)
        self.start_btn.setProperty("running", "true" if state != "idle" else "false")
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        self.loading_bar.setVisible(state == "loading")
        for b in self.app_buttons.values():
            b.setEnabled(state == "idle")
        self.pause_btn.setEnabled(state == "running")
        if state == "idle":
            self.paused = False
            self.pause_btn.setText("⏸")

    def start_capture(self):
        """Never blocks the window: models load and capture starts in background threads."""
        self.refresh_apps()
        apps = self._selected_apps()
        if not apps:
            QMessageBox.information(self, "AudioTranscriber", tr("Select at least one app (e.g. Discord) first."))
            return
        self.s.last_apps = [a.name for a in apps]
        self.s.save()
        self._set_state("loading")
        self._load_t0 = time.time()
        first_id = (max(self.lines) + 1) if self.lines else 1
        try:
            self._create_engine(first_id, apps)
        except Exception as e:
            log.exception("start")
            self._set_state("idle")
            QMessageBox.warning(self, "AudioTranscriber", tr("Could not start:") + f"\n{e}")

    def _create_engine(self, first_id, apps):
        eng = Engine(self.s,
                     on_status=self.bridge.status.emit,
                     on_line=self.bridge.line.emit,
                     on_update=self.bridge.update.emit,
                     on_metrics=self.bridge.metrics.emit,
                     on_ready=lambda: self.bridge.ready.emit(eng),
                     registry=self.registry)
        eng.discord = self.discord
        self.engine = eng
        eng.start(first_id)

        def open_captures():
            caps, errors = [], []
            for a in apps:
                cap = AppCapture(a, self.s, on_utterance=eng.submit, on_level=self.bridge.level.emit)
                try:
                    cap.start()
                    caps.append(cap)
                except Exception as e:
                    log.exception("capture start")
                    errors.append(f"{a.label}: {e}")
            self.bridge.captures.emit(eng, caps, errors)
        threading.Thread(target=open_captures, daemon=True, name="open-captures").start()

    def _on_captures(self, eng, caps, errors):
        if eng is not self.engine:            # user pressed Stop meanwhile
            for c in caps:
                threading.Thread(target=c.stop, daemon=True).start()
            return
        self.captures = caps
        self._dev_id = default_output_id()
        for c in caps:
            if not c.process_specific:
                self._on_status("asr", "⚠ " + tr("Windows refused per-app capture for {app} – capturing ALL system audio").format(app=c.app.label))
        if errors:
            QMessageBox.warning(self, "AudioTranscriber", tr("Could not capture:") + "\n" + "\n".join(errors))
        if not caps:
            self.stop_capture()

    def _on_ready(self, eng):
        if eng is not self.engine or self.state != "loading":
            return
        self._set_state("running")
        log.info("Ready in %.1fs", time.time() - self._load_t0)
        if self.isMinimized():
            self.tray.showMessage("AudioTranscriber", tr("Listening"), app_icon(), 1500)

    def stop_capture(self):
        """Stops listening and frees the GPU memory (Whisper + translator)."""
        caps, self.captures = self.captures, []
        eng, self.engine = self.engine, None

        def shutdown():
            for c in caps:
                c.stop()
            if eng:
                eng.stop()
        threading.Thread(target=shutdown, daemon=True, name="shutdown").start()
        self._set_state("idle")
        self._on_status("asr", tr("stopped – memory freed"))
        self._on_status("llm", tr("stopped – memory freed"))
        self._on_status("spk", "")

    def _apply_models(self):
        was_running = self.state != "idle"
        if was_running:
            self.stop_capture()
            QTimer.singleShot(800, self.start_capture)
        else:
            self._on_status("asr", tr("settings applied – used on next Start"))

    def _threshold(self, db):
        # dragging the marker switches to manual
        self.s.threshold_db = db
        if self.s.auto_threshold:
            self.auto_btn.setChecked(False)

    def _auto(self, on):
        self.s.auto_threshold = on
        if not on:
            self.meter.threshold = self.s.threshold_db
        self.meter.update()
        self.s.save()

    # ---------------------------------------------------------------- engine events
    def _on_status(self, which, msg):
        if which == "asr":
            self.st_asr.setText(f"Whisper: {tr(msg)}" if msg else "Whisper: " + tr("idle"))
        elif which == "spk":
            self.st_spk.setText(f"{tr('Speakers')}: {tr(msg)}" if msg else "")
        elif which == "upd":
            self.st_spk.setText(tr(msg))
        else:
            self.st_llm.setText(f"{tr('Translator')}: {tr(msg)}" if msg else tr("Translator") + ": " + tr("idle"))

    def _on_level(self, _app, db, speaking, threshold):
        self.meter.set_level(db, speaking)
        if self.s.auto_threshold:
            self.meter.threshold = threshold

    def _on_metrics(self, k, v):
        if k == "model_switch":
            msg = tr("It was lagging, so it switched to a lighter speech model.")
            self._on_status("asr", msg)
            self.tray.showMessage("AudioTranscriber", msg, app_icon(), 3000)
            return
        self.metrics[k] = v

    def _on_line(self, line: Line):
        self.empty.hide()
        self.lines[line.id] = line
        QTimer.singleShot(0, self._update_people_panel)
        card = Card(line, self.s.show_original, on_speaker=self.speaker_menu)
        self.cards[line.id] = card
        self.feed.insertWidget(self.feed.count() - 1, card)
        if line.speaker_id is not None and line.speaker_id not in [c.line.speaker_id for c in list(self.cards.values())[:-1]]:
            self._update_voice_count()
        while len(self.cards) > 200:
            oldest = min(self.cards)
            self.cards.pop(oldest).deleteLater()
        if self.overlay.isVisible():
            self.overlay.push(line)

    def _on_update(self, line: Line):
        if line.id not in self.lines:
            return                      # a line that was cleared (or never shown): don't bring it back
        card = self.cards.get(line.id)
        if line.state == "skipped":
            if card:
                self.cards.pop(line.id).deleteLater()
            self.lines.pop(line.id, None)
        elif card:
            card.refresh()
        if self.overlay.isVisible():
            self.overlay.push(line)
            self.overlay.render_lines()

    # ---------------------------------------------------------------- speakers
    def _update_voice_count(self):
        people = self.registry.all()
        self.settings_panel.set_people([(p.id, self.registry.name(p.id), p.count(), bool(p.discord_id)) for p in people])
        n = len(people)
        self.settings_panel.sp_count.setText(tr("Voices known: {n}").format(n=n))

    def _refresh_speakers(self):
        for l in self.lines.values():
            if l.speaker_id is not None:
                if l.speaker_id not in self.registry.speakers:
                    continue
                l.speaker_name = self.registry.name(l.speaker_id)
        for c in self.cards.values():
            c.refresh()
        self.overlay.render_lines()
        self._update_voice_count()
        self._update_people_panel()

    def speaker_menu(self, card):
        l = card.line
        sid, reg = l.speaker_id, self.registry
        m = QMenu(self)
        a = m.addAction(tr("Rename “{name}”…").format(name=reg.name(sid)))
        a.triggered.connect(lambda: self._rename(sid))
        sp_obj = reg.speakers.get(sid)
        if sp_obj is not None and sp_obj.discord_id and sp_obj.name_custom:
            dn = m.addAction(tr("Use the Discord name again"))
            dn.triggered.connect(lambda: (reg.use_discord_name(sid), self._refresh_speakers()))
        if l.speaker_unsure:
            ok = m.addAction(tr("Yes, this is {name}").format(name=reg.name(sid)))
            ok.triggered.connect(lambda: self._confirm(l))
        sub = m.addMenu(tr("This is actually…"))
        for sp in reg.all():
            if sp.id != sid:
                act = sub.addAction(reg.name(sp.id))
                act.triggered.connect(lambda _=False, to=sp.id: self._reassign(l, to))
        sub.addSeparator()
        new = sub.addAction(tr("Someone new…"))
        new.triggered.connect(lambda: self._new_person(l))
        m.addSeparator()
        lk = m.addMenu(tr("Always speaks…"))
        cur = reg.lang_of(sid)
        auto = lk.addAction(tr("Detect automatically") + ("  ✓" if not cur else ""))
        auto.triggered.connect(lambda: self._lock_lang(sid, ""))
        lk.addSeparator()
        for code in self.s.languages or list(LANGUAGES):
            act = lk.addAction(lname(code) + ("  ✓" if cur == code else ""))
            act.triggered.connect(lambda _=False, c=code: self._lock_lang(sid, c))
        ig = m.addAction(tr("Show this person again") if reg.is_ignored(sid) else tr("Ignore {name}").format(name=reg.name(sid)))
        ig.triggered.connect(lambda: self._ignore(sid, not reg.is_ignored(sid)))
        m.addSeparator()
        others = [sp for sp in reg.all() if sp.id != sid]
        if others:
            mg = m.addMenu(tr("Merge “{name}” into…").format(name=reg.name(sid)))
            for sp in others:
                act = mg.addAction(reg.name(sp.id))
                act.triggered.connect(lambda _=False, keep=sp.id: self._merge(keep, sid))
        m.addSeparator()
        fg = m.addAction(tr("Forget the voice of {name}…").format(name=reg.name(sid)))
        fg.triggered.connect(lambda: self._forget_one(sid))
        m.exec(card.spk.mapToGlobal(card.spk.rect().bottomLeft()))

    def _rename(self, sid):
        name, ok = QInputDialog.getText(self, tr("Rename speaker"), tr("Name:"), text=self.registry.name(sid))
        if ok and name.strip():
            self.registry.rename(sid, name)
            self._refresh_speakers()

    def _confirm(self, l):
        self.registry.reassign(l.embs, None, l.speaker_id)
        l.speaker_unsure = False
        self._refresh_speakers()

    def _reassign(self, l, to_id):
        self.registry.reassign(l.embs, l.speaker_id, to_id)
        l.speaker_id, l.speaker_unsure = to_id, False
        self._refresh_speakers()

    def _new_person(self, l):
        name, ok = QInputDialog.getText(self, tr("New speaker"), tr("Name (optional):"))
        if not ok:
            return
        l.speaker_id = self.registry.new_from(l.embs, l.speaker_id, name)
        l.speaker_unsure = False
        self._refresh_speakers()

    def _merge(self, keep, drop):
        self.registry.merge(keep, drop)
        for x in self.lines.values():
            if x.speaker_id == drop:
                x.speaker_id = keep
        self._refresh_speakers()

    def _lock_lang(self, sid, code):
        self.registry.set_lang(sid, code)
        self._on_status("spk", f"{self.registry.name(sid)}: " + (tr("always {lang}").format(lang=lname(code)) if code else tr("language detected automatically")))

    def _ignore(self, sid, on):
        self.registry.set_ignored(sid, on)
        if on:
            for lid in [i for i, l in self.lines.items() if l.speaker_id == sid]:
                card = self.cards.pop(lid, None)
                if card:
                    card.deleteLater()
                self.lines.pop(lid, None)
            self.overlay.lines = [l for l in self.overlay.lines if l.speaker_id != sid]
            self.overlay.render_lines()
        self._update_ignored()

    def _unignore_all(self):
        self.registry.unignore_all()
        self._update_ignored()

    def _update_ignored(self):
        n = sum(1 for sp in self.registry.all() if sp.ignored)
        self.settings_panel.ign_lab.setText(tr("People ignored: {n}").format(n=n) if n else tr("Nobody ignored"))
        self.settings_panel.unign_btn.setEnabled(n > 0)

    # ---------------------------------------------------------------- hotkeys, pause, copy
    def _start_hotkeys(self):
        if self.hotkeys is not None or not self.s.hotkeys_enabled:
            return
        on = lambda f: (lambda: self.s.hotkeys_enabled and f())   # noqa: E731
        self.hotkeys = GlobalHotkeys({"O": on(self.bridge.toggle_overlay.emit), "L": on(self.bridge.toggle_lock.emit),
                                      "S": on(self.bridge.toggle_run.emit), "P": on(self.bridge.toggle_pause.emit),
                                      "C": on(self.bridge.copy_last.emit)})
        self.hotkeys.start()

    def toggle_pause(self):
        if self.state != "running" or not self.engine:
            return
        self.paused = not self.paused
        self.engine.paused = self.paused
        self.pause_btn.setText("▶" if self.paused else "⏸")
        self._on_status("asr", tr("paused – press Ctrl+Alt+P to continue") if self.paused else tr("listening"))
        self.tray.showMessage("AudioTranscriber", tr("Paused") if self.paused else tr("Listening again"), app_icon(), 1200)

    def _show_target(self):
        self._update_langs_btn()
        t = getattr(self.s, "target", "en")
        if t not in TARGETS:
            t = "en"
        self.target_btn.setText(f"→ {TARGETS[t]}")
        self.target_btn.setToolTip(tr("Translating into {lang}.").format(lang=TARGETS[t]) + "\n" +
                                   tr("Click to pick another language (works while running, from the next sentence)."))
        self._update_subtitle()
        for a in self.target_menu.actions():
            a.setChecked(a.data() == t)

    def _show_llm(self):
        m = self.s.llm_model
        self.llm_btn.setText(f"AI: {LLM_SHORT.get(m, m)}")
        self.llm_btn.setToolTip(f"Translator: {m}\nClick to switch – lighter = less graphics memory and faster, "
                                "heavier = better translations.\nWorks while running (Whisper stays loaded).")
        for a in self.llm_menu.actions():
            a.setChecked(a.data() == m)

    def _set_llm(self, model):
        if not model or model == self.s.llm_model:
            self._show_llm()
            return
        if self.engine is not None and self.state != "idle":
            self.engine.switch_translator(model)          # sets s.llm_model itself
            self.s.llm_model = model
        else:
            self.s.llm_model = model
            self._on_status("llm", tr("{model} will be used on Start").format(model=model))
        self.s.save()
        self._show_llm()
        try:
            self.settings_panel._sel(self.settings_panel.lm, model)
        except Exception:
            pass

    def _fill_langs_menu(self):
        m = self.langs_menu
        m.clear()
        t = m.addAction(tr("Languages to recognise"))
        t.setEnabled(False)
        for code, name in LANGUAGES.items():
            a = m.addAction(f"{lname(code)}  ·  {code.upper()}")
            a.setCheckable(True)
            a.setChecked(code in self.s.languages)
            a.toggled.connect(lambda on, c=code: self._toggle_lang(c, on))
        m.addSeparator()
        only = m.addMenu(tr("Only this one"))
        for code in LANGUAGES:
            only.addAction(lname(code)).triggered.connect(lambda _=False, c=code: self._only_lang(c))
        m.addAction(tr("More in Settings…")).triggered.connect(
            lambda: self._open_settings_at(next(iter(self.settings_panel.lang_boxes.values()))))

    def _toggle_lang(self, code, on):
        langs = [c for c in LANGUAGES if (c in self.s.languages and c != code) or (c == code and on)]
        self._apply_langs(langs or [code])

    def _only_lang(self, code):
        self._apply_langs([code])

    def _apply_langs(self, langs):
        """Takes effect from the next sentence, also while listening."""
        self.s.languages = langs
        for c, cb in self.settings_panel.lang_boxes.items():
            cb.blockSignals(True)
            cb.setChecked(c in langs)
            cb.blockSignals(False)
        self.s.save()
        self._update_langs_btn()
        if self.langs_menu.isVisible():          # keep the ticks in step (e.g. the last one can't be unticked)
            for a in self.langs_menu.actions():
                if a.isCheckable():
                    code = a.text().rsplit("·", 1)[-1].strip().lower()
                    a.blockSignals(True)
                    a.setChecked(code in langs)
                    a.blockSignals(False)

    def _update_langs_btn(self):
        langs = [c for c in LANGUAGES if c in self.s.languages]
        shown = " ".join(c.upper() for c in langs[:3]) + (f" +{len(langs) - 3}" if len(langs) > 3 else "")
        self.langs_btn.setText("🎧 " + shown)
        self.langs_btn.setToolTip(tr("Languages to recognise") + ": " + ", ".join(lname(c) for c in langs) + "\n" +
                                  tr("Click to switch quickly (works while running, from the next sentence)."))

    def _set_target(self, code):
        if code in TARGETS:
            self.s.target = code
            self.s.save()
        self._show_target()

    def copy_last(self):
        done = [l for l in sorted(self.lines.values(), key=lambda x: x.id) if l.state == "done" and any(l.tr.values())]
        if not done:
            return
        l = done[-1]
        who = f"{l.speaker_name}: " if l.speaker_id else ""
        QApplication.clipboard().setText(f"{who}{next((v for v in l.tr.values() if v), '')}".strip())
        self.tray.showMessage("AudioTranscriber", tr("Last translation copied"), app_icon(), 1200)

    # ---------------------------------------------------------------- capture health (device changes)
    def _health(self):
        if self.state != "running" or not self.s.device_recover or self._recovering:
            return
        dev = default_output_id()
        changed = bool(dev and self._dev_id and dev != self._dev_id)
        if dev:
            self._dev_id = dev
        import psutil
        dead = [c for c in self.captures if not c.alive() or not psutil.pid_exists(c.app.pid)]
        if changed or dead:
            self.restart_captures(tr("audio device changed") if changed else tr("capture stopped"))
        elif not self.captures:
            # lost the app earlier (e.g. Discord restarted): try again every few seconds
            self._retry = getattr(self, "_retry", 0) + 1
            if self._retry >= 3:
                self._retry = 0
                self.restart_captures(tr("looking for the app again"))

    def restart_captures(self, why: str):
        eng = self.engine
        if not eng:
            return
        self._recovering = True
        names = [c.app.name for c in self.captures] or list(self.s.last_apps)
        old, self.captures = self.captures, []
        self._on_status("asr", f"{why} – " + tr("reconnecting…"))
        log.info("Restarting capture: %s", why)

        def run():
            for c in old:
                try:
                    c.stop()
                except Exception:
                    pass
            time.sleep(0.8)
            caps, errors = [], []
            try:
                current = {a.name: a for a in list_audio_apps()}
            except Exception:
                current = {}
            for n in names:
                a = current.get(n)
                if not a:
                    errors.append(f"{n}: " + tr("not running"))
                    continue
                cap = AppCapture(a, self.s, on_utterance=eng.submit, on_level=self.bridge.level.emit)
                try:
                    cap.start()
                    caps.append(cap)
                except Exception as e:
                    errors.append(f"{a.label}: {e}")
            if caps:
                self.bridge.captures.emit(eng, caps, [])
            self._recovering = False
            if eng is self.engine:                       # not stopped meanwhile
                self.bridge.status.emit("asr", tr("reconnected – listening") if caps
                                        else tr("the app is gone – waiting for it to come back"))
        threading.Thread(target=run, daemon=True, name="recover").start()

    # ---------------------------------------------------------------- Discord call → start / stop by itself
    VOICE = ("discord.exe", "discordptb.exe", "discordcanary.exe")

    def _watch_call(self):
        if not (self.s.auto_start or (self._auto_started and self.s.auto_stop)):
            return
        try:
            apps = list_audio_apps()
        except Exception:
            return
        wanted = {n.lower() for n in self.s.last_apps} | set(self.VOICE)
        in_call = [a for a in apps if a.active and a.name.lower() in wanted and a.name.lower() in self.VOICE]
        if self.state == "idle" and self.s.auto_start:
            self._call_seen = self._call_seen + 1 if in_call else 0
            if self._call_seen >= 2:                  # active for a few seconds: not just a notification sound
                self._call_seen = 0
                self.refresh_apps()
                for n, b in self.app_buttons.items():
                    b.setChecked(n.lower() in {a.name.lower() for a in in_call} or n in self.s.last_apps)
                self._auto_started = True
                self.tray.showMessage("AudioTranscriber", tr("Discord call – listening"), app_icon(), 2000)
                self.start_capture()
        elif self.state == "running" and self._auto_started and self.s.auto_stop:
            self._call_gone = 0 if in_call else self._call_gone + 1
            if self._call_gone >= 20:                 # about a minute without the call
                self._call_gone = 0
                self._auto_started = False
                self.tray.showMessage("AudioTranscriber", tr("Call ended – stopped"), app_icon(), 2000)
                self.stop_capture()

    def _forget_selected(self):
        ids = self.settings_panel.selected_people()
        if not ids:
            return
        names = ", ".join(self.registry.name(i) for i in ids)
        if QMessageBox.question(self, "AudioTranscriber", tr("Forget these voices?") + f"\n{names}\n\n" + tr("Everyone else is kept.")) != QMessageBox.Yes:
            return
        for sid in ids:
            self._forget_one(sid, ask=False)

    def _forget_one(self, sid, ask: bool = True):
        name = self.registry.name(sid)
        if ask and QMessageBox.question(self, "AudioTranscriber",
                                        tr("Forget the voice of {name}?\nThe other people are kept. If {name} talks again, they get a new name.").format(name=name)) != QMessageBox.Yes:
            return
        self.registry.delete(sid)
        for x in self.lines.values():                  # their lines no longer show a name
            if x.speaker_id == sid:
                x.speaker_id, x.speaker_unsure = None, False
        if self.engine is not None:
            for x in getattr(self.engine, "_spk_recent", []):
                if x.speaker_id == sid:
                    x.speaker_id, x.speaker_unsure = None, False
        self._refresh_speakers()
        self._on_status("spk", tr("Voice of {name} forgotten").format(name=name))

    def forget_voices(self):
        if QMessageBox.question(self, "AudioTranscriber", tr("Forget all saved voices?")) == QMessageBox.Yes:
            self.registry.forget_all()
            self._update_voice_count()

    # ---------------------------------------------------------------- feed helpers
    def _scrolled(self, v):
        sb = self.feed_scroll.verticalScrollBar()
        self._stick_bottom = v >= sb.maximum() - 40

    def _autoscroll(self, _min, mx):
        if self._stick_bottom:
            self.feed_scroll.verticalScrollBar().setValue(mx)

    def _display_changed(self):
        self._start_hotkeys()
        self._update_langs_btn()
        for c in self.cards.values():
            c.show_original = self.s.show_original
            c.orig.setVisible(self.s.show_original or c.line.state != "done")
        self.overlay.render_lines()
        self.overlay.update()
        self.s.save()

    def clear_feed(self):
        for c in self.cards.values():
            c.deleteLater()
        self.cards.clear()
        self.lines.clear()
        if self.engine is not None:              # start the translator's context fresh too
            self.engine.history.clear()
            self.engine._spk_recent = []         # and don't re-check speakers of cleared lines
        self.overlay.lines = []
        self.overlay.render_lines()
        self.empty.show()
        self._update_people_panel()

    def export(self):
        if not self.lines:
            QMessageBox.information(self, "AudioTranscriber", tr("Nothing to export yet."))
            return
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        path = TRANSCRIPTS_DIR / f"transcript_{dt.datetime.now():%Y-%m-%d_%H-%M}.txt"
        with open(path, "w", encoding="utf-8") as f:
            for l in sorted(self.lines.values(), key=lambda x: x.id):
                when = dt.datetime.fromtimestamp(l.t).strftime("%H:%M:%S")
                who = f"{l.speaker_name}{'?' if l.speaker_unsure else ''} · " if l.speaker_id else ""
                f.write(f"[{when}] {who}{l.source.rsplit('.', 1)[0]} ({l.lang.upper()})"
                        f"{'  ≈estimated' if l.estimated else ''}\n")
                f.write(f"  {l.corrected or l.text}\n")
                for k, v in l.tr.items():
                    if v:
                        f.write(f"  {k.upper()}: {v}\n")
                f.write("\n")
        QMessageBox.information(self, "AudioTranscriber", tr("Saved to") + f"\n{path}")

    # ---------------------------------------------------------------- overlay
    def _toggle_overlay(self, on):
        self.s.overlay_enabled = on
        if on:
            self.overlay.lines = [self.lines[i] for i in sorted(self.lines)][-self.s.overlay_lines:]
            self.overlay.show()
            self.overlay.render_lines()
        else:
            self.overlay.hide()
        self.s.save()

    def _move_overlay(self):
        if not self.overlay_btn.isChecked():
            self.overlay_btn.setChecked(True)
        self.overlay.move_mode()
        self._sync_lock_btn()

    def _update_subtitle(self):
        t = getattr(self.s, "target", "en")
        parts = []
        apps = [a.label for a in self._selected_apps()] if self.app_buttons else []
        if apps:
            parts.append(", ".join(apps[:2]))
        dc = getattr(self, "discord", None)
        if dc is not None and dc.connected and dc.channel_id:
            n = len(dc.members())
            parts.append(tr("In {place}: {n}").format(place=dc.channel_name or tr("the call"), n=n))
        parts.append(tr("translating into {lang}").format(lang=TARGETS.get(t, 'English')))
        self.subtitle.setText(" · ".join(parts))

    def _sync_lock_btn(self):
        locked = bool(self.s.overlay_locked)
        if getattr(self, "_lock_shown", None) != locked:
            self._lock_shown = locked
            self.lock_btn.setIcon(rail_icon("lock" if locked else "unlock", TEXT if locked else MUTED))
            self.lock_btn.setToolTip(tr("Overlay locked: clicks go through to the game – click or Ctrl+Alt+L to unlock")
                                     if locked else tr("Lock overlay (clicks go through to the game) – Ctrl+Alt+L"))

    # ---------------------------------------------------------------- side panel / settings
    def _show_settings(self, on):
        self.settings_panel.setVisible(on)
        for w in (self.side, self.feed_scroll, self.live_top):
            w.setVisible(not on)
        self.title_lab.setText(tr("Settings") if on else tr("Live session"))
        self.subtitle.setVisible(not on)
        self.live_btn.setChecked(not on)
        if on:
            self._update_voice_count()                 # fresh sample counts

    def _open_settings_at(self, w):
        self.set_btn.setChecked(True)
        self.settings_panel.show_widget(w)

    # ---------------------------------------------------------------- interface language
    def _set_language(self):
        """The installer leaves lang.txt with the language picked there; otherwise the saved one (English by default)."""
        f = ROOT / "lang.txt"
        try:
            code = f.read_text(encoding="utf-8").strip()
            f.unlink()
        except Exception:
            code = ""
        if code in i18n.CODES:
            self.s.ui_lang = code
            self.s.save()
        elif self.s.ui_lang not in i18n.CODES:
            self.s.ui_lang = "en"
            self.s.save()
        self._shown_lang = i18n.set_lang(self.s.ui_lang)
        self._qt_tr = []
        qcode = {"pt-BR": "pt_BR", "pt-PT": "pt_PT", "es-ES": "es", "es-419": "es"}.get(self.s.ui_lang, self.s.ui_lang)
        try:                                            # Qt's own buttons (Yes / No / Cancel…)
            from PySide6.QtCore import QTranslator, QLibraryInfo
            path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
            for name in (f"qtbase_{qcode}", f"qt_{qcode}"):
                t = QTranslator(QApplication.instance())
                if qcode != "en" and t.load(name, path):
                    QApplication.instance().installTranslator(t)
                    self._qt_tr.append(t)
                    break
        except Exception:
            log.exception("Qt translations")

    def _pick_language(self, code):
        if not code or code == i18n.current():
            return
        self.s.ui_lang = code
        self.s.save()
        msg = QMessageBox(self)
        msg.setWindowTitle("AudioTranscriber")
        i18n.set_lang(code)                              # the question already in the new language
        msg.setText(tr("The app restarts to switch the language.") +
                    ("\n" + tr("Listening stops for a moment.") if self.state != "idle" else ""))
        now = msg.addButton(tr("Restart now"), QMessageBox.AcceptRole)
        msg.addButton(tr("Later"), QMessageBox.RejectRole)
        i18n.set_lang(self._shown_lang)                  # the rest of the window stays as it is until the restart
        msg.exec()
        if msg.clickedButton() is now:
            self._restart()
        else:
            self.settings_panel._sel(self.settings_panel.ui_lang, code)

    def _restart(self):
        import subprocess
        self._restarting = True
        upd = getattr(self, "_updater_state", None)
        if upd and upd.get("zip"):                       # an update is waiting: it restarts the app itself
            self.close()
            return
        args = [a for a in sys.argv[1:] if a not in ("--tray", "--restart")] + ["--restart"]
        exe = sys.executable
        if exe.lower().endswith("python.exe"):          # no console window
            w = exe[:-10] + "pythonw.exe"
            exe = w if Path(w).exists() else exe
        try:
            subprocess.Popen([exe, sys.argv[0], *args], cwd=str(ROOT), close_fds=True)
        except Exception:
            log.exception("restart")
            return
        self.close()

    def _update_people_panel(self):
        """Side panel: the people heard in this session (newest first), plus who else is in the Discord call."""
        if not hasattr(self, "people_col"):
            return
        seen, order = {}, []
        for l in sorted(self.lines.values(), key=lambda x: -x.t):
            if l.speaker_id is not None and l.speaker_id in self.registry.speakers and l.speaker_id not in seen:
                seen[l.speaker_id] = l.lang
                order.append(l.speaker_id)
        rows = []
        for sid in order[:8]:
            lang = self.registry.lang_of(sid) or self.registry.usual_lang(sid) or seen[sid]
            rows.append((spk_color(sid), self.registry.name(sid), lname(lang), True))
        if self.discord is not None and self.discord.connected:
            for uid, names in self.discord.members().items():
                sid = self.registry.by_discord(uid)
                if sid in seen or len(rows) >= 10:
                    continue
                lang = (self.registry.usual_lang(sid) if sid else "") or ""
                rows.append((spk_color(sid) if sid else DIM, self.registry.name(sid) if sid else self.discord.name(uid),
                             lname(lang) if lang else tr("in call"), False))
        while self.people_col.count():
            it = self.people_col.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        for col, name, lang, active in rows:
            r = QWidget()
            rl_ = QHBoxLayout(r)
            rl_.setContentsMargins(0, 0, 0, 0)
            rl_.setSpacing(10)
            bar = QFrame()
            bar.setFixedSize(5, 20)
            bar.setStyleSheet(f"background: {col}; border-radius: 1px;")
            n = QLabel(name)
            n.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT if active else MUTED};")
            g = QLabel(lang)
            g.setStyleSheet(f"font-size: 12px; color: {MUTED};")
            rl_.addWidget(bar)
            rl_.addWidget(n, 1)
            rl_.addWidget(g)
            self.people_col.addWidget(r)
        self.people_empty.setVisible(not rows)
        if "lines" in getattr(self, "tiles", {}):
            self.tiles["lines"].setText(str(len(self.lines)))

    # ---------------------------------------------------------------- resources
    def _sample(self):
        d = self.monitor.sample()
        gb = 1024 ** 3
        if "vram_used" in d:
            self.chips["gpu"].setText(f"GPU {d['gpu']}%")
            self.chips["vram"].setText(f"VRAM {d['vram_used'] / gb:.1f}/{d['vram_total'] / gb:.0f} GB")
        else:
            self.chips["gpu"].hide()
            self.chips["vram"].hide()
        self.chips["cpu"].setText(f"CPU {d['cpu']:.0f}%")
        self.chips["ram"].setText(f"RAM app {d['app_ram'] / gb:.1f} GB")
        self.chips["ram"].setToolTip(tr("AudioTranscriber + Ollama memory") + f"\n{tr('System')}: {d['ram_used'] / gb:.1f}/{d['ram_total'] / gb:.0f} GB")
        a, l = self.metrics["asr_ms"], self.metrics["llm_ms"]
        self.chips["lat"].setText(f"⏱ {a / 1000:.1f}s + {l / 1000:.1f}s")
        tot = (a + l) / 1000
        col = MUTED if not (a or l) else GREEN if tot < 2.5 else AMBER if tot < 4.5 else RED
        self.chips["lat"].setStyleSheet(f"color: {col};")
        self.chips["lat"].setToolTip("Last sentence: transcription time + time until the first Italian words")
        tl = self.tiles
        tl["lat"].setText(f"{tot:.1f}s" if (a or l) else "–")
        tl["lat_box"].setToolTip(tr("Last sentence: {a} recognition + {b} until the translation started").format(a=f"{a / 1000:.1f}s", b=f"{l / 1000:.1f}s"))
        if "vram_used" in d:
            tl["gpu"].setText(f"{d['gpu']}%")
            tl["vram"].setText(f"{d['vram_used'] / gb:.1f}<span style='font-size:12px;color:{MUTED}'> / {d['vram_total'] / gb:.0f} GB</span>")
        else:
            tl["gpu"].setText("–")
            tl["vram"].setText("–")
        tl["cpu"].setText(f"{d['cpu']:.0f}%")
        tl["ram"].setText(f"{d['app_ram'] / gb:.1f}<span style='font-size:12px;color:{MUTED}'> GB</span>")
        tl["ram_box"].setToolTip(tr("AudioTranscriber + Ollama memory") + f"\n{tr('System')}: {d['ram_used'] / gb:.1f}/{d['ram_total'] / gb:.0f} GB")
        tl["lines"].setText(str(len(self.lines)))
        if self.settings_panel.isVisible() and self.s.translate_online:
            self.settings_panel.update_gem_usage()
        self._sync_lock_btn()

    # ---------------------------------------------------------------- Discord names
    def _discord_start(self):
        from .discord_rpc import DiscordVoice
        if self.discord is None:
            self.discord = DiscordVoice(self.s, on_status=self.bridge.discord_status.emit,
                                        on_members=self.bridge.discord_members.emit,
                                        on_connected=self.bridge.discord_connected.emit)
            self.discord.start()
        else:
            self.discord.restart()
        if self.engine is not None:
            self.engine.discord = self.discord

    def _discord_connect(self):
        sp = self.settings_panel
        self.s.discord_client_id = sp.dc_id.text().strip()
        self.s.discord_client_secret = sp.dc_secret.text().strip()
        if not self.s.discord_client_id or not self.s.discord_client_secret:
            self._discord_status(tr("paste the Client ID and the Client Secret first (see “How to set it up”)"))
            return
        self.s.discord_enabled = True
        sp.dc_en.blockSignals(True)
        sp.dc_en.setChecked(True)
        sp.dc_en.blockSignals(False)
        self.s.save()
        self._discord_status(tr("connecting…"))
        self._discord_start()

    def _discord_toggle(self, on):
        self.s.discord_enabled = bool(on)
        self.s.save()
        if on:
            self._discord_connect()
        elif self.discord is not None:
            self.discord.stop()
            self._discord_status("Off")

    def _discord_logout(self):
        from .discord_rpc import forget_login
        forget_login()
        if self.discord is not None and self.s.discord_enabled:
            self._discord_status(tr("logged out – press Connect to authorize again"))
            self.discord.stop()

    def _discord_kind(self, _i):
        self.s.discord_name = self.settings_panel.dc_kind.currentData() or "display"
        self.s.save()
        self._refresh_speakers()

    def _discord_status(self, msg):
        msg = tr(msg) if msg else ""
        self.settings_panel.dc_status.setText(msg[:1].upper() + msg[1:] if msg else tr("Off"))
        self.settings_panel.dc_status.setToolTip(msg)
        if msg and msg != "off":
            self.st_spk.setText(f"Discord: {msg}")

    def _discord_connected(self, me):
        if not self.s.discord_fresh_done:
            # first time with Discord names: start the voices from zero (the old ones go to a backup file)
            n = self.registry.start_fresh(ROOT / "speakers_before_discord.json")
            self.s.discord_fresh_done = True
            self.s.save()
            for x in self.lines.values():
                x.speaker_id, x.speaker_unsure = None, False
            if n:
                self._on_status("spk", tr("Discord linked – old voices moved to speakers_before_discord.json: {n}").format(n=n))
        self._discord_members()

    def _discord_members(self):
        if self.discord is None:
            return
        self.registry.update_discord_names(self.discord.members())
        self._refresh_speakers()
        self._update_subtitle()

    # ---------------------------------------------------------------- close
    def closeEvent(self, e):
        upd = getattr(self, "_updater_state", None)
        if upd and upd.get("zip") and upd.get("apply"):
            # an update was downloaded: install it now instead of on the next start
            from . import updater as _u
            # closed by the user: it updates and stays closed; a restart (language switch) opens it again
            _u._launch_helper(Path(upd["zip"]), restart=bool(getattr(self, "_restarting", False)))
            upd["zip"] = None
        if self.discord is not None:
            self.discord.stop()
        eng = self.engine
        self.stop_capture()
        if eng:
            eng.translator.unload()            # free Ollama's VRAM right away
        self.overlay.close()
        self.tray.hide()
        self.s.save()
        e.accept()
        QApplication.quit()
