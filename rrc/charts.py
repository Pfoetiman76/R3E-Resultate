"""Minimal line chart (QPainter, no external dependencies, PyInstaller-friendly).

Used for the best-time progression per track: x = session date, y = lap time.
"""
from PySide6 import QtCore, QtGui, QtWidgets

from .theme import RR_RED


class LineChartWidget(QtWidgets.QWidget):
    """Simple line chart with axis labels and min/max markers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self._points = []   # list[(label_x, value)]
        self._title = ""

    def set_series(self, title, points):
        """points: list of (x_label, value); values must be numeric > 0."""
        self._title = title
        self._points = list(points or [])
        self.update()

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bg = QtGui.QColor("#131316")
        p.fillRect(0, 0, w, h, bg)
        muted = QtGui.QColor("#8f8f99")
        text = QtGui.QColor("#f1f1f3")
        pad_l, pad_t, pad_r, pad_b = 70, 30, 16, 40
        cw, ch = w - pad_l - pad_r, h - pad_t - pad_b

        f = QtGui.QFont("Segoe UI", 9)
        p.setFont(f)
        if not self._title:
            p.setPen(muted)
            p.drawText(self.rect(), QtCore.Qt.AlignCenter, "Keine Daten")
            p.end()
            return

        vals = [v for _, v in self._points]
        if not vals or min(vals) <= 0:
            p.setPen(muted)
            p.drawText(self.rect(), QtCore.Qt.AlignCenter, "Keine gültigen Zeiten")
            p.end()
            return
        vmin, vmax = min(vals), max(vals)
        if vmax - vmin < 1000:
            mid = (vmax + vmin) / 2.0
            vmin, vmax = mid - 500, mid + 500
        else:
            pad = (vmax - vmin) * 0.08
            vmin, vmax = vmin - pad, vmax + pad

        # title
        p.setPen(text)
        ft = QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold)
        p.setFont(ft)
        p.drawText(pad_l, 8, cw, 20, QtCore.Qt.AlignLeft, self._title)
        p.setFont(f)

        # frame + gridlines (3 horizontal)
        p.setPen(QtGui.QPen(QtGui.QColor("#26262c"), 1))
        p.drawRect(pad_l, pad_t, cw, ch)
        for i in range(1, 4):
            y = pad_t + ch * i / 4.0
            p.setPen(QtGui.QPen(QtGui.QColor("#1c1c21"), 1))
            p.drawLine(pad_l, int(y), pad_l + cw, int(y))
            v = vmax - (vmax - vmin) * i / 4.0
            p.setPen(muted)
            m, rem = divmod(int(v), 60000)
            s, msec = divmod(rem, 1000)
            p.drawText(4, int(y) - 7, pad_l - 8, 14,
                       QtCore.Qt.AlignRight, f"{m}:{s:02d}.{msec:03d}")

        # polyline
        n = len(self._points)
        pen = QtGui.QPen(QtGui.QColor(RR_RED), 2)
        p.setPen(pen)
        pts = []
        for i, (_, v) in enumerate(self._points):
            x = pad_l + (cw * i / (n - 1) if n > 1 else cw / 2)
            y = pad_t + ch * (1 - (v - vmin) / (vmax - vmin))
            pts.append(QtCore.QPointF(x, y))
        if len(pts) > 1:
            p.drawPolyline(pts)
        p.setBrush(QtGui.QColor(RR_RED))
        for pt in pts:
            p.drawEllipse(pt, 3, 3)

        # x labels (first / last, avoids crowding)
        p.setPen(muted)
        if self._points:
            p.drawText(pad_l, h - 26, cw, 14, QtCore.Qt.AlignLeft,
                       str(self._points[0][0]))
            p.drawText(pad_l, h - 26, cw, 14, QtCore.Qt.AlignRight,
                       str(self._points[-1][0]))
            best_i = min(range(n), key=lambda i: self._points[i][1])
            bv = self._points[best_i][1]
            m, rem = divmod(bv, 60000)
            s, msec = divmod(rem, 1000)
            p.drawText(pad_l, h - 26, cw, 14, QtCore.Qt.AlignCenter,
                       f"Bestzeit {m}:{s:02d}.{msec:03d}")
        p.end()
