from . import (piano_tiles, whack, lights_out, simon,
               neon_link, labyrinth, flappy, heatmap)

# Acht Spiele, Reihenfolge = Menue-Reihenfolge (2x4-Kacheln).
#   0 piano       1 whack
#   2 lights      3 simon
#   4 neon_link   5 labyrinth
#   6 flappy      7 heatmap (Viewer der global gesammelten Heatmap)
ALL = [
    piano_tiles.PianoTilesGame,   # 0  rot
    whack.WhackGame,              # 1  gruen
    lights_out.LightsOutGame,     # 2  blau
    simon.SimonGame,              # 3  gelb
    neon_link.NeonLinkGame,       # 4  magenta
    labyrinth.LabyrinthGame,      # 5  cyan (scrollendes Labyrinth)
    flappy.FlappyGame,            # 6  orange
    heatmap.HeatmapGame,          # 7  violett (Hintergrund-Heatmap-Viewer)
]
