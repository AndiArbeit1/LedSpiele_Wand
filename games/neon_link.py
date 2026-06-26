"""Neon Link (8x8) -- Farbblock-Combo-Spiel.

Tippe eine Zelle, die mit >=2 gleichfarbigen Nachbarn verbunden ist ->
die ganze Gruppe loest sich auf, Bloecke fallen nach, oben ruecken neue
nach. Groessere Gruppen = mehr Punkte (n*(n+1)). Eine wechselnde
"Challenge-Farbe" (oben als Leiste) gibt bei Treffer doppelte Punkte.
Einzelne Bloecke ohne Gruppe = kleiner Punktabzug. Bomben raeumen das
3x3-Umfeld weg.

Brett: 8 breit x 7 hoch (Reihen 1..7). Reihe 0 = Spielzeit-Leiste, deren
Farbe die aktuelle Challenge-Farbe ist.

Level 1..4 = Spielzeit, Bomben-Wahrscheinlichkeit und Challenge-Tempo.
Score = Punkte (mehr = besser).
"""

import math
import random
import config
from framework import Game, lerp_color


LEVEL_PARAMS = {
    1: dict(time=45.0, bomb_p=0.010, challenge=5.0),
    2: dict(time=38.0, bomb_p=0.020, challenge=4.0),
    3: dict(time=30.0, bomb_p=0.028, challenge=3.0),
    4: dict(time=24.0, bomb_p=0.040, challenge=2.4),
}
TIME_BONUS_PER_CLEAR = 0.2
LONE_PENALTY = 3
BOMB_POINTS_PER_CELL = 5

BOARD_OY = 1                      # Reihe 0 ist die HUD-Leiste
PLAY_W = config.WIDTH            # 8
PLAY_H = config.HEIGHT - 1       # 7

COLORS = [
    (255, 30, 30),
    (40, 220, 80),
    (50, 100, 255),
    (255, 200, 0),
    (220, 0, 200),
]


def _params(level):
    return LEVEL_PARAMS.get(level, LEVEL_PARAMS[2])


class NeonLinkGame(Game):
    name = "Neon Link"
    color = (255, 0, 255)           # Magenta
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = True

    def reset(self):
        self.done = False
        self.params = _params(self.level)
        self.elapsed = 0.0
        self.score = 0
        self.time = self.params["time"]
        self.challenge_color = random.choice(COLORS)
        self.challenge_time = self.params["challenge"]
        self.grid = [[self._rand() for _ in range(PLAY_W)]
                     for _ in range(PLAY_H)]
        self.flash_cells = []
        self.flash_t = 0.0
        self.over = False
        self.over_timer = 0.0

    def _rand(self):
        if random.random() < self.params["bomb_p"]:
            return "bomb"
        return random.choice(COLORS)

    def update(self, dt):
        self.elapsed += dt
        if self.over:
            self.over_timer += dt
            if self.over_timer > 1.0 or self.hal.press_events():
                self.finish(score=self.score)
            return

        self.flash_t = max(0.0, self.flash_t - dt)
        if self.flash_t <= 0:
            self.flash_cells = []

        self.time -= dt
        if self.time <= 0:
            self.time = 0
            self.over = True
            self.hal.play("win")
            return

        self.challenge_time -= dt
        if self.challenge_time <= 0:
            self._new_challenge()

        for x, y in self.hal.press_events():
            gx = x
            gy = y - BOARD_OY
            if 0 <= gx < PLAY_W and 0 <= gy < PLAY_H:
                self._click(gx, gy)

    def _new_challenge(self):
        choices = [c for c in COLORS if c != self.challenge_color]
        self.challenge_color = random.choice(choices)
        self.challenge_time = self.params["challenge"]

    def _click(self, gx, gy):
        cell = self.grid[gy][gx]
        if cell is None:
            return
        if cell == "bomb":
            blast = []
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < PLAY_W and 0 <= ny < PLAY_H:
                        if self.grid[ny][nx] is not None:
                            blast.append((nx, ny))
                        self.grid[ny][nx] = None
            self.score += len(blast) * BOMB_POINTS_PER_CELL
            self.time += TIME_BONUS_PER_CLEAR
            self.flash_cells = blast
            self.flash_t = 0.18
            self.hal.play("kick")
            self._gravity()
            return
        group = self._flood(gx, gy, cell)
        if len(group) >= 2:
            n = len(group)
            pts = n * (n + 1)
            if cell == self.challenge_color:
                pts *= 2
                self._new_challenge()
                self.hal.play("snare")
            else:
                self.hal.play("good")
            self.score += pts
            self.time += TIME_BONUS_PER_CLEAR
            self.flash_cells = list(group)
            self.flash_t = 0.15
            for fx, fy in group:
                self.grid[fy][fx] = None
            self._gravity()
        else:
            self.score = max(0, self.score - LONE_PENALTY)
            self.flash_cells = [(gx, gy)]
            self.flash_t = 0.15
            self.hal.play("bad")

    def _flood(self, gx, gy, color):
        seen = {(gx, gy)}
        stack = [(gx, gy)]
        while stack:
            cx, cy = stack.pop()
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < PLAY_W and 0 <= ny < PLAY_H
                        and (nx, ny) not in seen
                        and self.grid[ny][nx] == color):
                    seen.add((nx, ny))
                    stack.append((nx, ny))
        return seen

    def _gravity(self):
        for col in range(PLAY_W):
            stack_col = [self.grid[r][col] for r in range(PLAY_H)
                         if self.grid[r][col] is not None]
            pad = PLAY_H - len(stack_col)
            new_col = [self._rand() for _ in range(pad)] + stack_col
            for r in range(PLAY_H):
                self.grid[r][col] = new_col[r]

    def render(self):
        # HUD-Leiste (Reihe 0): Laenge = Restzeit, Farbe = Challenge-Farbe.
        frac = max(0.0, self.time / self.params["time"])
        lit = int(round(frac * config.WIDTH))
        cpulse = 0.6 + 0.4 * math.sin(self.elapsed * 6)
        bar_col = tuple(int(c * cpulse) for c in self.challenge_color)
        dim = tuple(c // 10 for c in self.challenge_color)
        for x in range(config.WIDTH):
            self.hal.set(x, 0, bar_col if x < lit else dim)

        # Brett.
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 8)
        bomb_v = int(90 + 140 * pulse)
        for gy in range(PLAY_H):
            for gx in range(PLAY_W):
                cell = self.grid[gy][gx]
                py = gy + BOARD_OY
                if cell is None:
                    self.hal.set(gx, py, (0, 0, 0))
                elif cell == "bomb":
                    self.hal.set(gx, py, (bomb_v, bomb_v, bomb_v))
                else:
                    self.hal.set(gx, py, cell)
        if self.flash_t > 0:
            v = int(255 * max(0.0, min(1.0, self.flash_t / 0.18)))
            for fx, fy in self.flash_cells:
                self.hal.set(fx, fy + BOARD_OY, (v, v, v))
