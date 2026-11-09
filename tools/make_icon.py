"""Erzeugt rrc/app_icon.ico vor dem Build (CI und lokale Builds).

Aufruf: python tools/make_icon.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rrc import icon_gen

target = os.path.join(os.path.dirname(__file__), "..", "rrc", "app_icon.ico")
icon_gen.write_ico(os.path.abspath(target))
print(f"Icon erzeugt: {os.path.abspath(target)} "
      f"({os.path.getsize(os.path.abspath(target))} Bytes)")
