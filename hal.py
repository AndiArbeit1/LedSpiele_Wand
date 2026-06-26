"""Hardware Abstraction Layer v2 (8x8).

Plattform: Raspberry Pi 3 (v3.3 -- WLAN onboard, 32-/64-Bit OS).
LEDs:      WS2812 (NeoPixel) ueber GPIO21 (PCM statt PWM, damit es nicht
           mit dem analogen Audio-Ausgang/Klinke kollidiert, der intern
           ebenfalls die PWM-Peripherie nutzt). VIER LEDs pro Zelle/Taster
           (config.LEDS_PER_CELL), direkt hintereinander in der Kette; sie
           leuchten immer gemeinsam, also bleibt es logisch ein 8x8-Raster.
Switches:  64 Cherry MX Switches an MCP23017 IO-Expandern. Jeder Switch
           ist direkt an einem Pin angeschlossen (kein Matrix-Scan).
           Anzahl Chips + I2C-Topologie wird in config.MCP_CHIPS
           beschrieben.
Audio:     Klinkenausgang via pygame.mixer.

HAL-Auswahl ueber Env-Var LEDMATRIX_HAL:
    real     echte Hardware (Default wenn neopixel+smbus2 verfuegbar)
    web      Web-Bridge fuer Handy-Browser (siehe web_hal.py).
             Nimm das auf dem Pi 3 solange die LED-Matrix und das
             MCP23017-Board noch nicht angeschlossen sind.
    sim      Pygame-Fenster (Dev auf Windows / Linux-Desktop).
    auto     (Default) real -> sim, je nach verfuegbaren Modulen.
"""

import os
import time
import math
import config

try:
    import board
    import neopixel
    _HAVE_LEDS = True
except Exception:
    _HAVE_LEDS = False

try:
    from smbus2 import SMBus
    _HAVE_I2C = True
except Exception:
    _HAVE_I2C = False

try:
    import pygame
    pygame.mixer.init(frequency=config.AUDIO_RATE, channels=2, size=-16,
                      buffer=512)
    pygame.mixer.set_num_channels(config.AUDIO_CHANNELS)
    _HAVE_AUDIO = True
except Exception:
    _HAVE_AUDIO = False


def _xy_to_cell(x, y):
    """Logische Zelle (x, y) -> fortlaufende Zell-Nummer 0..NUM_CELLS-1.

    Erst Orientierung (FLIP_X/FLIP_Y) auf die physische Kachel drehen, dann
    wie die ESP32-Vorlage (tileboard.tile_to_led_indices): Kette beginnt bei
    Reihe 0, ungerade Reihen laufen rueckwaerts (Serpentine).
    """
    if config.FLIP_X:
        x = config.WIDTH - 1 - x
    if config.FLIP_Y:
        y = config.HEIGHT - 1 - y
    if config.LED_SERPENTINE and (y % 2 == 1):
        x = config.WIDTH - 1 - x
    return y * config.WIDTH + x


def _cell_led_indices(x, y):
    """Die LEDS_PER_CELL aufeinanderfolgenden LED-Indizes einer Zelle.

    Zelle n belegt LEDs n*LEDS_PER_CELL .. n*LEDS_PER_CELL+LEDS_PER_CELL-1
    ("1,2,3,4 gehoeren zu Taster 1" usw.).
    """
    base = _xy_to_cell(x, y) * config.LEDS_PER_CELL
    return range(base, base + config.LEDS_PER_CELL)


class _RealMatrix:
    def __init__(self):
        pin = getattr(board, "D{}".format(config.LED_PIN))
        self._strip = neopixel.NeoPixel(
            pin, config.NUM_PIXELS,
            brightness=config.LED_BRIGHTNESS,
            auto_write=False, pixel_order=neopixel.GRB,
        )

    def set(self, x, y, color):
        if 0 <= x < config.WIDTH and 0 <= y < config.HEIGHT:
            # Alle vier LEDs der Zelle gemeinsam setzen.
            for i in _cell_led_indices(x, y):
                self._strip[i] = color

    def fill(self, color):
        self._strip.fill(color)

    def clear(self):
        self._strip.fill((0, 0, 0))

    def show(self):
        self._strip.show()


