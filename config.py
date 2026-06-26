"""Hardware-Konfiguration (8x8).

Plattform: Raspberry Pi 3 mit CPython (v3.3 -- fuer den Pi 3, WLAN onboard,
           also kein USB-WLAN-Stick fuer den Hotspot noetig; laeuft mit
           32- oder 64-Bit Raspberry Pi OS).
Matrix:    8x8 logisches Raster, aber VIER WS2812-LEDs pro Taster/Zelle
           (NeoPixel) ueber GPIO21. 8 * 8 * 4 = 256 LEDs in der Kette.
           Die vier LEDs einer Zelle liegen direkt hintereinander in der
           Kette ("1,2,3,4 gehoeren zu Taster 1; 5,6,7,8 zu Taster 2"
           usw.) und leuchten immer gemeinsam in derselben Farbe -- aus
           Spiel-Sicht bleibt es ein 8x8-Raster.
Switches:  64 Taster (z.B. Cherry MX), jeder direkt an einem Pin eines
           MCP23017 16-bit I2C-IO-Expanders. 64 Pins = vier Chips
           (4 * 16 = 64).

Die vier MCP23017 sitzen direkt am I2C-Bus 1 auf den Adressen 0x20, 0x21,
0x22 und 0x24 (wie auf der laufenden ESP32-Hardware; vierter Chip auf 0x24,
nicht 0x23 -- mit i2cdetect bestaetigen). Per Adress-Pins A0..A2 einstellbar.
Kein Multiplexer noetig. Anpassen falls anders verkabelt.

Spiele und Spiel-Menue nutzen den vollen 8x8-Schirm; das Auswahl-Menue
und die Level-Auswahl bestehen aus 4x4-Kacheln (vier Quadranten).
"""

# ---- LED-Matrix ----
WIDTH = 8
HEIGHT = 8

# Vier physische WS2812-LEDs pro logischer Zelle/Taster. Die vier liegen
# in der Kette direkt hintereinander (Zelle 0 -> LED 0..3, Zelle 1 ->
# LED 4..7, usw.) und werden immer gemeinsam gesetzt.
LEDS_PER_CELL = 4

NUM_CELLS = WIDTH * HEIGHT                 # 64 logische Zellen / Taster
NUM_PIXELS = NUM_CELLS * LEDS_PER_CELL     # 256 echte LEDs

LED_PIN = 21
# 21 statt 18: laeuft ueber PCM statt PWM-Hardware, damit es nicht mit dem
# analogen Audio-Ausgang (Klinke) kollidiert, der intern ebenfalls die
# PWM-Peripherie nutzt.
LED_BRIGHTNESS = 0.3
# True, wenn die LED-Streifen reihenweise im Zickzack verloetet sind.
# Kette beginnt bei Reihe y=0: gerade Reihen links->rechts, ungerade Reihen
# rechts->links, usw. (identisch zur ESP32-Vorlage tileboard.py). Bei sauber
# verdrahteter "alle Reihen gleich"-Matrix auf False setzen.
LED_SERPENTINE = True

# ---- I2C / MCP23017 ----
# Jeder MCP23017 ist als Dict definiert:
#   bus: I2C-Bus-Nummer am Pi (typisch 1).
#   address: I2C-Adresse (0x20..0x27, per Adress-Pins A0..A2 einstellbar).
#   mux_channel: Kanal am TCA9548A (0..7) oder None falls direkt am Bus.
# Adressen wie auf der laufenden ESP32-Hardware: 0x20, 0x21, 0x22, 0x24.
# ACHTUNG: der vierte Chip (Reihen 6/7) sitzt auf 0x24, NICHT 0x23 -- bitte
# mit `i2cdetect -y 1` bzw. `hwtest.py --scan-only` bestaetigen und hier
# anpassen, falls dein Chip doch auf 0x23 antwortet.
MCP_CHIPS = [
    {"bus": 1, "address": 0x20, "mux_channel": None},
    {"bus": 1, "address": 0x21, "mux_channel": None},
    {"bus": 1, "address": 0x22, "mux_channel": None},
    {"bus": 1, "address": 0x24, "mux_channel": None},
]

# TCA9548A Multiplexer-Adresse. Auf None setzen, falls kein Multiplexer.
# Fuer 8x8 (64 Taster, vier Chips an 0x20/0x21/0x22/0x24) nicht noetig.
MUX_BUS = 1
MUX_ADDRESS = None


# ---- Orientierung (Montage an der Wand korrigieren) ----
# Wirkt GEMEINSAM auf LEDs und Taster, damit "gedrueckte Kachel = leuchtende
# Kachel" konsistent bleibt. Logische Spiel-Koordinate (0,0) = oben-links.
# FLIP_X spiegelt links/rechts, FLIP_Y spiegelt oben/unten; beide zusammen
# = 180deg-Drehung (Panel steht auf dem Kopf an der Wand).
FLIP_X = False
FLIP_Y = True


def _phys_to_button(px, py):
    """Physische Kachel (px, py) -> (chip_index, bit_index 0..15).

    Wie auf der ESP32-Hardware (tileboard.tile_to_button): Chip = py//2,
    gerade Reihe -> Port A (bit = px), ungerade Reihe -> Port B (bit = 8+px).
    """
    chip_idx = py // 2
    bit_idx = px if (py % 2 == 0) else (8 + px)
    return (chip_idx, bit_idx)


def _build_default_switch_map():
    """Logische (x, y) -> (chip_index, bit_index), inkl. FLIP_X/FLIP_Y.

    Die logische Koordinate wird per Flags auf die physische Kachel gedreht
    und dann auf die Taster-Verdrahtung abgebildet.
    """
    mapping = {}
    for y in range(HEIGHT):
        for x in range(WIDTH):
            px = (WIDTH - 1 - x) if FLIP_X else x
            py = (HEIGHT - 1 - y) if FLIP_Y else y
            mapping[(x, y)] = _phys_to_button(px, py)
    return mapping


# (x, y) -> (chip_index, bit_index 0..15)
# Anpassen wenn deine Verdrahtung anders ist.
SWITCH_MAP = _build_default_switch_map()

DEBOUNCE_MS = 25
SCAN_INTERVAL_MS = 5

# ---- Audio ----
AUDIO_RATE = 22050
AUDIO_CHANNELS = 16

# ---- Menue ----
# Taster oben rechts ca. 0.8s halten -> zurueck ins Menue.
MENU_BUTTON = (WIDTH - 1, 0)
MENU_HOLD_MS = 800

# Geheim-Kombi: die beiden UNTEREN Ecken (unten-links + unten-rechts)
# gleichzeitig druecken, MENU_COMBO_COUNT mal hintereinander -> jederzeit
# zurueck ins Menue. Jedes "gleichzeitig gedrueckt" zaehlt einmal (man muss
# zwischendurch mindestens eine Ecke loslassen). Vergeht zwischen zwei
# Doppel-Druecken mehr als MENU_COMBO_RESET_MS, faengt die Zaehlung neu an.
MENU_COMBO_CELLS = [(0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1)]
MENU_COMBO_COUNT = 5
MENU_COMBO_RESET_MS = 2000

# ---- Level ----
# Genau vier Level pro Spiel.
NUM_LEVELS = 4

# ---- Loop ----
TARGET_FPS = 60
