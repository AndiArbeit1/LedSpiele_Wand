"""Game-Framework: Basisklasse, Hilfsfunktionen, Mini- und Big-Font.

Spiele melden am Ende einen Score und ggf. Spielerzahl, damit run_game
einen passenden End-Screen rendern kann.
"""

import time
import config


class Game:
    name = "Game"
    color = (255, 255, 255)
    supports_multiplayer = False
    has_score_screen = True
    # True: Spiel hat 4 Level -> Level-Auswahl vor dem Start. False (z.B.
    # Heatmap): direkt starten, keine Level-Auswahl.
    has_levels = True
    # True: hoeherer Score ist besser. False (z.B. Lights Out): weniger ist
    # besser. Steuert, was der Scoreboard als Bestwert zaehlt.
    higher_is_better = True

    def __init__(self, hal):
        self.hal = hal
        self.done = False
        self.level = 3
        self.players = 1
        self.final_score = None
        self.final_score2 = None

    def configure(self, level, players):
        self.level = level
        self.players = players

    def reset(self):
        pass

    def update(self, dt):
        pass

    def render(self):
        pass

    def finish(self, score=None, score2=None):
        self.done = True
        self.final_score = score
        self.final_score2 = score2


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


def lerp_color(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def scale_color(c, s):
    return (int(c[0] * s), int(c[1] * s), int(c[2] * s))


def heat_color(h):
    h = clamp(h, 0.0, 1.0)
    if h < 0.25:   return lerp_color((0, 0, 0),     (0, 0, 80),    h / 0.25)
    if h < 0.5:    return lerp_color((0, 0, 80),    (180, 0, 120), (h - 0.25) / 0.25)
    if h < 0.75:   return lerp_color((180, 0, 120), (255, 120, 0), (h - 0.5) / 0.25)
    return lerp_color((255, 120, 0), (255, 255, 200), (h - 0.75) / 0.25)


def heat_color_rgb(h):
    """Erweiterte Heatmap-Palette: dunkel -> blau -> gruen -> gelb -> rot -> weiss."""
    h = clamp(h, 0.0, 1.0)
    if h < 0.20:  return lerp_color((0, 0, 0),     (0,   0, 120),  h / 0.20)
    if h < 0.40:  return lerp_color((0, 0, 120),   (0, 200, 200),  (h - 0.20) / 0.20)
    if h < 0.60:  return lerp_color((0, 200, 200), (60, 255,  40), (h - 0.40) / 0.20)
    if h < 0.80:  return lerp_color((60, 255, 40), (255, 200,  0), (h - 0.60) / 0.20)
    return         lerp_color((255, 200, 0),  (255, 255, 255), (h - 0.80) / 0.20)


# 3x5 Mini-Font (Spaltenmuster, LSB = oberste Reihe)
FONT_3x5 = {
    "0": [0b11111, 0b10001, 0b11111],
    "1": [0b00000, 0b11111, 0b00000],
    "2": [0b11101, 0b10101, 0b10111],
    "3": [0b10101, 0b10101, 0b11111],
    "4": [0b00111, 0b00100, 0b11111],
    "5": [0b10111, 0b10101, 0b11101],
    "6": [0b11111, 0b10101, 0b11101],
    "7": [0b00001, 0b00001, 0b11111],
    "8": [0b11111, 0b10101, 0b11111],
    "9": [0b10111, 0b10101, 0b11111],
    " ": [0b00000, 0b00000, 0b00000],
    ":": [0b00000, 0b01010, 0b00000],
    "-": [0b00100, 0b00100, 0b00100],
    "G": [0b11111, 0b10001, 0b10111],
    "O": [0b11111, 0b10001, 0b11111],
    "!": [0b00000, 0b10111, 0b00000],
    "L": [0b11111, 0b10000, 0b10000],
    "V": [0b00111, 0b11000, 0b00111],
    "P": [0b11111, 0b00101, 0b00111],
    "R": [0b11111, 0b00101, 0b11010],
    "1V": [0b11111, 0b00111, 0b11100, 0b00111, 0b11111],
}


def draw_text(hal, text, x0, y0, color):
    x = x0
    for ch in text.upper():
        glyph = FONT_3x5.get(ch, FONT_3x5[" "])
        for cx, col_bits in enumerate(glyph):
            for cy in range(5):
                if col_bits & (1 << cy):
                    hal.set(x + cx, y0 + cy, color)
        x += 4
    return x


# 5x7 Big-Font fuer Score-Screen. Spaltenmuster: LSB = oberste Reihe.
FONT_5x7 = {
    "0": [0b0111110, 0b1000001, 0b1000001, 0b1000001, 0b0111110],
    "1": [0b0000000, 0b1000010, 0b1111111, 0b1000000, 0b0000000],
    "2": [0b1100010, 0b1010001, 0b1001001, 0b1000101, 0b1000010],
    "3": [0b0100010, 0b1000001, 0b1001001, 0b1001001, 0b0110110],
    "4": [0b0011000, 0b0010100, 0b0010010, 0b1111111, 0b0010000],
    "5": [0b0100111, 0b1000101, 0b1000101, 0b1000101, 0b0111001],
    "6": [0b0111110, 0b1001001, 0b1001001, 0b1001001, 0b0110010],
    "7": [0b0000001, 0b1110001, 0b0001001, 0b0000101, 0b0000011],
    "8": [0b0110110, 0b1001001, 0b1001001, 0b1001001, 0b0110110],
    "9": [0b0100110, 0b1001001, 0b1001001, 0b1001001, 0b0111110],
    " ": [0b0000000, 0b0000000, 0b0000000, 0b0000000, 0b0000000],
    "-": [0b0001000, 0b0001000, 0b0001000, 0b0001000, 0b0001000],
    ":": [0b0000000, 0b0110110, 0b0110110, 0b0000000, 0b0000000],
    "G": [0b0111110, 0b1000001, 0b1001001, 0b1001001, 0b0111010],
    "O": [0b0111110, 0b1000001, 0b1000001, 0b1000001, 0b0111110],
    "L": [0b1111111, 0b1000000, 0b1000000, 0b1000000, 0b1000000],
    "V": [0b0011111, 0b0100000, 0b1000000, 0b0100000, 0b0011111],
    "S": [0b0100110, 0b1001001, 0b1001001, 0b1001001, 0b0110010],
    "C": [0b0111110, 0b1000001, 0b1000001, 0b1000001, 0b0100010],
    "R": [0b1111111, 0b0001001, 0b0011001, 0b0101001, 0b1000110],
    "E": [0b1111111, 0b1001001, 0b1001001, 0b1001001, 0b1000001],
    "P": [0b1111111, 0b0001001, 0b0001001, 0b0001001, 0b0000110],
    "1V": [0b1111111, 0b0011110, 0b0111000, 0b1110000, 0b0011110, 0b0111000, 0b1111111],
    "!": [0b0000000, 0b0000000, 0b1011111, 0b0000000, 0b0000000],
}


def text_width_5x7(text):
    return 6 * len(text) - 1 if text else 0


def draw_text_5x7(hal, text, x0, y0, color, gap=1):
    """Zeichnet text in 5x7-Font. y0 = oberste Reihe (7 hoch)."""
    x = x0
    for ch in text.upper():
        glyph = FONT_5x7.get(ch, FONT_5x7[" "])
        for cx, col_bits in enumerate(glyph):
            for cy in range(7):
                if col_bits & (1 << cy):
                    hal.set(x + cx, y0 + cy, color)
        x += len(glyph) + gap
    return x


def text_width_5x7_gap(text, gap=1):
    if not text:
        return 0
    return sum(len(FONT_5x7.get(ch, FONT_5x7[" "])) for ch in text.upper()) \
        + gap * (len(text) - 1)


def draw_rect(hal, x0, y0, w, h, color):
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            hal.set(x, y, color)


def draw_rect_outline(hal, x0, y0, w, h, color):
    for x in range(x0, x0 + w):
        hal.set(x, y0, color)
        hal.set(x, y0 + h - 1, color)
    for y in range(y0, y0 + h):
        hal.set(x0, y, color)
        hal.set(x0 + w - 1, y, color)


def run_game(hal, game, fps=config.TARGET_FPS):
    game.reset()
    target_dt = 1.0 / fps
    last = time.monotonic()
    while not game.done:
        now = time.monotonic()
        dt = now - last
        last = now

        hal.poll()
        if hal.menu_requested():
            return None

        game.update(dt)
        hal.clear()
        game.render()
        hal.show()

        sleep_for = target_dt - (time.monotonic() - now)
        if sleep_for > 0:
            time.sleep(sleep_for)
    return (game.final_score, game.final_score2)
