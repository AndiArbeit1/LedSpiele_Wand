"""Simon-Farben auf 4x4.

Das 4x4-Feld ist in vier 2x2-Quadranten (Pads) aufgeteilt -- die vier
klassischen Simon-Farben. Der Computer zeigt eine Sequenz, der Spieler
tippt sie nach. Stimmt sie, kommt ein Pad dazu (Sequenz wird laenger).
Ein Fehler beendet das Spiel.

Level 1..4 = Wiedergabe-Tempo (hoeher = schneller, schwerer zu merken).
Score = Laenge der laengsten korrekt wiederholten Sequenz.
"""

import random
import config
from framework import Game


# Pad-Index -> (Basisfarbe, Ton-Frequenz).
PADS = [
    ((220, 30, 30),  330.0),   # 0 TL  rot
    ((30, 220, 60),  415.0),   # 1 TR  gruen
    ((40, 90, 255),  494.0),   # 2 BL  blau
    ((235, 200, 0),  587.0),   # 3 BR  gelb
]

# Tempo pro Level: (Leuchtdauer, Pause dazwischen) in Sekunden.
LEVEL_TIMING = {
    1: (0.55, 0.28),
    2: (0.42, 0.20),
    3: (0.32, 0.14),
    4: (0.24, 0.10),
}


def _pad_for_cell(x, y):
    col = 0 if x < config.WIDTH // 2 else 1
    row = 0 if y < config.HEIGHT // 2 else 1
    return row * 2 + col


def _pad_cells(pad):
    """Liefert die Zellen (x,y) eines Pads (2x2-Quadrant)."""
    half_w = config.WIDTH // 2
    half_h = config.HEIGHT // 2
    cx = (pad % 2) * half_w
    cy = (pad // 2) * half_h
    return [(cx + dx, cy + dy)
            for dy in range(half_h) for dx in range(half_w)]


class SimonGame(Game):
    name = "Simon"
    color = (255, 255, 0)           # Gelb (Pads bleiben innen 4-farbig)
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = True

    def reset(self):
        self.done = False
        self.show_on, self.show_gap = LEVEL_TIMING.get(self.level,
                                                       LEVEL_TIMING[2])
        self.seq = [random.randint(0, 3)]
        self.score = 0
        # Phasen: "show", "input", "good", "over"
        self.phase = "show"
        self.show_i = 0
        self.show_t = 0.0
        self.lit = None         # aktuell leuchtendes Pad in show-Phase
        self.input_i = 0
        self.press_pad = None   # Pad das der Spieler gerade beruehrt
        self.press_t = 0.0
        self.phase_t = 0.0

    def _next_round(self):
        self.seq.append(random.randint(0, 3))
        self.phase = "show"
        self.show_i = 0
        self.show_t = 0.0
        self.lit = None

    def update(self, dt):
        self.phase_t += dt
        self.press_t = max(0.0, self.press_t - dt)
        if self.press_t == 0.0:
            self.press_pad = None

        if self.phase == "show":
            self._update_show(dt)
        elif self.phase == "input":
            self._update_input(dt)
        elif self.phase == "good":
            if self.phase_t > 0.5:
                self.phase_t = 0.0
                self._next_round()
        elif self.phase == "over":
            if self.phase_t > 1.3:
                self.finish(score=self.score)

    def _update_show(self, dt):
        self.show_t += dt
        cycle = self.show_on + self.show_gap
        # Welcher Schritt sind wir, und leuchtet das Pad gerade?
        step = int(self.show_t // cycle)
        if step >= len(self.seq):
            self.phase = "input"
            self.phase_t = 0.0
            self.input_i = 0
            self.lit = None
            return
        in_cycle = self.show_t - step * cycle
        if in_cycle < self.show_on:
            pad = self.seq[step]
            if self.lit != pad:
                self.lit = pad
                _, freq = PADS[pad]
                self.hal.play_freq(freq, dur=self.show_on, vol=0.5)
        else:
            self.lit = None

    def _update_input(self, dt):
        for (x, y) in self.hal.press_events():
            pad = _pad_for_cell(x, y)
            self.press_pad = pad
            self.press_t = 0.18
            _, freq = PADS[pad]
            self.hal.play_freq(freq, dur=0.18, vol=0.5)
            if pad == self.seq[self.input_i]:
                self.input_i += 1
                if self.input_i >= len(self.seq):
                    # Ganze Sequenz korrekt.
                    self.score = len(self.seq)
                    self.hal.play("good")
                    self.phase = "good"
                    self.phase_t = 0.0
                    return
            else:
                self.hal.play("bad")
                self.phase = "over"
                self.phase_t = 0.0
                return

    def render(self):
        if self.phase == "over":
            # Rotes Aufblinken.
            v = int(max(0, 200 - self.phase_t * 200))
            self.hal.fill((v, 0, 0))
            return

        for pad in range(4):
            base, _ = PADS[pad]
            bright = 0.12
            if self.phase == "show" and self.lit == pad:
                bright = 1.0
            elif self.phase == "input" and self.press_pad == pad:
                bright = 1.0
            elif self.phase == "good":
                bright = 0.6
            col = tuple(int(c * bright) for c in base)
            for (x, y) in _pad_cells(pad):
                self.hal.set(x, y, col)
