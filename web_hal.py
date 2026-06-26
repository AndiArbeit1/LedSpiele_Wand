"""WebHAL: serviert die Matrix an einen Handy-Browser ueber HTTP+SSE.

Dieser HAL ersetzt den echten LED+MCP23017-HAL solange die endgueltige
Hardware noch nicht da ist. Auf dem Pi 3 laeuft der Server, das Handy
verbindet sich (z.B. ueber den Pi-Hotspot -- der Pi 3 hat WLAN onboard,
also kein USB-WLAN-Stick noetig), oeffnet die Web-Seite und sieht/bedient
das 8x8-Grid. Audio spielt
lokal auf dem Pi via pygame.mixer (Klinkenbuchse oder HDMI).

Aktivieren:
    export LEDMATRIX_HAL=web    # in main.py wird das ausgewertet
    python3 main.py

Optional:
    LEDMATRIX_HOST   default 0.0.0.0
    LEDMATRIX_PORT   default 8000
"""

import os
import time
import math
import array
import json
import random as _rnd
import threading
import http.server
import socketserver
from urllib.parse import urlparse

import config
import webcommon

try:
    import pygame
    pygame.mixer.init(frequency=config.AUDIO_RATE, channels=2, size=-16,
                      buffer=512)
    pygame.mixer.set_num_channels(config.AUDIO_CHANNELS)
    _HAVE_AUDIO = True
except Exception as _e:
    print("[web_hal] Audio nicht verfuegbar: {}".format(_e))
    _HAVE_AUDIO = False


_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "static")
_INDEX_BYTES = None


def _load_index():
    global _INDEX_BYTES
    if _INDEX_BYTES is None:
        with open(os.path.join(_STATIC_DIR, "index.html"), "rb") as f:
            _INDEX_BYTES = f.read()
    return _INDEX_BYTES


