"""Songs fuer Piano Tiles.

Jede Note = (midi_pitch, beats).
Beim Spielen wird pro Note ein Tile gespawnt; trifft der Spieler das
Tile, wird der zugehoerige Ton ueber hal.play_freq() abgespielt -- so
ergibt die Folge der Treffer die Melodie.
"""

import random


def midi_to_freq(m):
    return 440.0 * (2 ** ((m - 69) / 12.0))


# ---- Bekannte Melodien (gemeinfrei, monophone Kurzfassungen) ----
# Reihenfolge = Level-Reihenfolge: ruhig/leicht zuerst, schnell zuletzt.

# Tetris-Theme (Korobeiniki, russisches Volkslied, gemeinfrei). Level 1.
TETRIS = [
    (76, 1), (71, 0.5), (72, 0.5), (74, 1), (72, 0.5), (71, 0.5),
    (69, 1), (69, 0.5), (72, 0.5), (76, 1), (74, 0.5), (72, 0.5),
    (71, 1.5), (72, 0.5), (74, 1), (76, 1),
    (72, 1), (69, 1), (69, 2),
    (74, 1), (77, 1), (81, 1), (79, 0.5), (77, 0.5),
    (76, 1.5), (72, 0.5), (76, 1), (74, 0.5), (72, 0.5),
    (71, 1), (71, 0.5), (72, 0.5), (74, 1), (76, 1),
    (72, 1), (69, 1), (69, 2),
]

# Twinkle Twinkle Little Star (gemeinfrei). Level 2.
TWINKLE = [
    (60, 1), (60, 1), (67, 1), (67, 1), (69, 1), (69, 1), (67, 2),
    (65, 1), (65, 1), (64, 1), (64, 1), (62, 1), (62, 1), (60, 2),
    (67, 1), (67, 1), (65, 1), (65, 1), (64, 1), (64, 1), (62, 2),
    (67, 1), (67, 1), (65, 1), (65, 1), (64, 1), (64, 1), (62, 2),
    (60, 1), (60, 1), (67, 1), (67, 1), (69, 1), (69, 1), (67, 2),
    (65, 1), (65, 1), (64, 1), (64, 1), (62, 1), (62, 1), (60, 2),
]

# Beethoven - Fuer Elise (Anfangsthema). Level 3.
FUER_ELISE = [
    (76, 0.5), (75, 0.5), (76, 0.5), (75, 0.5), (76, 0.5),
    (71, 0.5), (74, 0.5), (72, 0.5), (69, 1),
    (60, 0.5), (64, 0.5), (69, 0.5), (71, 1),
    (64, 0.5), (68, 0.5), (71, 0.5), (72, 1),
    (76, 0.5), (75, 0.5), (76, 0.5), (75, 0.5), (76, 0.5),
    (71, 0.5), (74, 0.5), (72, 0.5), (69, 1),
    (60, 0.5), (64, 0.5), (69, 0.5), (71, 1),
    (64, 0.5), (72, 0.5), (71, 0.5), (69, 2),
]

# Grieg - In der Halle des Bergkoenigs. Treibend, Level 4.
BERGKOENIG = [
    (69, 0.5), (71, 0.5), (72, 0.5), (74, 0.5), (76, 0.5), (72, 0.5), (76, 1),
    (75, 0.5), (71, 0.5), (75, 1),
    (69, 0.5), (71, 0.5), (72, 0.5), (74, 0.5), (76, 0.5), (72, 0.5),
    (76, 0.5), (79, 0.5),
    (77, 0.5), (74, 0.5), (72, 0.5), (71, 1),
]


SONGS = [
    {"name": "Tetris",            "notes": TETRIS,
     "color": (90, 170, 255)},
    {"name": "Twinkle Twinkle",   "notes": TWINKLE,
     "color": (255, 80, 80)},
    {"name": "Fuer Elise",        "notes": FUER_ELISE,
     "color": (200, 120, 255)},
    {"name": "Bergkoenig",        "notes": BERGKOENIG,
     "color": (80, 255, 120)},
]


# ---- Lobby-/Menue-Musik ----
# Eigene, frei loopende Arcade-Chiptune (gemeinfrei) im Attract-Mode-Stil:
# heller, treibender Arpeggio-Hook in C-Dur. (midi, beats); midi 0 = Pause.
LOBBY = [
    # Hook hoch (C-Dur-Arpeggio mit Wendung)
    (72, 0.5), (76, 0.5), (79, 0.5), (84, 0.5), (83, 0.5), (79, 0.5), (76, 0.5), (79, 0.5),
    # Antwort eine Stufe weiter (F/A)
    (77, 0.5), (81, 0.5), (84, 0.5), (81, 0.5), (79, 0.5), (76, 0.5), (72, 0.5), (74, 0.5),
    # Steigerung nach oben
    (76, 0.5), (79, 0.5), (83, 0.5), (84, 0.5), (86, 0.5), (84, 0.5), (79, 0.5), (76, 0.5),
    # Aufloesung zurueck zum Grundton
    (84, 1), (79, 0.5), (76, 0.5), (72, 1), (0, 0.5),
]
LOBBY_BPM = 132


# ---- BPM pro Level (genau 4 Level) ----
LEVEL_BPM = {1: 90, 2: 100, 3: 110, 4: 130}


def song_for_level(level):
    """level 1..4 = Song 1..4 mit zunehmender BPM."""
    idx = (max(1, level) - 1) % len(SONGS)
    song = SONGS[idx]
    bpm = LEVEL_BPM.get(level, 100)
    return song, bpm


def lane_for_note(note_index, midi_pitch, width):
    """Verteilt Noten ueber alle Spalten 0..width-1.

    Tonhoehe wird auf die volle Breite gemappt, dazu leichter
    deterministischer Jitter, damit nicht alles in einer Lane klebt.
    """
    pitch_min, pitch_max = 55, 76
    rng = pitch_max - pitch_min
    p = max(0.0, min(1.0, (midi_pitch - pitch_min) / rng))
    base = int(round(p * (width - 1)))
    jitter = (note_index * 7) % 3 - 1
    lane = base + jitter
    return max(0, min(width - 1, lane))