# ---- MCP23017 + optionaler TCA9548A Multiplexer ----

# MCP23017-Register (IOCON.BANK=0, Werkszustand nach Power-on/Reset).
_MCP_IODIRA = 0x00   # Richtung Port A (1 = Input)
_MCP_GPIO_A = 0x12   # GPIO-Zustand Port A/B (0x12/0x13, zusammenhaengend)


class _Tca9548a:
    """I2C-Multiplexer. Eine Instanz pro Bus."""

    def __init__(self, bus, address):
        self._bus_obj = SMBus(bus)
        self._address = address
        self._current_channel = None

    def select(self, channel):
        if channel == self._current_channel:
            return
        self._bus_obj.write_byte(self._address, 1 << channel)
        self._current_channel = channel


class _Mcp23017Reader:
    """Liest 64 Switches verteilt auf mehrere MCP23017.

    Jeder MCP23017 wird ueber die GPIOA/GPIOB-Register als 2-Byte-Read
    ausgelesen (Port A = Bit 0..7, Port B = Bit 8..15). Die Taster-Platinen
    haben eigene Pull-Down-Widerstaende nach GND: ein Bit ist 0, wenn der
    Switch offen ist (vom Pull-Down nach Masse gezogen), 1 wenn gedrueckt
    (Switch verbindet den Pin mit VCC). Interne Pull-Ups bleiben deshalb
    aus -- die wuerden gegen die externen Pull-Downs arbeiten.

    Boards muessen nicht alle gleichzeitig angeschlossen sein: ein Chip,
    der beim Start nicht antwortet, wird einfach uebersprungen (dessen
    Taster bleiben "nicht gedrueckt", der Rest -- LEDs, Sound, andere
    Chips -- laeuft normal weiter).
    """

    def __init__(self):
        # Bus-Cache: pro Bus-Nummer eine SMBus-Instanz.
        self._buses = {}
        for chip in config.MCP_CHIPS:
            b = chip["bus"]
            if b not in self._buses:
                self._buses[b] = SMBus(b)

        self._mux = None
        if config.MUX_ADDRESS is not None:
            self._mux = _Tca9548a(config.MUX_BUS, config.MUX_ADDRESS)

        self._chip_present = []
        for i, chip in enumerate(config.MCP_CHIPS):
            try:
                self._init_chip(i, chip)
                self._chip_present.append(True)
            except Exception as e:
                self._chip_present.append(False)
                print("[hal] MCP23017 @0x{:02x} nicht erreichbar ({}) -- "
                      "Taster auf diesem Chip vorerst deaktiviert.".format(
                          chip["address"], e))

        # State + Debounce-Timer pro logischem (x,y)-Switch.
        self._state = [[False] * config.WIDTH for _ in range(config.HEIGHT)]
        self._last_change = [[0.0] * config.WIDTH for _ in range(config.HEIGHT)]

        # Reverse-Mapping: chip_idx -> Liste von (bit_idx, x, y)
        # Damit wir nach dem Read schnell alle Switches eines Chips
        # aktualisieren koennen.
        self._chip_to_switches = [[] for _ in range(len(config.MCP_CHIPS))]
        for (x, y), (chip_idx, bit_idx) in config.SWITCH_MAP.items():
            self._chip_to_switches[chip_idx].append((bit_idx, x, y))

    def _init_chip(self, idx, chip):
        if chip.get("mux_channel") is not None and self._mux is not None:
            self._mux.select(chip["mux_channel"])
        bus = self._buses[chip["bus"]]
        # Beide Ports als Input (Werkszustand, hier explizit gesetzt).
        # Keine internen Pull-Ups aktivieren: die Taster-Platinen haben
        # bereits eigene Pull-Down-Widerstaende, beides zusammen wuerde
        # einen Spannungsteiler ergeben statt klarer High/Low-Pegel.
        bus.write_i2c_block_data(chip["address"], _MCP_IODIRA, [0xFF, 0xFF])

    def _read_chip(self, idx, chip):
        if chip.get("mux_channel") is not None and self._mux is not None:
            self._mux.select(chip["mux_channel"])
        bus = self._buses[chip["bus"]]
        # GPIOA/GPIOB in einem Block lesen (Port A = Bit 0..7, B = 8..15).
        data = bus.read_i2c_block_data(chip["address"], _MCP_GPIO_A, 2)
        return (data[1] << 8) | data[0]

    def scan(self, now):
        events = []
        debounce_s = config.DEBOUNCE_MS / 1000.0
        for idx, chip in enumerate(config.MCP_CHIPS):
            if not self._chip_present[idx]:
                continue
            try:
                port_val = self._read_chip(idx, chip)
            except Exception:
                continue
            # Bit = 1 -> Switch gedrueckt (Pull-Down-Platine: offen = 0).
            for (bit_idx, x, y) in self._chip_to_switches[idx]:
                pressed = ((port_val >> bit_idx) & 1) == 1
                if pressed != self._state[y][x]:
                    if now - self._last_change[y][x] >= debounce_s:
                        self._state[y][x] = pressed
                        self._last_change[y][x] = now
                        events.append((x, y, pressed))
        return events

    def pressed(self):
        return [(x, y) for y in range(config.HEIGHT)
                for x in range(config.WIDTH) if self._state[y][x]]


