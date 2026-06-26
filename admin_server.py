"""Reiner Admin-/Statistik-Webserver.

Laeuft, wenn die echte Hardware angeschlossen ist: gespielt wird dann auf
der LED-Matrix, aber Highscores und Statistiken kann man im Browser unter
http://<pi-ip>:8000/ ansehen. Kein Spiel-Display, keine Eingaben -- nur
Lesen.

Wird von hal.py automatisch gestartet (Thread, daemon). Port via
LEDMATRIX_PORT (default 8000), Host via LEDMATRIX_HOST (default 0.0.0.0).
"""

import os
import threading
import http.server
import socketserver
from urllib.parse import urlparse

import webcommon


class _AdminHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # Callback "zurueck ins Menue" -- von start() gesetzt (HAL._request_menu).
    on_menu = None

    def log_message(self, *a, **kw):
        return

    def _send_bytes(self, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            # Im Hardware-Modus gibt es keine Spiel-Seite -> direkt Admin.
            self._send_bytes(webcommon.static_bytes("admin.html"),
                             "text/html; charset=utf-8")
            return
        if webcommon.try_serve_common(self, path):
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        # Drain Body (sonst klemmt keep-alive).
        n = int(self.headers.get("Content-Length", "0") or "0")
        if n > 0:
            try:
                self.rfile.read(n)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
        if path == "/menu":
            if callable(type(self).on_menu):
                try:
                    type(self).on_menu()
                except Exception as e:
                    print("[admin_server] Menue-Request fehlgeschlagen:", e)
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if webcommon.try_serve_post_common(self, path):
            return
        self.send_error(404)


class _ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start(on_menu=None):
    """Startet den Admin-Server im Hintergrund. Liefert die Server-Instanz
    (oder None, falls der Port nicht gebunden werden konnte).

    on_menu: optionaler Callback, den die Admin-Seite per POST /menu ausloest
    (zurueck ins Menue auf der echten Matrix).
    """
    _AdminHandler.on_menu = staticmethod(on_menu) if on_menu else None
    port = int(os.environ.get("LEDMATRIX_PORT", "8000"))
    host = os.environ.get("LEDMATRIX_HOST", "0.0.0.0")
    try:
        server = _ThreadingServer((host, port), _AdminHandler)
    except OSError as e:
        print("[admin_server] Port {} nicht verfuegbar: {}".format(port, e))
        return None
    threading.Thread(target=server.serve_forever, daemon=True,
                     name="AdminHTTP").start()
    print("[admin_server] Admin/Stats: http://{}:{}/admin".format(host, port))
    return server
