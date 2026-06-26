"""Flappy (8x8).

Ein Vogel haengt in einer festen Spalte (links). Von rechts scrollen
"Roehren" mit einer Luecke heran. Tippe IRGENDWO -> der Vogel flattert
nach oben, sonst zieht ihn die Schwerkraft nach unten. Fliege durch die
Luecken. Eine Beruehrung oder Aufschlag = sofort vorbei (ein Leben).

Es wird IMMER schneller: mit jeder passierten Roehre steigt das Tempo
(level-abhaengig), und ab ein paar Punkten wird die Luecke enger.

Score = Anzahl passierter Roehren (mehr = besser).
Level 1..4 = Start-Tempo, Beschleunigung und Luecken-Groesse.
"""

import random
import config
from framework import Game


BIRD_X = 2
GRAVITY = 18.0
FLAP_V = -4.7
MAX_SPEED = 9.0

# base  = Start-Tempo (Zellen/s)
# accel = Tempo-Zuwachs pro passierter Roehre
# gap   = Start-Luecke (Zellen), schrumpft mit dem Score
# space = Abstand zwischen Roehren (Zellen)
LEVEL_PARAMS = {
    1: dict(base=2.6, accel=0.10, gap=5, space=6),
    2: dict(base=3.4, accel=0.18, gap=4, space=5),
    3: dict(base=4.4, accel=0.28, gap=3, space=5),
    4: dict(base=5.6, accel=0.40, gap=3, space=4),
}

BIRD_COLOR = (255, 210, 40)
BIRD_FLAP_COLOR = (255, 255, 180)
PIPE_COLOR = (40, 200, 80)
PIPE_EDGE = (120, 255, 150)


class _Pipe:
    __slots__ = ("x", "gap_y", "gap_h", "passed")

    def __init__(self, x, gap_y, gap_h):
        self.x = x
        self.gap_y = gap_y
        self.gap_h = gap_h
        self.passed = False


class FlappyGame(Game):
    name = "Flappy"
    color = (255, 165, 0)           # Orange
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = True

    def reset(self):
        self.done = False
        self.params = LEVEL_PARAMS.get(self.level, LEVEL_PARAMS[2])
        self.bird_y = config.HEIGHT / 2.0
        self.vy = 0.0
        self.pipes = []
        self.score = 0
        self.flap_flash = 0.0
        self.over = False
        self.over_timer = 0.0
        self.bad_flash = 0.0
        self._spawn_pipe(config.WIDTH + 1)

    def _cur_speed(self):
        return min(MAX_SPEED, self.params["base"] + self.score * self.params["accel"])

    def _cur_gap(self):
        # Luecke schrumpft mit steigendem Score, mindestens 2.
        return max(2, self.params["gap"] - self.score // 8)

    def _spawn_pipe(self, x):
        gap_h = self._cur_gap()
        gap_y = random.randint(0, config.HEIGHT - gap_h)
        self.pipes.append(_Pipe(float(x), gap_y, gap_h))

    def update(self, dt):
        if self.over:
            self.over_timer += dt
            if self.over_timer > 1.2:
                self.finish(score=self.score)
            return

        self.flap_flash = max(0.0, self.flap_flash - dt)
        self.bad_flash = max(0.0, self.bad_flash - dt)

        # Flap bei irgendeinem Tastendruck.
        if self.hal.press_events():
            self.vy = FLAP_V
            self.flap_flash = 0.12
            self.hal.play("hat")

        # Physik.
        self.vy += GRAVITY * dt
        self.bird_y += self.vy * dt

        if self.bird_y <= 0:
            self.bird_y = 0
            self.vy = 0
        if self.bird_y >= config.HEIGHT - 1:
            self.bird_y = config.HEIGHT - 1
            self._die()
            return

        # Roehren bewegen (Tempo steigt mit Score).
        speed = self._cur_speed()
        for p in self.pipes:
            p.x -= speed * dt

        by = int(round(self.bird_y))
        for p in self.pipes:
            if not p.passed and p.x <= BIRD_X:
                p.passed = True
                if p.gap_y <= by < p.gap_y + p.gap_h:
                    self.score += 1
                    self.hal.play("good")
                else:
                    self._die()
                    return

        self.pipes = [p for p in self.pipes if p.x > -1]
        if not self.pipes or \
                (config.WIDTH - max(p.x for p in self.pipes)) >= self.params["space"]:
            self._spawn_pipe(config.WIDTH + 1)

    def _die(self):
        self.over = True
        self.bad_flash = 0.4
        self.hal.play("miss")

    def render(self):
        if self.over and self.bad_flash > 0:
            v = int(min(255, self.bad_flash * 500))
            self.hal.fill((v, 0, 0))
            return

        for p in self.pipes:
            px = int(round(p.x))
            if not (0 <= px < config.WIDTH):
                continue
            for y in range(config.HEIGHT):
                if p.gap_y <= y < p.gap_y + p.gap_h:
                    continue
                edge = (y == p.gap_y - 1) or (y == p.gap_y + p.gap_h)
                self.hal.set(px, y, PIPE_EDGE if edge else PIPE_COLOR)

        by = int(round(self.bird_y))
        col = BIRD_FLAP_COLOR if self.flap_flash > 0 else BIRD_COLOR
        self.hal.set(BIRD_X, by, col)
