"""Prozeduraler Icon-Generator (reines Python, keine Abhängigkeiten).

Erzeugt das App-Symbol (Stoppuhr + Schriftzug + roter Balken, Marcels
freigegebene Kombination aus Varianten A und C) als Windows-Icon-Datei
mit den Größen 16, 24, 32, 48, 64, 128 und 256 Pixeln.

Das Icon wird komplett pixelweise gezeichnet (PNG wird per zlib selbst
kodiert), damit weder Pillow noch Qt zur Build- oder Laufzeit benötigt
werden. Die CI erzeugt die .ico-Datei vor dem PyInstaller-Build; die App
selbst schreibt sie beim ersten Start in den App-Datenordner.

Koordinatensystem: alle Formen sind im 128er-Raum definiert und werden
auf die Zielgröße skaliert. Für kleine Größen werden Strichstärken
mindestens 1 Pixel breit gehalten, damit nichts "verschluckt" wird.
"""
import math
import struct
import zlib

# Farbpalette (identisch zu theme.py 0.4.3+)
BG = (0x13, 0x13, 0x18, 255)
PANEL = (0x1A, 0x1A, 0x20, 255)
BORDER = (0x2A, 0x2A, 0x32, 255)
RED = (0xE8, 0x21, 0x2B, 255)
GOLD = (0xE8, 0xC3, 0x4A, 255)
WHITE = (0xE8, 0xE8, 0xE8, 255)

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


# ------------------------------------------------------------- Rasterung --

