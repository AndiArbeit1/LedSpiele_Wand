"""Piano Tiles (so viele Spalten/Reihen wie die Matrix hat).

Pro Note des Songs erscheint ein Tile oben in einer Spalte und faellt
nach unten. Erreicht es die unterste Reihe (Hit-Zone), muss der Taster
in dieser Spalte gedrueckt werden. Treffer = die Note erklingt -> der
Spieler "spielt" das Lied. Score = Anzahl Treffer.

ENDLOS-MODUS: Das gewaehlte Lied laeuft in einer Endlosschleife und wird
mit jeder Runde schneller (hoehere BPM + schnelleres Fallen). Das Spiel
endet erst, wenn vier Tiles verpasst wurden.

Level 1..4 = Start-Song + Start-BPM. Solo only.
Kein HUD -- Leben/Combo/Tempo werden nur ueber Sound + Hit-Zone-Flash
vermittelt (kein Rand-Aufblitzen bei schnelleren Schleifen).
"""

import config
import songs
from framework import Game


HIT_ZONE_Y = config.HEIGHT - 1   # unterste Reihe
MISS_LIVES = 1
SPEEDUP_PER_LOOP = 1.18          # +18% Tempo pro Schleife
MAX_BPM = 280                    # Deckel, damit es spielbar/stabil bleibt
LOOP_GAP_BEATS = 2               # kleine Pause vor dem Neustart der Schleife


class _Tile:
    __slots__ = ("lane", "y", "midi", "color", "active")

    def __init__(self, lane, y, midi, color):
        self.lane = lane
        self.y = y
        self.midi = midi
        self.color = color
        self.active = True


class PianoTilesGame(Game):
    name = "Piano"
    color = (255, 0, 0)             # Rot
    supports_multiplayer = False
    has_score_screen = True
    higher_is_better = True

    def reset(self):
        self.done = False
        self.song, self.base_bpm = songs.song_for_level(self.level)
        self.loops = 0
        self._apply_speed()
        self.tiles = []
        self.note_index = 0
        self.next_note_time = 0.6
        self.t = 0.0
        self.lives = MISS_LIVES
        self.score = 0
        self.combo = 0
        self.flash = 0.0
        self.bad_flash = 0.0
        self.over = False
        self.over_timer = 0.0

    def _apply_speed(self):
        """Setzt Tempo abhaengig von der aktuellen Schleifen-Zahl."""
        bpm = min(MAX_BPM, self.base_bpm * (SPEEDUP_PER_LOOP ** self.loops))
        self.bpm = bpm
        self.beat_seconds = 60.0 / bpm
        # Fall-Dauer von oben bis Hit-Zone; nach unten gedeckelt, damit
        # auch in schnellen Schleifen noch reagierbar.
        self.fall_seconds = max(0.8, 2.6 * 100.0 / bpm)
        self.fall_speed = (HIT_ZONE_Y + 1) / self.fall_seconds

    def _spawn_next_note(self):
        if self.note_index >= len(self.song["notes"]):
            # Lied zu Ende -> Endlosschleife: schneller von vorn.
            self.loops += 1
            self.note_index = 0
            self._apply_speed()
            self.hal.play("win")
            self.next_note_time = self.t + LOOP_GAP_BEATS * self.beat_seconds
            return
        midi, beats = self.song["notes"][self.note_index]
        lane = songs.lane_for_note(self.note_index, midi, config.WIDTH)
        self.tiles.append(_Tile(lane, -1.0, midi, self.song["color"]))
        self.note_index += 1
        self.next_note_time = self.t + beats * self.beat_seconds

    def update(self, dt):
        if self.over:
            self.over_timer += dt
            if self.over_timer > 1.3:
                self.finish(score=self.score)
            return

        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.bad_flash = max(0.0, self.bad_flash - dt)

        while self.t >= self.next_note_time:
            self._spawn_next_note()

        for tile in self.tiles:
            tile.y += self.fall_speed * dt

        # Verpasste Tiles.
        kept = []
        for tile in self.tiles:
            if not tile.active:
                continue
            if tile.y > HIT_ZONE_Y + 0.6:
                self.lives -= 1
                self.hal.play("miss")
                self.bad_flash = 0.22
                self.combo = 0
                if self.lives <= 0:
                    self.over = True
                continue
            kept.append(tile)
        self.tiles = kept

        # Taster -> Tile in der Hit-Zone der Spalte.
        for x, y in self.hal.press_events():
            hit_tile = None
            best_dist = 1.3
            for tile in self.tiles:
                if tile.lane == x:
                    dist = abs(tile.y - HIT_ZONE_Y)
                    if dist < best_dist:
                        best_dist = dist
                        hit_tile = tile
            if hit_tile is not None:
                hit_tile.active = False
                self.tiles.remove(hit_tile)
                self.combo += 1
                self.score += 1 + self.combo // 8
                self.hal.play_freq(songs.midi_to_freq(hit_tile.midi),
                                   dur=0.18, vol=0.5)
                self.flash = 0.12
            else:
                self.combo = 0
                self.hal.play("bad")
                self.bad_flash = 0.10

    def render(self):
        # Hit-Zone dezent markiert.
        for x in range(config.WIDTH):
            self.hal.set(x, HIT_ZONE_Y, (24, 24, 44))

        for tile in self.tiles:
            iy = int(round(tile.y))
            if 0 <= iy < config.HEIGHT:
                self.hal.set(tile.lane, iy, tile.color)

        if self.flash > 0:
            v = int(self.flash * 600)
            for x in range(config.WIDTH):
                self.hal.set(x, HIT_ZONE_Y, (0, v, 0))
        if self.bad_flash > 0:
            v = int(self.bad_flash * 500)
            for x in range(config.WIDTH):
                self.hal.set(x, HIT_ZONE_Y, (v, 0, 0))
