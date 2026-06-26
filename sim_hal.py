"""Pygame-Simulator fuer die LED-Matrix + 8x8 Switch-Grid.

Bedienung:
    Linksklick auf Zelle  = Switch druecken
    Linke Maustaste halten + ziehen = mehrere Zellen "halten"
    Rechtsklick = Zelle "sticky"
    Taste  M    = Zurueck zum Menue (entspricht dem Halten von (7,0))
    Taste  Esc  = Beenden
"""

import math
import time
import array
import random

import pygame
import config


CELL_PX = 38
GAP_PX = 3
PAD_PX = 12
STATUS_PX = 28


class SimHAL:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init(frequency=config.AUDIO_RATE, channels=2,
                              size=-16, buffer=512)
            pygame.mixer.set_num_channels(config.AUDIO_CHANNELS)
            self._have_audio = True
        except Exception:
            self._have_audio = False

        w = config.WIDTH * CELL_PX + PAD_PX * 2
        h = config.HEIGHT * CELL_PX + PAD_PX * 2 + STATUS_PX
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption(
            "LED Matrix ({0}x{1})  -  M=menu  Esc=quit".format(
                config.WIDTH, config.HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 18)

        self._buf = [[(0, 0, 0)] * config.WIDTH for _ in range(config.HEIGHT)]
        self._state = [[False] * config.WIDTH for _ in range(config.HEIGHT)]
        self._sticky = [[False] * config.WIDTH for _ in range(config.HEIGHT)]
        self._event_queue = []
        self._mouse_down = False
        self._last_drag_cell = None
        self._menu_requested = False
        self._quit_requested = False
        # Geheim-Kombi (zwei untere Ecken, mehrmals) -> Menue.
        self._combo_both_prev = False
        self._combo_count = 0
        self._combo_last = 0.0

        self._sounds = {}
        self._tone_cache = {}
        self._build_default_sounds()

    def _xy_from_mouse(self, mx, my):
        mx -= PAD_PX
        my -= PAD_PX
        if mx < 0 or my < 0:
            return None
        x = mx // CELL_PX
        y = my // CELL_PX
        if 0 <= x < config.WIDTH and 0 <= y < config.HEIGHT:
            return int(x), int(y)
        return None

    def _press_cell(self, x, y):
        if not self._state[y][x]:
            self._state[y][x] = True
            self._event_queue.append((x, y, True))

    def poll(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._quit_requested = True
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self._quit_requested = True
                elif ev.key == pygame.K_m:
                    self._menu_requested = True
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                cell = self._xy_from_mouse(*ev.pos)
                if cell is None:
                    continue
                cx, cy = cell
                if ev.button == 1:
                    self._mouse_down = True
                    self._last_drag_cell = cell
                    self._press_cell(cx, cy)
                elif ev.button == 3:
                    self._sticky[cy][cx] = not self._sticky[cy][cx]
                    if self._sticky[cy][cx]:
                        self._press_cell(cx, cy)
                    else:
                        self._state[cy][cx] = False
                        self._event_queue.append((cx, cy, False))
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    self._mouse_down = False
                    self._last_drag_cell = None
                    for y in range(config.HEIGHT):
                        for x in range(config.WIDTH):
                            if self._state[y][x] and not self._sticky[y][x]:
                                self._state[y][x] = False
                                self._event_queue.append((x, y, False))
            elif ev.type == pygame.MOUSEMOTION:
                if self._mouse_down:
                    cell = self._xy_from_mouse(*ev.pos)
                    if cell is not None and cell != self._last_drag_cell:
                        self._last_drag_cell = cell
                        self._press_cell(*cell)

        self._check_menu_combo()

        if self._quit_requested:
            self.shutdown()
            raise SystemExit

    def _check_menu_combo(self):
        cells = config.MENU_COMBO_CELLS
        pressed = self.pressed()
        both = all(c in pressed for c in cells)
        if both and not self._combo_both_prev:
            now = time.monotonic()
            if (now - self._combo_last) * 1000 > config.MENU_COMBO_RESET_MS:
                self._combo_count = 0
            self._combo_count += 1
            self._combo_last = now
            if self._combo_count >= config.MENU_COMBO_COUNT:
                self._menu_requested = True
                self._combo_count = 0
        self._combo_both_prev = both

    def events(self):
        out, self._event_queue = self._event_queue, []
        return out

    def press_events(self):
        return [(x, y) for (x, y, p) in self.events() if p]

    def pressed(self):
        return [(x, y) for y in range(config.HEIGHT)
                for x in range(config.WIDTH) if self._state[y][x]]

    def is_pressed(self, x, y):
        return self._state[y][x]

    def menu_requested(self):
        if self._menu_requested:
            self._menu_requested = False
            return True
        return False

    def set(self, x, y, color):
        if 0 <= x < config.WIDTH and 0 <= y < config.HEIGHT:
            self._buf[y][x] = (int(color[0]) & 0xff,
                               int(color[1]) & 0xff,
                               int(color[2]) & 0xff)

    def fill(self, color):
        c = (int(color[0]) & 0xff, int(color[1]) & 0xff, int(color[2]) & 0xff)
        for y in range(config.HEIGHT):
            for x in range(config.WIDTH):
                self._buf[y][x] = c

    def clear(self):
        self.fill((0, 0, 0))

    def show(self):
        self.screen.fill((18, 18, 22))
        for y in range(config.HEIGHT):
            for x in range(config.WIDTH):
                col = self._buf[y][x]
                rx = PAD_PX + x * CELL_PX + GAP_PX
                ry = PAD_PX + y * CELL_PX + GAP_PX
                size = CELL_PX - GAP_PX * 2
                pygame.draw.rect(self.screen, (40, 40, 48),
                                 (rx - 1, ry - 1, size + 2, size + 2),
                                 border_radius=6)
                pygame.draw.rect(self.screen, col, (rx, ry, size, size),
                                 border_radius=6)
                if self._state[y][x]:
                    ring = (255, 255, 255) if not self._sticky[y][x] else (255, 200, 0)
                    pygame.draw.rect(self.screen, ring,
                                     (rx, ry, size, size), 2, border_radius=6)

        hint = self.font.render(
            "Linksklick=press, Drag=multi, Rechtsklick=sticky, M=menu, Esc=quit",
            True, (180, 180, 190))
        self.screen.blit(hint, (PAD_PX,
                                PAD_PX + config.HEIGHT * CELL_PX + 6))
        pygame.display.flip()

    def _build_default_sounds(self):
        if not self._have_audio:
            return
        rate = config.AUDIO_RATE

        def tone(freq, dur=0.15, vol=0.5, shape="sine"):
            n = int(rate * dur)
            buf = array.array("h")
            for i in range(n):
                t = i / rate
                if shape == "square":
                    s = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
                elif shape == "saw":
                    s = 2.0 * ((t * freq) % 1.0) - 1.0
                else:
                    s = math.sin(2 * math.pi * freq * t)
                env = min(1.0, 8 * t, 8 * (dur - t))
                v = int(max(-1.0, min(1.0, s * env * vol)) * 30000)
                buf.append(v); buf.append(v)
            return pygame.mixer.Sound(buffer=buf.tobytes())

        def noise(dur=0.1, vol=0.5):
            n = int(rate * dur)
            buf = array.array("h")
            for i in range(n):
                t = i / rate
                env = min(1.0, 30 * t, 5 * (dur - t))
                v = int(max(-1.0, min(1.0, (random.random() * 2 - 1) * env * vol)) * 30000)
                buf.append(v); buf.append(v)
            return pygame.mixer.Sound(buffer=buf.tobytes())

        self._tone_builder = tone

        self._sounds = {
            "kick":  tone(60, 0.18, 0.8, "sine"),
            "snare": noise(0.12, 0.6),
            "hat":   noise(0.05, 0.3),
            "tom":   tone(120, 0.15, 0.7, "sine"),
            "clap":  noise(0.08, 0.5),
            "click": tone(1500, 0.03, 0.4, "square"),
            "good":  tone(880, 0.12, 0.5, "sine"),
            "bad":   tone(180, 0.18, 0.6, "saw"),
            "miss":  tone(140, 0.30, 0.6, "saw"),
            "win":   tone(660, 0.40, 0.6, "sine"),
        }
        for i, midi in enumerate([60, 62, 64, 65, 67, 69, 71, 72,
                                  74, 76, 77, 79, 81, 83, 84]):
            f = 440.0 * (2 ** ((midi - 69) / 12.0))
            self._sounds["note{}".format(i)] = tone(f, 0.18, 0.4, "sine")

    def play(self, name):
        if not self._have_audio:
            return
        s = self._sounds.get(name)
        if s is not None:
            s.play()

    def play_freq(self, freq, dur=0.18, vol=0.4):
        if not self._have_audio:
            return
        key = (int(freq), int(dur * 1000))
        s = self._tone_cache.get(key)
        if s is None:
            s = self._tone_builder(freq, dur, vol, "sine")
            self._tone_cache[key] = s
        s.play()

    def play_music(self, path, loops=-1, vol=0.6):
        """Hintergrund-Musik (z.B. Lobby) abspielen, loops=-1 = endlos."""
        if not self._have_audio:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(vol)
            pygame.mixer.music.play(loops=loops)
        except Exception as e:
            print("[sim_hal] Musik nicht abspielbar ({}): {}".format(path, e))

    def stop_music(self):
        if not self._have_audio:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def shutdown(self):
        try:
            pygame.quit()
        except Exception:
            pass
