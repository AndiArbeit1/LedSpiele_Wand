"""Whack-a-Mole auf 4x4.

Ein "Maulwurf" leuchtet kurz an einer zufaelligen Stelle. Wird der Taster
rechtzeitig getroffen -> Punkt + sofort der naechste. Verpasst oder daneben
-> ein Leben weg (kurzer roter Flash). Mit steigendem Score sinkt die
Reaktionszeit (TTL).

Voller 4x4-Schirm fuer den Maulwurf, kein Dauer-HUD (zu klein); Leben und
Treffer werden ueber Flashes vermittelt. Score = Treffer.

Level 1..4 = Start-Schwierigkeit.
"""

import random
import config
from framework import Game


LEVEL_PARAMS = {
    1: dict(ttl_start=2.0, ttl_min=1.2, ramp=0.03),
    2: dict(ttl_start=1.6, ttl_min=0.9, ramp=0.04),
    3: dict(ttl_start=1.2, ttl_min=0.65, ramp=0.05),
    4: dict(ttl_start=0.9, ttl_min=0.40, ramp=0.06),
}
INIT_LIVES = 1


class WhackGame(Game):
    name = "Whack"
    color = (0, 255, 0)             # Gruen
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = True

    def reset(self):
        self.done = False
        self.params = LEVEL_PARAMS.get(self.level, LEVEL_PARAMS[2])
        self.score = 0
        self.lives = INIT_LIVES
        self.over = False
        self.over_timer = 0.0
        self.flash = 0.0       # gruen bei Treffer
        self.bad_flash = 0.0   # rot bei Miss / Fehlklick
        self._spawn()

    def _spawn(self):
        self.mole_x = random.randint(0, config.WIDTH - 1)
        self.mole_y = random.randint(0, config.HEIGHT - 1)
        ttl = self.params["ttl_start"] - self.params["ramp"] * self.score
        self.mole_ttl = max(self.params["ttl_min"], ttl)
        self.mole_age = 0.0

    def update(self, dt):
        if self.over:
            self.over_timer += dt
            if self.over_timer > 1.2:
                self.finish(score=self.score)
            return

        self.flash = max(0.0, self.flash - dt)
        self.bad_flash = max(0.0, self.bad_flash - dt)
        self.mole_age += dt

        hit = False
        miss_click = False
        for (x, y) in self.hal.press_events():
            if x == self.mole_x and y == self.mole_y:
                hit = True
            else:
                miss_click = True

        if hit:
            self.score += 1
            self.flash = 0.16
            self.hal.play("good")
            self._spawn()
            return
        if miss_click:
            self.bad_flash = 0.16
            self.hal.play("bad")
        if self.mole_age >= self.mole_ttl:
            self.lives -= 1
            self.bad_flash = 0.30
            self.hal.play("miss")
            if self.lives <= 0:
                self.over = True
            else:
                self._spawn()

    def render(self):
        if self.bad_flash > 0:
            v = int(min(255, self.bad_flash * 600))
            self.hal.fill((v, 0, 0))
            return
        if self.flash > 0:
            v = int(min(255, self.flash * 700))
            self.hal.fill((0, v, 0))
            return
        if self.over:
            return

        # Maulwurf: rot->weiss je naeher an Ablaufzeit.
        age_ratio = min(1.0, self.mole_age / self.mole_ttl)
        r = 255
        g = int(255 * (1.0 - age_ratio))
        b = int(120 * (1.0 - age_ratio))
        self.hal.set(self.mole_x, self.mole_y, (r, g, b))
