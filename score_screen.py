"""Ergebnis-Anzeige auf 8x8.

Zeigt am Ende die erreichte ZAHL an -- je nach Spiel sind das Punkte,
Zuege oder die Zeit (in Zehntelsekunden). Passt die Zahl auf den Schirm
(<= 8 breit), steht sie still in der Mitte, sonst laeuft sie als Laufband
durch.

    neuer Rekord  -> Ziffern in wechselnden Regenbogenfarben
    sonst         -> Ziffern ruhig in der Spielfarbe (kein Regenbogen)

Endet nach kurzer Zeit oder auf Tastendruck. Liefert True, wenn der
Menue-Halten-Taster ausgeloest wurde.
"""

import math
import time
import config
from framework import hsv_to_rgb, draw_text_5x7, text_width_5x7_gap


GRACE_SECONDS = 0.8      # anfangs KEINE Tipps annehmen -> der Score wird
                         # sicher gesehen (sonst klicken die "Todes-Tipps"
                         # ihn sofort weg, bevor man ihn liest).
AUTO_RETURN = 10.0       # Fallback ohne Tipp -> zurueck zur Lobby/Menue
SCROLL_SPEED = 7.0       # Zellen/s fuers Laufband (laeuft jetzt in Schleife)
Y0 = (config.HEIGHT - 7) // 2


def run_score(hal, score=None, is_record=False, base_color=(255, 220, 60)):
    text = "" if score is None else str(int(score))
    width = text_width_5x7_gap(text)
    static = width <= config.WIDTH
    start = time.monotonic()
    last = start
    t = 0.0

    while True:
        now = time.monotonic()
        dt = now - last
        last = now
        t += dt

        hal.poll()
        if hal.menu_requested():
            return True
        elapsed = now - start
        presses = hal.press_events()   # jeden Frame leeren (Puffer abbauen)
        # In der Schonzeit werden Tipps ignoriert -> der Score steht sicher da.
        if elapsed > GRACE_SECONDS and presses:
            return False
        if elapsed > AUTO_RETURN:
            return False

        if static:
            x = (config.WIDTH - width) // 2
        else:
            # Endlos-Laufband, bis getippt oder Timeout.
            span = width + config.WIDTH
            x = config.WIDTH - (SCROLL_SPEED * t) % span

        if is_record:
            col = hsv_to_rgb((t * 0.6) % 1.0, 1.0, 0.85)
        else:
            # Ruhiges Pulsieren in der Spielfarbe.
            p = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 3.0))
            col = tuple(min(255, int(c * p)) for c in base_color)

        hal.clear()
        if text:
            draw_text_5x7(hal, text, int(round(x)), Y0, col)
        else:
            # Kein Score (Notfall): kurzes ruhiges Aufleuchten.
            hal.fill(tuple(c // 3 for c in base_color))
            if now - start > 1.0:
                return False
        hal.show()
        time.sleep(1.0 / 30)
