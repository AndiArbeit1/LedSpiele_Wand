"""Neon Mind (8x8) -- schnelles Merk-/Reaktionsspiel auf Zeit.

Drei Runden, simpel:
  1. Kurz blitzt ein Ziel-Symbol in der Mitte auf (je hoeher das Level,
     desto kuerzer).
  2. Dann erscheinen vier Symbole in den Ecken. Tippe so schnell wie
     moeglich das, das eben gezeigt wurde.
  3. Die gebrauchte Zeit wird addiert. Fehlklick = Zeitstrafe.

Nach drei Runden ist Schluss. Score = gebrauchte Gesamtzeit in Zehntel-
sekunden -- weniger ist besser.

Level 1..4: kuerzeres Reveal = schwerer zu merken.
"""

import random
import config
from framework import Game


ROUNDS = 3
READY_SECONDS = 0.6
WRONG_PENALTY = 1.0   # Sekunden Strafe pro Fehlklick

LEVEL_REVEAL = {1: 0.90, 2: 0.65, 3: 0.45, 4: 0.32}

SLOTS = [(0, 1), (5, 1), (0, 5), (5, 5)]
CENTER_SLOT = (2, 3)

SYMBOLS = {
    "square":  [(1, 1, 1), (1, 0, 1), (1, 1, 1)],
    "x":       [(1, 0, 1), (0, 1, 0), (1, 0, 1)],
    "plus":    [(0, 1, 0), (1, 1, 1), (0, 1, 0)],
    "diamond": [(0, 1, 0), (1, 0, 1), (0, 1, 0)],
    "h":       [(1, 0, 1), (1, 1, 1), (1, 0, 1)],
    "t":       [(1, 1, 1), (0, 1, 0), (0, 1, 0)],
    "u":       [(1, 0, 1), (1, 0, 1), (1, 1, 1)],
    "l":       [(1, 0, 0), (1, 0, 0), (1, 1, 1)],
    "slash":   [(0, 0, 1), (0, 1, 0), (1, 0, 0)],
    "bar":     [(0, 0, 0), (1, 1, 1), (0, 0, 0)],
}
SYMBOL_COLORS = {
    "square":  (255, 30, 30),
    "x":       (40, 110, 255),
    "plus":    (30, 230, 60),
    "diamond": (255, 220, 0),
    "h":       (255, 60, 180),
    "t":       (255, 130, 0),
    "u":       (0, 220, 220),
    "l":       (180, 255, 60),
    "slash":   (200, 60, 255),
    "bar":     (240, 240, 240),
}
SYMBOL_NAMES = list(SYMBOLS.keys())


class NeonMindGame(Game):
    name = "Neon Mind"
    color = (0, 255, 255)           # Cyan
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = False   # weniger Zeit = besser

    def reset(self):
        self.done = False
        self.reveal = LEVEL_REVEAL.get(self.level, LEVEL_REVEAL[2])
        self.total_time = 0.0
        self.round = 0
        self.wrong_flash = 0.0
        self._new_round()

    def _new_round(self):
        self.target = random.choice(SYMBOL_NAMES)
        others = [s for s in SYMBOL_NAMES if s != self.target]
        random.shuffle(others)
        self.options = [self.target] + others[:3]
        random.shuffle(self.options)
        self.phase = "ready"
        self.phase_t = READY_SECONDS
        self.choose_t = 0.0
        self.hal.press_events()
        self.round += 1
        self.hal.play("hat")

    def update(self, dt):
        self.wrong_flash = max(0.0, self.wrong_flash - dt)

        if self.phase == "ready":
            self.phase_t -= dt
            if self.phase_t <= 0:
                self.phase = "reveal"
                self.phase_t = self.reveal
                self.hal.play("snare")
        elif self.phase == "reveal":
            self.phase_t -= dt
            if self.phase_t <= 0:
                self.phase = "choose"
                self.choose_t = 0.0
                self.hal.press_events()
        elif self.phase == "choose":
            self.choose_t += dt
            self._process_presses()

    def _process_presses(self):
        for x, y in self.hal.press_events():
            idx = self._slot_at(x, y)
            if idx is None:
                continue
            if self.options[idx] == self.target:
                self.total_time += self.choose_t
                self.hal.play("good")
                if self.round >= ROUNDS:
                    # Zeit in Zehntelsekunden als Score (weniger = besser).
                    self.finish(score=int(round(self.total_time * 10)))
                else:
                    self._new_round()
            else:
                self.total_time += WRONG_PENALTY
                self.wrong_flash = 0.25
                self.hal.play("bad")
            return

    def _slot_at(self, x, y):
        for idx, (sx, sy) in enumerate(SLOTS):
            if sx <= x <= sx + 2 and sy <= y <= sy + 2:
                return idx
        return None

    # ---- Render ----
    def render(self):
        # Runden-Fortschritt: ein Punkt je bereits begonnener Runde.
        for i in range(self.round):
            self.hal.set(i, 0, (80, 200, 255))

        if self.wrong_flash > 0:
            v = int(self.wrong_flash * 400)
            for x in range(config.WIDTH):
                self.hal.set(x, config.HEIGHT - 1, (v, 0, 0))

        if self.phase == "reveal":
            self._draw_symbol(CENTER_SLOT[0], CENTER_SLOT[1], self.target, 1.0)
        elif self.phase == "choose":
            for idx, (sx, sy) in enumerate(SLOTS):
                self._draw_symbol(sx, sy, self.options[idx], 1.0)

    def _draw_symbol(self, x0, y0, sym, brightness=1.0):
        pattern = SYMBOLS[sym]
        color = SYMBOL_COLORS[sym]
        c = (int(color[0] * brightness),
             int(color[1] * brightness),
             int(color[2] * brightness))
        for py in range(3):
            for px in range(3):
                if pattern[py][px]:
                    self.hal.set(x0 + px, y0 + py, c)