class Canvas:
    """RGBA-Pixelbuffer mit einfachen Formprimitiven (ohne Antialiasing)."""

    def __init__(self, size):
        self.size = size
        self.px = [[None] * size for _ in range(size)]

    def set(self, x, y, color):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.px[y][x] = color

    def rect(self, x, y, w, h, color, rx=0.0):
        s = self.size
        x0, y0, x1, y1 = x, y, x + w, y + h
        for yy in range(max(0, int(math.floor(y0))),
                        min(s, int(math.ceil(y1)))):
            for xx in range(max(0, int(math.floor(x0))),
                             min(s, int(math.ceil(x1)))):
                if rx > 0 and self._outside_rounded(xx + 0.5, yy + 0.5,
                                                    x0, y0, x1, y1, rx):
                    continue
                self.set(xx, yy, color)

    @staticmethod
    def _outside_rounded(px_, py_, x0, y0, x1, y1, r):
        # Punkt in einer der Ecken außerhalb des Viertelkreises?
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                       (x0 + r, y1 - r), (x1 - r, y1 - r)):
            in_x = (cx == x0 + r and px_ < cx) or (cx == x1 - r and px_ > cx)
            in_y = (cy == y0 + r and py_ < cy) or (cy == y1 - r and py_ > cy)
            if in_x and in_y:
                if (px_ - cx) ** 2 + (py_ - cy) ** 2 > r * r:
                    return True
        return False

    def circle_fill(self, cx, cy, r, color):
        s = self.size
        for yy in range(max(0, int(math.floor(cy - r))),
                        min(s, int(math.ceil(cy + r)) + 1)):
            for xx in range(max(0, int(math.floor(cx - r))),
                            min(s, int(math.ceil(cx + r)) + 1)):
                if (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def ring(self, cx, cy, r, w, color):
        s = self.size
        outer, inner = r + w / 2.0, r - w / 2.0
        for yy in range(max(0, int(math.floor(cy - outer))),
                        min(s, int(math.ceil(cy + outer)) + 1)):
            for xx in range(max(0, int(math.floor(cx - outer))),
                            min(s, int(math.ceil(cx + outer)) + 1)):
                d = math.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
                if inner <= d <= outer:
                    self.set(xx, yy, color)

    def thick_line(self, x1, y1, x2, y2, w, color):
        s = self.size
        hw = w / 2.0
        pad = math.ceil(hw) + 1
        for yy in range(max(0, int(min(y1, y2) - pad)),
                        min(s, int(max(y1, y2) + pad) + 1)):
            for xx in range(max(0, int(min(x1, x2) - pad)),
                            min(s, int(max(x1, x2) + pad) + 1)):
                if _dist_segment(xx + 0.5, yy + 0.5, x1, y1, x2, y2) <= hw:
                    self.set(xx, yy, color)

    def polygon(self, points, color):
        """Ausgefülltes Polygon (Scanline, Gerade-Ungerade-Regel)."""
        s = self.size
        ys = [p[1] for p in points]
        for yy in range(max(0, int(math.floor(min(ys)))),
                        min(s, int(math.ceil(max(ys))) + 1)):
            py = yy + 0.5
            xs = []
            for i in range(len(points)):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % len(points)]
                if (y1 <= py < y2) or (y2 <= py < y1):
                    xs.append(x1 + (py - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for xx in range(max(0, int(math.floor(xs[i]))),
                                min(s, int(math.ceil(xs[i + 1])))):
                    self.set(xx, yy, color)

    def to_rgba(self):
        return bytes(b for row in self.px for c in row
                     for b in (c if c else (0, 0, 0, 0)))


def _dist_segment(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy)
                     / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


# ------------------------------------------------------------ Buchstaben --

def _draw_r(c, x, base_y, height, color):
    t = height * 0.30
    w = height * 0.74
    def L(x1, y1, x2, y2):
        c.thick_line(x + x1 * w, base_y - y1 * height,
                     x + x2 * w, base_y - y2 * height, t, color)
    L(0.14, 0.02, 0.14, 0.98)          # Hauptschaft
    L(0.10, 0.96, 0.62, 0.96)          # oberer Balken
    L(0.60, 0.94, 0.60, 0.52)           # Schale rechts
    L(0.10, 0.50, 0.64, 0.50)          # Mittelbalken
    L(0.44, 0.50, 0.86, 0.02)          # Diagonalbein
    return w


def _draw_c(c, x, base_y, height, color):
    t = height * 0.30
    # C als Polyzug (9 Stützpunkte)
    pts = [(0.72, 0.10), (0.50, 0.02), (0.28, 0.02), (0.10, 0.20),
           (0.02, 0.50), (0.10, 0.80), (0.28, 0.98), (0.50, 0.98),
           (0.72, 0.90)]
    w = height * 0.76
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        c.thick_line(x + x1 * w, base_y - y1 * height,
                     x + x2 * w, base_y - y2 * height, t, color)
    return w


# ----------------------------------------------------------- Icon-Aufbau --

def draw_icon(size):
    """Zeichnet das App-Icon in der gegebenen Pixelgröße."""
    k = size / 128.0
    c = Canvas(size)

    def S(v):
        """Skaliert 128er-Koordinate; Mindeststrichbreite 1px."""
        return max(1.0, v * k)

    # Hintergrundkachel mit Rand
    c.rect(4 * k, 4 * k, 120 * k, 120 * k, BORDER, rx=24 * k)
    bw = max(1.0, 2 * k)
    c.rect(4 * k + bw, 4 * k + bw, 120 * k - 2 * bw, 120 * k - 2 * bw,
           BG, rx=max(0.5, 24 * k - bw))

    # Krone der Stoppuhr
    c.rect(56 * k, 12 * k, 16 * k, max(1.5, 9 * k), GOLD, rx=3 * k)

    # Zifferblatt
    cx, cy, r = 64 * k, 52 * k, 27 * k
    c.circle_fill(cx, cy, r, PANEL)
    c.ring(cx, cy, r, S(5), GOLD)

    # Zeiger
    c.thick_line(cx, cy, cx, 32 * k, S(5), RED)
    c.thick_line(cx, cy, 79 * k, 59 * k, S(4), WHITE)
    c.circle_fill(cx, cy, 4.5 * k, GOLD)

    # Schriftzug RRC (Höhe ~19 im 128er Raum, Grundlinie y=104)
    h = 19 * k
    base_y = 104 * k
    gap = 8 * k
    letters = (_draw_r, _draw_r, _draw_c)
    widths = []
    for fn in letters:
        widths.append(h * (0.74 if fn is _draw_r else 0.76))
    total = sum(widths) + 2 * gap
    x = 64 * k - total / 2.0
    for fn, w in zip(letters, widths):
        fn(c, x, base_y, h, GOLD)
        x += w + gap

    # Roter Balken unten
    c.rect(28 * k, 112 * k, 72 * k, max(1.5, 7 * k), RED, rx=3.5 * k)
    return c.to_rgba()


# ------------------------------------------------------- PNG/ICO-Kodierung --

def _png_chunk(tag, data):
    raw = tag + data
    return (struct.pack(">I", len(data)) + raw
            + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF))


def encode_png(size, rgba):
    """Minimaler PNG-Encoder (RGBA, keine Kompressionsoptimierung nötig)."""
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + rgba[y * size * 4:(y + 1) * size * 4]
                   for y in range(size))
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", zlib.compress(raw, 9))
            + _png_chunk(b"IEND", b""))


def encode_ico(sizes=ICO_SIZES):
    """ICO-Container mit PNG-Einträgen (Windows Vista und neuer)."""
    images = [(s, encode_png(s, draw_icon(s))) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    data = b""
    for s, png in images:
        w = 0 if s >= 256 else s
        h = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32,
                               len(png), offset)
        data += png
        offset += len(png)
    return header + entries + data


def write_ico(path):
    """Schreibt die Icon-Datei (überschreibt vorhandene Datei)."""
    with open(path, "wb") as f:
        f.write(encode_ico())


def write_preview_png(path, size=256):
    """Schreibt eine einzelne PNG-Vorschau (für Tests/Dokumentation)."""
    with open(path, "wb") as f:
        f.write(encode_png(size, draw_icon(size)))
