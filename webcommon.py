"""Gemeinsame HTTP-Bausteine fuer Web-Spielmodus und Admin-Seite.

Sowohl die Handy-Bridge (web_hal.py) als auch der reine Admin-Server
(admin_server.py, laeuft wenn die echte Hardware dran ist) liefern die
Admin-Seite und die Stats-API aus. Damit es nur eine Quelle gibt, liegen
die Routen hier.
"""

import os
import json
from urllib.parse import urlparse, parse_qs

import scoreboard
import lobbymusic

_ROOT = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_ROOT, "static")
_HEATMAP_PATH = os.path.join(_ROOT, "heatmap.json")
_cache = {}


def reset_heatmap():
    """Loescht die gesammelte Heatmap (heatmap.json). Beim naechsten Spiel
    faengt sie wieder bei null an."""
    try:
        if os.path.exists(_HEATMAP_PATH):
            os.remove(_HEATMAP_PATH)
        return True
    except Exception as e:
        print("[webcommon] Heatmap-Reset fehlgeschlagen:", e)
        return False


def static_bytes(name):
    """Laedt eine Datei aus static/ (gecached)."""
    if name not in _cache:
        with open(os.path.join(_STATIC_DIR, name), "rb") as f:
            _cache[name] = f.read()
    return _cache[name]


def stats_json():
    """Aktuelle Highscores/Statistiken als JSON-Bytes (nicht gecached)."""
    return json.dumps(scoreboard.to_dict(), ensure_ascii=False).encode("utf-8")


def try_serve_common(handler, path):
    """Behandelt GET fuer /admin, /api/stats und /admin.html.

    Liefert True, wenn die Route bedient wurde. Erwartet einen
    BaseHTTPRequestHandler mit den Hilfsmethoden _send_bytes.
    """
    if path in ("/admin", "/admin/", "/admin.html"):
        handler._send_bytes(static_bytes("admin.html"), "text/html; charset=utf-8")
        return True
    if path == "/api/stats":
        handler._send_bytes(stats_json(), "application/json; charset=utf-8")
        return True
    if path == "/api/lobby-music":
        data = {"tracks": lobbymusic.list_tracks(),
                "selected": lobbymusic.get_selected_id()}
        handler._send_bytes(json.dumps(data).encode("utf-8"),
                            "application/json; charset=utf-8")
        return True
    return False


def try_serve_post_common(handler, path):
    """Behandelt gemeinsame POST-Routen (Admin-Resets). True, wenn bedient.

    /api/reset-scores   -> alle Highscores/Statistiken loeschen
    /api/reset-heatmap  -> gesammelte Heatmap loeschen
    Antwortet selbst mit 204 (kein Body) -- funktioniert in Web- und
    Hardware-Modus, weil beide nur send_response/end_headers brauchen.
    """
    if path == "/api/reset-scores":
        scoreboard.reset()
    elif path == "/api/reset-heatmap":
        reset_heatmap()
    elif path == "/api/lobby-music":
        # Track-ID aus der Query (?id=...) -> gewaehlten Lobby-Track setzen.
        qs = parse_qs(urlparse(handler.path).query)
        lobbymusic.set_selected_id((qs.get("id") or [""])[0])
    else:
        return False
    handler.send_response(204)
    handler.send_header("Content-Length", "0")
    handler.end_headers()
    return True
