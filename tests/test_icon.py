"""Tests für den Icon-Generator (0.4.5)."""
import os
import tempfile
import unittest

from rrc import icon_gen


class TestIconGenerator(unittest.TestCase):
    def test_ico_container_valid(self):
        data = icon_gen.encode_ico()
        # ICONDIR: reserviert 0, Typ 1 (Icon), Anzahl Einträge = Anzahl Größen
        self.assertEqual(data[0:2], b"\x00\x00")
        self.assertEqual(data[2:4], b"\x01\x00")
        n = int.from_bytes(data[4:6], "little")
        self.assertEqual(n, len(icon_gen.ICO_SIZES))
        # erster Eintrag (beginnt bei Byte 6) zeigt auf ein PNG
        off = int.from_bytes(data[6 + 12:6 + 16], "little")
        self.assertTrue(data[off:off + 8].startswith(b"\x89PNG"))

    def test_all_sizes_render(self):
        for s in icon_gen.ICO_SIZES:
            rgba = icon_gen.draw_icon(s)
            self.assertEqual(len(rgba), s * s * 4)
            # Hintergrundkachel füllt die Fläche (Ecken bleiben frei)
            opaque = sum(1 for i in range(3, len(rgba), 4) if rgba[i] == 255)
            self.assertGreater(opaque, s * s * 0.55)

    def test_gold_and_red_present(self):
        rgba = icon_gen.draw_icon(128)
        colors = {tuple(rgba[i:i + 4]) for i in range(0, len(rgba), 4)}
        self.assertIn(icon_gen.GOLD, colors)
        self.assertIn(icon_gen.RED, colors)

    def test_write_ico(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "test.ico")
            icon_gen.write_ico(p)
            self.assertGreater(os.path.getsize(p), 1000)
            icon_gen.write_preview_png(os.path.join(d, "t.png"), 32)
            self.assertGreater(os.path.getsize(os.path.join(d, "t.png")), 100)


if __name__ == "__main__":
    unittest.main()