class _Handler(http.server.BaseHTTPRequestHandler):
    """HTTP-Handler. `hal` wird per Subclass-Attribut gesetzt."""

    hal = None
    protocol_version = "HTTP/1.1"

    def log_message(self, *a, **kw):
        return  # ruhig.

    # ---- GET ----
    def do_GET(self):
        path = urlparse(self.path).path
        if webcommon.try_serve_common(self, path):
            return
        if path in ("/", "/index.html"):
            self._send_bytes(_load_index(), "text/html; charset=utf-8")
        elif path == "/events":
            self._stream_events()
        elif path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_error(404)

    # ---- POST ----
    def do_POST(self):
        path = urlparse(self.path).path
        n = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(n) if n > 0 else b""
        if path == "/input":
            self._handle_input(body)
            return
        if path == "/menu":
            self.hal._request_menu()
            self._send_204()
            return
        if webcommon.try_serve_post_common(self, path):
            return
        self.send_error(404)

    def _handle_input(self, body):
        try:
            d = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(400)
            return
        events = d if isinstance(d, list) else [d]
        for e in events:
            try:
                self.hal._add_input(int(e["x"]), int(e["y"]), bool(e["p"]))
            except (KeyError, TypeError, ValueError):
                continue
        self._send_204()

    def _send_204(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_bytes(self, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ---- SSE-Stream: Display-Frames ----
    def _stream_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            cfg = json.dumps({
                "w": config.WIDTH,
                "h": config.HEIGHT,
                "menuButton": list(config.MENU_BUTTON),
                "menuHoldMs": config.MENU_HOLD_MS,
            })
            self.wfile.write(("event: config\ndata: " + cfg + "\n\n").encode())
            # initialen Frame mitschicken falls schon einer da ist
            with self.hal._frame_lock:
                init_hex = self.hal._frame_hex
            if init_hex:
                self.wfile.write(("data: " + init_hex + "\n\n").encode())
            self.wfile.flush()

            last_hex = init_hex
            min_dt = 1.0 / 30.0  # max 30 Frames/s an Browser
            last_sent_t = 0.0
            while True:
                got = self.hal._frame_event.wait(timeout=2.0)
                if not got:
                    # Heartbeat, falls Proxy die idle-Connection killen wuerde
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self.hal._frame_event.clear()
                now = time.monotonic()
                if now - last_sent_t < min_dt:
                    time.sleep(min_dt - (now - last_sent_t))
                    now = time.monotonic()
                with self.hal._frame_lock:
                    frame_hex = self.hal._frame_hex
                if frame_hex is None or frame_hex == last_hex:
                    continue
                self.wfile.write(("data: " + frame_hex + "\n\n").encode())
                self.wfile.flush()
                last_hex = frame_hex
                last_sent_t = now
        except (BrokenPipeError, ConnectionResetError, OSError):
            return


class _ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class WebHAL:
    """Phone-Bridge-HAL: Display+Touch laufen ueber Browser, Audio ueber Pi."""

    def __init__(self):
        # Display-Puffer
        self._buf = [[(0, 0, 0)] * config.WIDTH for _ in range(config.HEIGHT)]
        self._frame_hex = None
        self._frame_lock = threading.Lock()
        self._frame_event = threading.Event()

        # Input-State
        self._state = [[False] * config.WIDTH for _ in range(config.HEIGHT)]
        self._event_queue = []
        self._input_lock = threading.Lock()
        self._menu_hold_start = None
        self._menu_requested = False

        # Audio
        self._sounds = {}
        self._tone_cache = {}
        self._build_default_sounds()

        # HTTP-Server
        port = int(os.environ.get("LEDMATRIX_PORT", "8000"))
        host = os.environ.get("LEDMATRIX_HOST", "0.0.0.0")
        bound = type("_BoundHandler", (_Handler,), {"hal": self})
        self._server = _ThreadingServer((host, port), bound)
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True, name="WebHAL-HTTP")
        self._server_thread.start()
        print("[web_hal] HTTP server: http://{}:{}/  (Handy hier oeffnen)"
              .format(host, port))

    # ---- Display ----
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
        # 150 Zellen -> 900 Hex-Zeichen, zeilenweise.
        parts = []
        for row in self._buf:
            for (r, g, b) in row:
                parts.append("%02x%02x%02x" % (r, g, b))
        hex_str = "".join(parts)
        with self._frame_lock:
            if hex_str == self._frame_hex:
                return
            self._frame_hex = hex_str
        self._frame_event.set()

    # ---- Input ----
    def poll(self):
        # Touch-Events kommen async ueber HTTP rein. Wir muessen hier nur
        # die Menue-Halten-Logik anhand des aktuellen States pruefen.
        self._check_menu_hold(time.monotonic())

    def events(self):
        with self._input_lock:
            out, self._event_queue = self._event_queue, []
        return out

    def press_events(self):
        return [(x, y) for (x, y, p) in self.events() if p]

    def pressed(self):
        with self._input_lock:
            return [(x, y) for y in range(config.HEIGHT)
                    for x in range(config.WIDTH) if self._state[y][x]]

    def is_pressed(self, x, y):
        with self._input_lock:
            return self._state[y][x]

    def menu_requested(self):
        if self._menu_requested:
            self._menu_requested = False
            return True
        return False

    def _add_input(self, x, y, pressed):
        if not (0 <= x < config.WIDTH and 0 <= y < config.HEIGHT):
            return
        with self._input_lock:
            if bool(pressed) != self._state[y][x]:
                self._state[y][x] = bool(pressed)
                self._event_queue.append((x, y, bool(pressed)))

    def _request_menu(self):
        # Vom dedizierten "Menue"-Button im Browser ausgeloest.
        self._menu_requested = True

    def _check_menu_hold(self, now):
        mx, my = config.MENU_BUTTON
        with self._input_lock:
            held = self._state[my][mx]
        if held:
            if self._menu_hold_start is None:
                self._menu_hold_start = now
            elif (now - self._menu_hold_start) * 1000 >= config.MENU_HOLD_MS:
                self._menu_requested = True
        else:
            self._menu_hold_start = None

    # ---- Audio (identisch zu hal.py / sim_hal.py) ----
    def _build_default_sounds(self):
        if not _HAVE_AUDIO:
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
                v = int(max(-1.0, min(1.0,
                        (_rnd.random() * 2 - 1) * env * vol)) * 30000)
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
            print("[web_hal] Musik nicht abspielbar ({}): {}".format(path, e))

    def stop_music(self):
        if not _HAVE_AUDIO:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def shutdown(self):
        try:
            self._server.shutdown()
        except Exception:
            pass
        try:
            self._server.server_close()
        except Exception:
            pass
