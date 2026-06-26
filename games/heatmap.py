"""Heatmap (8x8) -- gemeinsamer, DAUERHAFTER Tipp-Punkt ueber alle Spieler.

  - Der Schirm ist zunaechst LEER (alles aus), sobald das Spiel gewaehlt ist.
  - Es passiert nichts, bis jemand einen (scheinbar zufaelligen) Taster drueckt.
  - Dann wird die GESAMTE Heatmap gezeigt: der aktuelle Druck PLUS alle
    Druecke aller Spieler davor -- eine Farbe (Orange, REVEAL_COLOR), die mit
    der Haeufigkeit immer heller wird. Der eigene Druck blinkt weiss, damit
    man ihn im Muster wiederfindet.
  - Nach REVEAL_SECONDS geht es automatisch zurueck ins Menue.

Im Gegensatz zu frueher werden die Daten DAUERHAFT gesammelt (heatmap.json
neben dem Projekt). So sieht jeder neue Spieler, wo alle vorherigen schon
draufgedrueckt haben -- und dass die "zufaellige" Wahl gar nicht so zufaellig
ist.
"""

import os
import json
import threading

import config
from framework import Game


REVEAL_SECONDS = 5.0
MIN_VISIBLE = 0.12

# Aufdeck-Farbe im Spiel: EINE Farbe, die mit der Druckhaeufigkeit immer
# heller wird (das Menue-Kachel-Icon nutzt weiter HeatmapGame.color).
REVEAL_COLOR = (255, 140, 0)    # Orange

# heatmap.json liegt im Projekt-Wurzelverzeichnis (eine Ebene ueber games/),
# neben scores.json -- damit die Daemon-Instanz und Tests denselben Stand
# teilen und es Neustarts ueberlebt.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.path.join(_ROOT, "heatmap.json")


def _load_counts():
    """Kumulative Zaehler aller bisherigen Spieler laden (sonst Nullen)."""
    grid = [[0] * config.WIDTH for _ in range(config.HEIGHT)]
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("counts")
        if (isinstance(rows, list) and len(rows) == config.HEIGHT
                and all(isinstance(r, list) and len(r) == config.WIDTH
                        for r in rows)):
            for y in range(config.HEIGHT):
                for x in range(config.WIDTH):
                    grid[y][x] = int(rows[y][x])
    except Exception:
        # Keine/kaputte Datei oder geaenderte Groesse -> bei null anfangen.
        pass
    return grid


def _save_counts(grid):
    try:
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"counts": grid}, f)
        os.replace(tmp, _PATH)
    except Exception as e:
        print("[heatmap] Speichern fehlgeschlagen: {}".format(e))


def _save_counts_async(grid):
    """Speichert im Hintergrund -- der SD-Schreibzugriff darf den Game-Loop
    im Moment des Drueckens nicht blockieren (kein Ruckeln beim Aufdecken)."""
    snapshot = [row[:] for row in grid]
    threading.Thread(target=_save_counts, args=(snapshot,),
                     daemon=True).start()


class HeatmapGame(Game):
    name = "Heatmap"
    color = (138, 43, 226)          # Violett
    supports_multiplayer = False
    has_score_screen = False
    has_levels = False        # keine Level-Auswahl -- direkt rein

    def reset(self):
        self.done = False
        self.phase = "wait"   # wait (leer) | reveal (aufgedeckt)
        self.timer = 0.0
        self.counts = _load_counts()   # alle Spieler davor
        self.current = set()           # die Zelle(n) dieses Spielers
        self._reveal = None            # vorberechnetes Farbgitter (reveal)

    def _build_reveal(self):
        """Einmal beim Aufdecken: festes Helligkeitsgitter bauen -- EINE Farbe
        (REVEAL_COLOR), die mit der Druckhaeufigkeit immer heller wird.
        Danach kostet jeder Frame nur noch Blitten + Blink-Overlay (kein Lag)."""
        cmax = 0
        for row in self.counts:
            for v in row:
                if v > cmax:
                    cmax = v
        base = REVEAL_COLOR
        grid = [[None] * config.WIDTH for _ in range(config.HEIGHT)]
        if cmax > 0:
            inv = 1.0 / cmax
            for y in range(config.HEIGHT):
                for x in range(config.WIDTH):
                    c = self.counts[y][x]
                    if c == 0:
                        continue
                    k = MIN_VISIBLE + (1 - MIN_VISIBLE) * (c * inv)
                    grid[y][x] = (int(base[0] * k), int(base[1] * k),
                                  int(base[2] * k))
        self._reveal = grid

    def update(self, dt):
        if self.phase == "wait":
            # Warten, bis jemand drueckt. Der erste Druck zaehlt fuer diese
            # Runde, wird dauerhaft gespeichert und deckt die Heatmap auf.
            presses = self.hal.press_events()
            if presses:
                for (x, y) in presses:
                    self.counts[y][x] += 1
                    self.current.add((x, y))
                self._build_reveal()           # Bild fertig rechnen ...
                _save_counts_async(self.counts)  # ... Speichern nebenher
                self.phase = "reveal"
                self.timer = REVEAL_SECONDS
                self.hal.play("good")
            return

        # reveal: nur noch ablaufen lassen, weitere Druecke ignorieren.
        self.timer -= dt
        if self.timer <= 0:
            self.finish()

    def render(self):
        if self.phase == "wait":
            return  # komplett leer

        # Vorberechnetes Heatmap-Bild blitten.
        grid = self._reveal
        if grid:
            for y in range(config.HEIGHT):
                row = grid[y]
                for x in range(config.WIDTH):
                    col = row[x]
                    if col is not None:
                        self.hal.set(x, y, col)

        # Eigener Druck blinkt weiss -> man findet sich im Muster wieder.
        if int(self.timer * 4) % 2 == 0:
            for (x, y) in self.current:
                self.hal.set(x, y, (255, 255, 255))
