"""Labyrinth (scrollend) -- der Spieler bleibt immer in der MITTE des
Schirms, das Labyrinth bewegt sich um ihn herum.

Steuerung ueber die vier RAENDER des 8x8-Schirms (jeder Tipp = ein Feld):
  - rechter Rand  -> nach rechts
  - linker Rand   -> nach links
  - oberer Rand   -> nach oben
  - unterer Rand  -> nach unten

Das Labyrinth ist GROESSER als 8x8 (je hoeher das Level, desto groesser);
man sieht immer nur einen 8x8-Ausschnitt, zentriert auf dem Spieler. Ziel:
vom Start (oben links) zum Ausgang (gruen, unten rechts). Score = gebrauchte
Zeit in Zehntelsekunden -- weniger ist besser.

Level 1..4 = Labyrinth-Groesse (groesser = schwerer).
"""

import random
import config
from framework import Game


# Der Spieler sitzt immer auf dieser Schirm-Position (Mitte).
CX = config.WIDTH // 2
CY = config.HEIGHT // 2

# Labyrinth-Groesse je Level (ungerade fuer den Generator, alle > 8x8).
LEVEL_SIZE = {1: 11, 2: 15, 3: 21, 4: 27}

WALL_COLOR = (20, 24, 70)       # gedaempftes Blau = Wand / ausserhalb
PLAYER_COLOR = (0, 255, 255)    # Cyan = Spieler (Mitte)
GOAL_COLOR = (0, 255, 0)        # Gruen = Ausgang


def _gen_maze(w, h):
    """Perfektes Labyrinth per Recursive Backtracker. 1 = Wand, 0 = Weg.
    w, h ungerade; die "Raum"-Zellen liegen auf ungeraden Koordinaten."""
    maze = [[1] * w for _ in range(h)]
    maze[1][1] = 0
    stack = [(1, 1)]
    while stack:
        x, y = stack[-1]
        nbrs = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nx, ny = x + dx, y + dy
            if 1 <= nx < w - 1 and 1 <= ny < h - 1 and maze[ny][nx] == 1:
                nbrs.append((nx, ny, dx, dy))
        if nbrs:
            nx, ny, dx, dy = random.choice(nbrs)
            maze[y + dy // 2][x + dx // 2] = 0   # Wand dazwischen oeffnen
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()
    return maze


class LabyrinthGame(Game):
    name = "Labyrinth"
    color = (0, 255, 255)           # Cyan
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = False        # weniger Zeit = besser

    def reset(self):
        self.done = False
        size = LEVEL_SIZE.get(self.level, LEVEL_SIZE[2])
        self.w = self.h = size
        self.maze = _gen_maze(self.w, self.h)
        self.px, self.py = 1, 1                      # Spieler-Startfeld
        self.gx, self.gy = self.w - 2, self.h - 2    # Ausgang
        self.t = 0.0
        self.win = False
        self.win_t = 0.0
        self.move_flash = 0.0
        self.blocked_flash = 0.0

    def _dir_for(self, x, y):
        """Rand-Tipp -> Richtung (dx, dy); Tipp im Inneren -> None."""
        if x == config.WIDTH - 1:
            return (1, 0)
        if x == 0:
            return (-1, 0)
        if y == 0:
            return (0, -1)
        if y == config.HEIGHT - 1:
            return (0, 1)
        return None

    def update(self, dt):
        if self.win:
            self.win_t += dt
            if self.win_t > 1.2:
                self.finish(score=int(self.t * 10))   # Zehntelsekunden
            return

        self.t += dt
        self.move_flash = max(0.0, self.move_flash - dt)
        self.blocked_flash = max(0.0, self.blocked_flash - dt)

        for (x, y) in self.hal.press_events():
            d = self._dir_for(x, y)
            if d is None:
                continue
            tx, ty = self.px + d[0], self.py + d[1]
            if 0 <= tx < self.w and 0 <= ty < self.h and self.maze[ty][tx] == 0:
                self.px, self.py = tx, ty
                self.move_flash = 0.08
                self.hal.play("click")
                if (self.px, self.py) == (self.gx, self.gy):
                    self.win = True
                    self.win_t = 0.0
                    self.hal.play("win")
                    return
            else:
                self.blocked_flash = 0.10
                self.hal.play("bad")

    def render(self):
        if self.win:
            # Ganzer Schirm pulst gruen.
            v = int(120 + 135 * abs(((self.win_t * 3) % 1.0) - 0.5) * 2)
            for sy in range(config.HEIGHT):
                for sx in range(config.WIDTH):
                    self.hal.set(sx, sy, (0, v, 0))
            return

        # 8x8-Ausschnitt zeichnen, zentriert auf dem Spieler.
        for sy in range(config.HEIGHT):
            for sx in range(config.WIDTH):
                wx = self.px + (sx - CX)
                wy = self.py + (sy - CY)
                if not (0 <= wx < self.w and 0 <= wy < self.h):
                    self.hal.set(sx, sy, WALL_COLOR)        # ausserhalb = Wand
                elif (wx, wy) == (self.gx, self.gy):
                    self.hal.set(sx, sy, GOAL_COLOR)
                elif self.maze[wy][wx] == 1:
                    self.hal.set(sx, sy, WALL_COLOR)
                # Weg (0) -> bleibt aus (hal.clear())

        # Spieler immer in der Mitte.
        if self.blocked_flash > 0:
            pcol = (255, 60, 0)         # kurz rot = Wand im Weg
        elif self.move_flash > 0:
            pcol = (180, 255, 255)
        else:
            pcol = PLAYER_COLOR
        self.hal.set(CX, CY, pcol)
