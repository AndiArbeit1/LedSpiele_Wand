"""Persistente Highscores + Statistiken.

Speichert pro Spiel und Level den Bestwert sowie ein paar Statistiken
(Anzahl Spiele, letzter Wert, letzter Zeitpunkt). Wird nach jedem Spiel
ueber record() aktualisiert und liegt als JSON neben diesem Modul.

Die Admin-Webseite liest denselben Store ueber to_dict() aus.
"""

import os
import json
import time
import threading


_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")
_lock = threading.Lock()
_data = None


def _empty():
    return {"games": {}, "total_plays": 0}


def _load():
    global _data
    if _data is not None:
        return _data
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            _data = json.load(f)
        if not isinstance(_data, dict) or "games" not in _data:
            _data = _empty()
    except Exception:
        _data = _empty()
    return _data


def _save():
    try:
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _PATH)
    except Exception as e:
        print("[scoreboard] Speichern fehlgeschlagen: {}".format(e))


def record(game, level, score, higher_is_better=True):
    """Traegt ein Spielergebnis ein. Liefert (is_record, best_score).

    Bei higher_is_better=False (z.B. Lights Out: weniger Klicks = besser)
    zaehlt der kleinere Wert als Bestwert.
    """
    if score is None:
        return (False, None)
    score = int(score)
    level = int(level)
    with _lock:
        d = _load()
        g = d["games"].setdefault(game, {
            "plays": 0, "levels": {}, "last_score": None, "last_ts": None,
            "higher_is_better": bool(higher_is_better),
        })
        g["higher_is_better"] = bool(higher_is_better)
        g["plays"] += 1
        g["last_score"] = score
        g["last_ts"] = int(time.time())
        d["total_plays"] += 1

        lk = str(level)
        lvl = g["levels"].setdefault(lk, {"best": None, "plays": 0})
        lvl["plays"] += 1
        is_record = False
        if lvl["best"] is None:
            lvl["best"] = score
            is_record = True
        else:
            if higher_is_better and score > lvl["best"]:
                lvl["best"] = score
                is_record = True
            elif not higher_is_better and score < lvl["best"]:
                lvl["best"] = score
                is_record = True
        best = lvl["best"]
        _save()
        return (is_record, best)


def best(game, level):
    with _lock:
        d = _load()
        g = d["games"].get(game)
        if not g:
            return None
        lvl = g["levels"].get(str(int(level)))
        return lvl["best"] if lvl else None


def to_dict():
    """Komplettkopie fuer die Admin-Seite."""
    with _lock:
        d = _load()
        return json.loads(json.dumps(d))


def reset():
    """Loescht alle Highscores/Statistiken (Admin-Reset)."""
    global _data
    with _lock:
        _data = _empty()
        _save()