class _StubMatrix:
    def __init__(self):
        self._buf = [(0, 0, 0)] * config.NUM_PIXELS

    def set(self, x, y, color):
        if 0 <= x < config.WIDTH and 0 <= y < config.HEIGHT:
            c = tuple(int(v) for v in color)
            for i in _cell_led_indices(x, y):
                self._buf[i] = c

    def fill(self, color):
        c = tuple(int(v) for v in color)
        self._buf = [c] * config.NUM_PIXELS

    def clear(self):
        self.fill((0, 0, 0))

    def show(self):
        pass


class _StubButtons:
    def scan(self, now):
        return []

    def pressed(self):
        return []


def _have_real_hw():
    return _HAVE_LEDS and _HAVE_I2C


class HAL:
    def __new__(cls):
        choice = os.environ.get("LEDMATRIX_HAL", "auto").strip().lower()

        if choice == "web":
            from web_hal import WebHAL
            return WebHAL()
        if choice == "sim":
            from sim_hal import SimHAL
            return SimHAL()
        if choice == "real":
            # User-Vorgabe: echte Hardware, kein Fallback.
            return super().__new__(cls)

        # auto
        if _have_real_hw():
            return super().__new__(cls)
        try:
            from sim_hal import SimHAL
            return SimHAL()
        except Exception as e:
            print("[hal] Pygame-Sim nicht verfuegbar ({}), nutze Stub.".format(e))
            return super().__new__(cls)

    def __init__(self):
        self._admin = None
        if _have_real_hw():
            self.matrix = _RealMatrix()
            try:
                self.buttons = _Mcp23017Reader()
            except Exception as e:
                # Z.B. I2C-Bus noch nicht aktiviert oder noch gar kein
                # MCP23017 angeschlossen -- LEDs/Sound sollen trotzdem
                # laufen, nur die Taster bleiben dann erstmal tot.
                print("[hal] Taster-I2C nicht verfuegbar ({}), "
                      "Taster vorerst deaktiviert.".format(e))
                self.buttons = _StubButtons()
            # Echte Hardware ist dran -> Admin-/Statistik-Webserver starten,
            # damit man Highscores im Browser sehen kann.
            try:
                import admin_server
                self._admin = admin_server.start(on_menu=self._request_menu)
            except Exception as e:
                print("[hal] Admin-Server nicht gestartet: {}".format(e))
        else:
            self.matrix = _StubMatrix()
            self.buttons = _StubButtons()
        self._event_queue = []
        self._sounds = {}
        self._tone_cache = {}
        self._build_default_sounds()
        self._menu_hold_start = None
        self._menu_requested = False
        # Geheim-Kombi (zwei untere Ecken, mehrmals): Zustand.
        self._combo_both_prev = False
        self._combo_count = 0
        self._combo_last = 0.0

    def set(self, x, y, color):
        self.matrix.set(x, y, color)

    def fill(self, color):
        self.matrix.fill(color)

    def clear(self):
        self.matrix.clear()

    def show(self):
        self.matrix.show()

    def poll(self):
        now = time.monotonic()
        new_events = self.buttons.scan(now)
        self._event_queue.extend(new_events)
        self._check_menu_hold(now)
        self._check_menu_combo(now)

    def events(self):
        out, self._event_queue = self._event_queue, []
        return out

    def press_events(self):
        return [(x, y) for (x, y, pressed) in self.events() if pressed]

    def pressed(self):
        return self.buttons.pressed()

    def is_pressed(self, x, y):
        return (x, y) in self.buttons.pressed()

    def _check_menu_hold(self, now):
        mx, my = config.MENU_BUTTON
        held = (mx, my) in self.buttons.pressed()
        if held:
            if self._menu_hold_start is None:
                self._menu_hold_start = now
            elif (now - self._menu_hold_start) * 1000 >= config.MENU_HOLD_MS:
                self._menu_requested = True
        else:
            self._menu_hold_start = None

    def _check_menu_combo(self, now):
        """Beide unteren Ecken gleichzeitig, COUNT mal hintereinander -> Menue.

        Gezaehlt wird die steigende Flanke von "beide gedrueckt" (man muss
        also zwischendurch loslassen). Zu lange Pause -> Zaehlung beginnt neu.
        """
        cells = config.MENU_COMBO_CELLS
        pressed = self.buttons.pressed()
        both = all(c in pressed for c in cells)
        if both and not self._combo_both_prev:
            if (now - self._combo_last) * 1000 > config.MENU_COMBO_RESET_MS:
                self._combo_count = 0
            self._combo_count += 1
            self._combo_last = now
            if self._combo_count >= config.MENU_COMBO_COUNT:
                self._menu_requested = True
                self._combo_count = 0
        self._combo_both_prev = both

    def menu_requested(self):
        if self._menu_requested:
            self._menu_requested = False
            return True
        return False

    def _request_menu(self):
        """Von aussen (Admin-Seite, POST /menu) -> zurueck ins Menue."""
        self._menu_requested = True

    def _build_default_sounds(self):
        if not _HAVE_AUDIO:
            return
        import array
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
                buf.append(v)
                buf.append(v)
            return pygame.mixer.Sound(buffer=buf.tobytes())

        def noise(dur=0.1, vol=0.5):
            import random
            n = int(rate * dur)
            buf = array.array("h")
            for i in range(n):
                t = i / rate
                env = min(1.0, 30 * t, 5 * (dur - t))
                v = int(max(-1.0, min(1.0, (random.random() * 2 - 1) * env * vol)) * 30000)
                buf.append(v)
                buf.append(v)
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
        for i, midi in enumerate([60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84]):
            f = 440.0 * (2 ** ((midi - 69) / 12.0))
            self._sounds["note{}".format(i)] = tone(f, 0.18, 0.4, "sine")

    def play(self, name):
        if not _HAVE_AUDIO:
            return
        s = self._sounds.get(name)
        if s is not None:
            s.play()

    def play_freq(self, freq, dur=0.18, vol=0.4):
        if not _HAVE_AUDIO:
            return
        key = (int(freq), int(dur * 1000))
        s = self._tone_cache.get(key)
        if s is None:
            s = self._tone_builder(freq, dur, vol, "sine")
            self._tone_cache[key] = s
        s.play()

    def play_music(self, path, loops=-1, vol=0.6):
        """Hintergrund-Musik (z.B. Lobby) abspielen, loops=-1 = endlos."""
        if not _HAVE_AUDIO:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(vol)
            pygame.mixer.music.play(loops=loops)
        except Exception as e:
            print("[hal] Musik nicht abspielbar ({}): {}".format(path, e))

    def stop_music(self):
        if not _HAVE_AUDIO:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def shutdown(self):
        try:
            self.clear()
            self.show()
        except Exception:
            pass
        if self._admin is not None:
            try:
                self._admin.shutdown()
                self._admin.server_close()
            except Exception:
                pass
