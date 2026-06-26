"""Lobby-Musik-Auswahl.

Verwaltet, welcher Musik-Track im Menue (Lobby) laeuft. Die Auswahl wird
persistent in lobby_music.json gespeichert (neben scores.json) und kann
ueber die Admin-Seite umgestellt werden. Das Menue liest die Auswahl beim
Abspielen, der Web-Handler setzt sie.
"""

import os
import json

_ROOT = os.path.dirname(os.path.abspath(__file__))
_MUSIC_DIR = os.path.join(_ROOT, "music")
_SEL_PATH = os.path.join(_ROOT, "lobby_music.json")

# Sonder-ID: Lobby-Musik komplett aus (im Web-Interface waehlbar).
OFF_ID = "off"

# Verfuegbare Tracks (Reihenfolge = Anzeige auf der Admin-Seite).
TRACKS = [
    {"id": "retro",    "name": "Retro Arcade", "file": "retro.mp3"},
    {"id": "fortnite", "name": "Fortnite OG",  "file": "fortnite.mp3"},
]

# Standard-Track (die neue Retro-Arcade-Musik).
DEFAULT_ID = "retro"


def list_tracks():
    # "Aus" zuerst, damit man die Lobby-Musik im Web abschalten kann.
    return [{"id": OFF_ID, "name": "Aus", "file": None}] + TRACKS


def _valid(tid):
    return tid == OFF_ID or any(t["id"] == tid for t in TRACKS)


def is_off():
    return get_selected_id() == OFF_ID


def get_selected_id():
    """Aktuell gewaehlte Track-ID (oder Default, wenn nichts/kaputt)."""
    try:
        with open(_SEL_PATH, "r", encoding="utf-8") as f:
            tid = json.load(f).get("id")
        if _valid(tid):
            return tid
    except Exception:
        pass
    return DEFAULT_ID


def set_selected_id(tid):
    """Track-ID waehlen + persistent speichern. True bei Erfolg."""
    if not _valid(tid):
        return False
    try:
        tmp = _SEL_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"id": tid}, f)
        os.replace(tmp, _SEL_PATH)
        return True
    except Exception as e:
        print("[lobbymusic] Speichern fehlgeschlagen:", e)
        return False


def selected_file():
    """Voller Pfad zur MP3 des aktuell gewaehlten Tracks, oder None wenn aus."""
    tid = get_selected_id()
    if tid == OFF_ID:
        return None
    for t in TRACKS:
        if t["id"] == tid:
            return os.path.join(_MUSIC_DIR, t["file"])
    return os.path.join(_MUSIC_DIR, TRACKS[0]["file"])
