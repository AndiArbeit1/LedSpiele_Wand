"""Headless-Smoke-Test fuer das 8x8-Setup (ohne pygame/Hardware).

Prueft: Imports, Bildschirmgroesse, Menue-/Level-Routing, alle acht Spiele
laufen ein paar Frames ohne Out-of-Bounds, Scoreboard schreibt/liest,
Admin-Stats-JSON ist gueltig.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["LEDMATRIX_HAL"] = "stub"  # nur als Marker, HAL wird nicht genutzt

import config, menu, games
from select_screens import level_loop
from menu import menu_loop

assert (config.WIDTH, config.HEIGHT) == (8, 8), "Matrix muss 8x8 sein"
assert config.NUM_LEVELS == 4
assert len(games.ALL) == 8, "Es muessen genau 8 Spiele sein"

oob = []

class FakeHAL:
    def __init__(self, presses=None):
        self.q = list(presses or [])
        self.fired = False
    def poll(self): pass
    def menu_requested(self): return False
    def press_events(self):
        if self.fired: return []
        self.fired = True
        return list(self.q)
    def play(self, n): pass
    def play_freq(self, f, dur=0.0, vol=0.0): pass
    def play_music(self, path, loops=-1, vol=0.6): pass
    def stop_music(self): pass
    def clear(self): pass
    def fill(self, c): pass
    def show(self): pass
    def set(self, x, y, c):
        if not (0 <= x < config.WIDTH and 0 <= y < config.HEIGHT):
            oob.append((x, y))

print("GAMES:", [g.name for g in games.ALL])

# --- Menue-Routing: 2x4-Kacheln (4 breit x 2 hoch) ---
cases = [((0, 0), 0), ((4, 0), 1), ((0, 2), 2), ((4, 2), 3),
         ((0, 4), 4), ((4, 4), 5), ((0, 6), 6), ((4, 6), 7),
         ((7, 7), 7), ((3, 1), 0)]
for (px, py), idx in cases:
    got = menu_loop(FakeHAL([(px, py)]), games.ALL)
    assert got is games.ALL[idx], ((px, py), idx, got.name)
print("MENU ROUTING OK (8 Kacheln)")

# --- Level-Routing: 2x2-Quadranten ---
assert level_loop(FakeHAL([(0, 0)])) == 1  # TL
assert level_loop(FakeHAL([(7, 0)])) == 2  # TR
assert level_loop(FakeHAL([(0, 7)])) == 3  # BL
assert level_loop(FakeHAL([(7, 7)])) == 4  # BR
print("LEVEL ROUTING OK")

# --- Menue-Render ohne Out-of-Bounds ---
render_hal = FakeHAL([])
for i in range(len(games.ALL)):
    for cx, cy in menu._tile_cells(i):
        render_hal.set(cx, cy, (1, 1, 1))

# --- Jedes Spiel ein paar Frames laufen lassen ---
for cls in games.ALL:
    h = FakeHAL([(0, 0), (1, 1), (2, 2), (3, 3)])
    g = cls(h)
    g.configure(2, 1)
    g.reset()
    for _ in range(160):
        h.fired = False  # bei jedem Frame neue (gleiche) Presses zulassen
        g.update(0.05)
        g.render()
        if g.done:
            break
    print("  {:10s} ok (score={})".format(cls.name, g.final_score))

assert not oob, "Out-of-Bounds Pixel: {}".format(oob[:10])
print("NO OUT-OF-BOUNDS")

# --- Scoreboard ---
import scoreboard
scoreboard._PATH = scoreboard._PATH + ".smoketest"
scoreboard._data = None
r1, b1 = scoreboard.record("Whack", 1, 5, higher_is_better=True)
r2, b2 = scoreboard.record("Whack", 1, 9, higher_is_better=True)
r3, b3 = scoreboard.record("Whack", 1, 7, higher_is_better=True)
assert r1 and r2 and not r3, (r1, r2, r3)
assert b3 == 9, b3
rl, bl = scoreboard.record("Lights", 1, 20, higher_is_better=False)
rl2, bl2 = scoreboard.record("Lights", 1, 12, higher_is_better=False)
assert rl and rl2 and bl2 == 12
print("SCOREBOARD OK (best whack=9, best lights=12)")

# --- Admin Stats JSON ---
import webcommon
payload = json.loads(webcommon.stats_json())
assert "games" in payload and "Whack" in payload["games"]
print("STATS JSON OK (total_plays={})".format(payload["total_plays"]))

os.remove(scoreboard._PATH)
print("ALL OK")
