"""Level-Auswahl auf 8x8 als vier 4x4-Kacheln (Quadranten).

Gleiches Layout wie das Haupt-Menue: vier 4x4-Quadranten, einer pro Level.
    oben links  = Level 1 (cyan, leicht)
    oben rechts = Level 2 (gruen)
    unten links = Level 3 (gelb)
    unten rechts= Level 4 (rot, schwer)
Ein Druck in eine Kachel waehlt das Level. Ruhige, fuer alle Kacheln
gleichmaessige Animation (kein nervoeses Flackern).
"""

import math
import time
import config
from menu import _quadrant_index, _quadrant_cells


# Eine Farbe pro Level (leicht -> schwer).
LEVEL_COLORS = [
    ( 80, 200, 255),  # 1 - cyan
    ( 80, 255, 120),  # 2 - gruen
    (255, 200,  50),  # 3 - gelb
    (255,  70,  70),  # 4 - rot
]


def level_loop(hal):
    """Liefert Level 1..NUM_LEVELS. None = zurueck zum Menue."""
    n = min(4, config.NUM_LEVELS)
    last = time.monotonic()
    t = 0.0

    while True:
        now = time.monotonic()
        dt = now - last
        last = now
        t += dt

        hal.poll()
        if hal.menu_requested():
            return None

        for px, py in hal.press_events():
            i = _quadrant_index(px, py)
            if i < n:
                hal.play("click")
                return i + 1

        # Gleichmaessiger Puls fuer ALLE Kacheln (gleiche Phase).
        pulse = 0.6 + 0.25 * math.sin(t * 1.6)
        hal.clear()
        for i in range(n):
            base = LEVEL_COLORS[i % len(LEVEL_COLORS)]
            col = tuple(min(255, int(c * pulse)) for c in base)
            for (cx, cy) in _quadrant_cells(i):
                hal.set(cx, cy, col)
        hal.show()
        time.sleep(1.0 / 30)
