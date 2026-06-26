"""Hauptmenue auf 8x8 fuer bis zu acht Spiele.

Acht Kacheln in einem 2x4-Raster (2 Spalten, 4 Reihen). Jede Kachel ist
4 breit x 2 hoch und traegt die Farbe ihres Spiels. Ein Druck irgendwo in
einer Kachel startet das zugehoerige Spiel.

Kachel-Index (= Reihenfolge in games.ALL):
    0 oben-links     1 oben-rechts
    2               3
    4               5
    6 unten-links    7 unten-rechts

Fuer die Level-Auswahl (vier Level) wird weiter das 2x2-Quadranten-Layout
genutzt -- die Helfer _quadrant_index/_quadrant_cells bleiben deshalb hier.
"""

import math
import time
import config
import lobbymusic


TILE_W = 4
TILE_H = 2
TILE_COLS = 2
TILE_ROWS = 4


def _tile_index(x, y):
    col = min(TILE_COLS - 1, x // TILE_W)
    row = min(TILE_ROWS - 1, y // TILE_H)
    return row * TILE_COLS + col


def _tile_cells(i):
    col = i % TILE_COLS
    row = i // TILE_COLS
    cx = col * TILE_W
    cy = row * TILE_H
    return [(cx + dx, cy + dy)
            for dy in range(TILE_H) for dx in range(TILE_W)]


# ---- 2x2-Quadranten (fuer die Level-Auswahl) ----

def _quadrant_index(x, y):
    col = 0 if x < config.WIDTH // 2 else 1
    row = 0 if y < config.HEIGHT // 2 else 1
    return row * 2 + col


def _quadrant_cells(i):
    half_w = config.WIDTH // 2
    half_h = config.HEIGHT // 2
    cx = (i % 2) * half_w
    cy = (i // 2) * half_h
    return [(cx + dx, cy + dy)
            for dy in range(half_h) for dx in range(half_w)]


def menu_loop(hal, games):
    """Blockiert bis ein Spiel gewaehlt wird. Liefert die Game-Klasse."""
    if not games:
        return None
    n = min(TILE_COLS * TILE_ROWS, len(games))
    last = time.monotonic()
    t = 0.0
    current_track = None
    next_music_check = 0.0

    while True:
        now = time.monotonic()
        dt = now - last
        last = now
        t += dt

        # Lobby-Musik: den (per Admin) gewaehlten Track in Endlosschleife
        # spielen. ~1x/s pruefen, ob umgestellt wurde -> ggf. neu starten.
        # main.py stoppt die Musik beim Spielstart (hal.stop_music()).
        if t >= next_music_check:
            next_music_check = t + 1.0
            sel = lobbymusic.get_selected_id()
            if sel != current_track:
                current_track = sel
                f = lobbymusic.selected_file()
                if f:
                    hal.play_music(f, loops=-1, vol=1.0)
                else:
                    hal.stop_music()  # "Aus" gewaehlt -> Stille in der Lobby.

        hal.poll()
        hal.menu_requested()  # Flag wegputzen, wir SIND im Menue.

        for x, y in hal.press_events():
            i = _tile_index(x, y)
            if i < n:
                hal.play("click")
                return games[i]

        hal.clear()
        # Sanfte Welle, die diagonal ueber die Kacheln laeuft, plus
        # eigener Puls je Kachel -> lebendig, aber nicht hektisch.
        for i in range(n):
            base = games[i].color
            phase = t * 1.8 + i * 0.7
            pulse = 0.5 + 0.35 * math.sin(phase)
            for (cx, cy) in _tile_cells(i):
                wave = 0.12 * math.sin(t * 2.6 - (cx + cy) * 0.5)
                k = max(0.0, min(1.0, pulse + wave))
                col = tuple(min(255, int(c * k)) for c in base)
                hal.set(cx, cy, col)
        hal.show()
        time.sleep(1.0 / 30)
