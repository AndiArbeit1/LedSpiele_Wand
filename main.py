"""LED-Matrix Spielesammlung (4x4).

Ablauf pro Spiel:
    Menue (4 Kacheln)
      -> Level-Auswahl (1..4)
      -> Spiel laeuft
      -> Ergebnis-Feedback (Rekord ja/nein)
      -> zurueck ins Menue

Highscores/Statistiken werden persistent gespeichert (scoreboard.py) und
auf der Admin-Webseite angezeigt (/admin).

Bedienung:
- Menue:  Druck in eine der vier Kacheln startet das Spiel.
- Level:  Druck in eine der vier Reihen waehlt Level 1..4.
- Im Spiel: Taster oben rechts ca. 0.8s halten -> zurueck ins Menue.
  Alternativ jederzeit: beide unteren Ecken gleichzeitig, 5x hintereinander.

Start:
    sudo python3 main.py          (echte Hardware, auto-erkannt)
    LEDMATRIX_HAL=web python3 main.py   (Spielen im Handy-Browser)
"""

import config
from hal import HAL
from framework import run_game
import games
from menu import menu_loop
from select_screens import level_loop
from score_screen import run_score
import scoreboard


def main():
    hal = HAL()
    try:
        while True:
            cls = menu_loop(hal, games.ALL)

            if getattr(cls, "has_levels", True):
                level = level_loop(hal)
                if level is None:
                    continue  # Menue gehalten -> zurueck zur Spielauswahl
            else:
                level = 1  # Spiel ohne Level (z.B. Heatmap) startet direkt

            game = cls(hal)
            game.configure(level, 1)
            hal.stop_music()   # Lobby-Musik aus, solange gespielt wird
            result = run_game(hal, game)
            if result is None:
                continue  # Menue gehalten -> direkt zurueck

            if getattr(cls, "has_score_screen", False):
                score = result[0]
                is_record = False
                if score is not None:
                    is_record, _ = scoreboard.record(
                        cls.name, level, score,
                        higher_is_better=getattr(cls, "higher_is_better", True),
                    )
                run_score(hal, score=score, is_record=is_record,
                          base_color=cls.color)
    except KeyboardInterrupt:
        pass
    finally:
        hal.shutdown()


if __name__ == "__main__":
    main()
