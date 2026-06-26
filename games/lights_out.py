"""Lights Out auf dem vollen Schirm (8x8 = config.WIDTH x config.HEIGHT).

Klick auf eine Zelle togglet sie + die 4 direkten Nachbarn (Kreuz).
Ziel: alle Lichter aus.

Statt zufaelligem Verwuerfeln gibt es VIER FESTE Bretter (eines pro Level,
jedes Mal identisch). Alle sind garantiert loesbar: die 8x8-Lights-Out-Matrix
ist invertierbar (Nullraum-Dimension 0), also ist JEDE Stellung eindeutig
loesbar -- die vier Bretter wurden zusaetzlich mit einem GF(2)-Solver
bestaetigt (scratchpad/lo_gen.py). Steigende Schwierigkeit (optimale
Klickzahl 4 / 6 / 10 / 16).

Score = Anzahl Klicks bis Loesung (weniger = besser).
"""

import config
from framework import Game, hsv_to_rgb


# Feste Startbretter pro Level (1 = Licht an). Reihen = y 0..7 oben->unten,
# Spalten = x 0..7 links->rechts.
LEVEL_BOARDS = {
    1: [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 0, 0, 0],
        [0, 0, 1, 1, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    2: [
        [0, 1, 0, 0, 0, 0, 1, 0],
        [1, 1, 1, 0, 0, 1, 1, 1],
        [0, 1, 0, 1, 0, 0, 1, 0],
        [0, 0, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 1, 0],
        [1, 1, 1, 0, 0, 1, 1, 1],
        [0, 1, 0, 0, 0, 0, 1, 0],
    ],
    3: [
        [0, 1, 1, 1, 1, 0, 0, 0],
        [1, 0, 1, 1, 1, 0, 0, 0],
        [1, 1, 1, 0, 0, 1, 0, 0],
        [1, 1, 1, 1, 0, 0, 1, 1],
        [0, 1, 1, 0, 0, 1, 1, 0],
        [1, 1, 1, 0, 1, 1, 1, 1],
        [0, 1, 0, 1, 0, 1, 1, 1],
        [0, 0, 1, 1, 1, 0, 0, 1],
    ],
    4: [
        [1, 1, 1, 1, 1, 1, 1, 0],
        [1, 0, 1, 1, 1, 1, 1, 1],
        [1, 1, 0, 1, 0, 0, 1, 1],
        [0, 0, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 0, 1, 1, 1, 0],
        [1, 1, 1, 1, 0, 0, 1, 1],
        [1, 1, 1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 0, 1, 1],
    ],
}

SOLVED_HOLD = 1.4

LIGHT_ON = (255, 180, 30)
# Aus = ganz leicht rot glimmend (lieber dunkel als zu hell).
LIGHT_OFF = (8, 0, 0)


class LightsOutGame(Game):
    name = "Lights"
    color = (0, 0, 255)             # Blau
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = False        # weniger Klicks = besser

    def reset(self):
        self.done = False
        self.t = 0.0
        self.w = config.WIDTH
        self.h = config.HEIGHT
        board = LEVEL_BOARDS.get(self.level, LEVEL_BOARDS[1])
        # Feste Stellung laden (Kopie, damit das Original unveraendert bleibt).
        self.cells = [[bool(board[y][x]) for x in range(self.w)]
                      for y in range(self.h)]
        self.clicks = 0
        self.solved = False
        self.solved_t = 0.0

    def _toggle(self, gx, gy):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = gx + dx, gy + dy
            if 0 <= nx < self.w and 0 <= ny < self.h:
                self.cells[ny][nx] = not self.cells[ny][nx]

    def _any_on(self):
        return any(self.cells[y][x] for y in range(self.h) for x in range(self.w))

    def update(self, dt):
        self.t += dt
        if self.solved:
            self.solved_t += dt
            if self.solved_t > SOLVED_HOLD:
                self.finish(score=self.clicks)
            return
        for (x, y) in self.hal.press_events():
            self._toggle(x, y)
            self.clicks += 1
            self.hal.play("click")
        if not self._any_on():
            self.solved = True
            self.hal.play("win")

    def render(self):
        if self.solved:
            for y in range(self.h):
                for x in range(self.w):
                    hue = ((x + y) * 0.12 + self.solved_t * 0.7) % 1.0
                    self.hal.set(x, y, hsv_to_rgb(hue, 1.0, 0.7))
            return
        for y in range(self.h):
            for x in range(self.w):
                self.hal.set(x, y, LIGHT_ON if self.cells[y][x] else LIGHT_OFF)
