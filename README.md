# LED Matrix 8×8 — Pi Spielesammlung (v3.3, für Raspberry Pi 3)

**Acht Spiele** auf einem **8×8-Raster** mit **64 Tastern**. Pro Taster
sitzen **vier WS2812-LEDs** (alle vier leuchten gemeinsam), also
**256 LEDs** insgesamt — aus Spiel-Sicht bleibt es ein 8×8-Schirm.
Jedes Spiel hat **vier Level**. Solange keine Hardware dran ist, spielst du
im **Handy-Browser** (der Pi macht dafür sein **eigenes WLAN** — der
**Pi 3 hat WLAN onboard**, also ohne USB-WLAN-Stick); sobald die echte
Matrix angeschlossen ist, läuft alles auf der Matrix und im Browser gibt
es eine **Admin-Seite** mit Highscores und Statistiken.

Diese Version (v3.3) ist für den **Raspberry Pi 3** (WLAN onboard, läuft mit
**32- oder 64-Bit Raspberry Pi OS**).

Spiele und Level-Auswahl nutzen den vollen 8×8-Schirm. Das Spiel-Menü ist in
**acht Kacheln** aufgeteilt (2 Spalten × 4 Reihen, je 4×2). Die Level-Auswahl
nutzt **vier 4×4-Kacheln** (Quadranten).

## Die acht Spiele

| # | Spiel | Farbe | Ziel | Score |
|---|-------|-------|------|-------|
| 0 | **Piano Tiles** | blau | fallende Tiles in der richtigen Spalte unten treffen | Treffer (mehr = besser) |
| 1 | **Whack-a-Mole** | grün | leuchtenden Maulwurf antippen bevor er verschwindet | Treffer (mehr = besser) |
| 2 | **Lights Out** | bernstein | alle Lichter ausschalten (Klick togglet Kreuz) | Klicks (weniger = besser) |
| 3 | **Simon-Farben** | lila | gezeigte Farbsequenz nachtippen (4 Quadranten) | Sequenzlänge (mehr = besser) |
| 4 | **Neon Link** | cyan | Farbgruppen (≥2) auflösen; Challenge-Farbe = Bonus | Punkte (mehr = besser) |
| 5 | **Labyrinth** | cyan | scrollendes Labyrinth (größer als 8×8), Spieler bleibt mittig; über die vier Ränder steuern (rechts/links/oben/unten), zum Ausgang finden | Zeit (weniger = besser) |
| 6 | **Flappy** | orange | tippen = flattern, durch die Lücken; wird laufend schneller | Röhren (mehr = besser) |
| 7 | **Heatmap** | rot-orange | leer → drücken → 5 s zeigen wo **alle Spieler** je gedrückt haben (dauerhaft) → zurück ins Menü | — |

**Level 1–4** = leicht → schwer (Tempo bzw. Schwierigkeit).

Die **Kachel-Anordnung** im Menü (Index = obige #) — ohne Flips ist die
logische Sicht zugleich die Wand-Sicht:

```
0  1
2  3
4  5
6  7
```

Praktisch heißt das: oben-links **rot** (Spiel 0 Piano), oben-rechts **grün**
(Spiel 1 Whack) usw. — genau so erscheint es an der Wand (`FLIP_X = FLIP_Y =
False`).

### Heatmap — drück „zufällig", sieh das Muster aller vor dir

Schirm komplett leer → sobald jemand einen (scheinbar zufälligen) Taster
drückt, deckt sich für 5 Sekunden die **gesamte** Heatmap auf: der eigene
Druck **plus alle Drücke aller Spieler davor** (kalt = blau … heiß = weiß).
Der eigene Druck blinkt weiß, damit man sich im Muster wiederfindet → danach
automatisch zurück ins Menü. Es gibt keine Level-Auswahl.

Die Daten werden **dauerhaft** gesammelt (`heatmap.json` neben `scores.json`)
und überleben Neustarts — so wächst über viele Spieler ein Muster, das zeigt,
dass die „zufällige" Wahl gar nicht so zufällig ist. Zum Zurücksetzen einfach
`heatmap.json` löschen.

## Bedienung

- **Menü:** Druck in eine der acht Kacheln startet das zugehörige Spiel.
- **Level:** Druck in eine der vier 4×4-Kacheln wählt Level 1–4
  (oben links = 1, oben rechts = 2, unten links = 3, unten rechts = 4).
- **Zurück ins Menü:** Taster **oben rechts** ca. 0,8 s halten.
  (Im Browser zusätzlich der „Menü"-Knopf.)
- **Notausstieg ins Menü (jederzeit):** die **beiden unteren Ecken**
  (unten-links + unten-rechts) **gleichzeitig** drücken, **5×
  hintereinander** (zwischendurch loslassen). Funktioniert auch mitten im
  Spiel. (Einstellbar in `config.py`: `MENU_COMBO_*`.)
- Nach dem Spiel: die **erreichte Zahl** (Punkte / Züge / Zeit) wird angezeigt —
  bei einem **neuen Rekord** in Regenbogenfarben, sonst ruhig in der Spielfarbe.
  Größere Zahlen laufen als Laufband durch. Details stehen auf der Admin-Seite.

---

## 1. Schnellstart ohne Hardware (Handy-Browser)

Zum Ausprobieren brauchst du **keine** LEDs/Taster. Auf dem Pi:

```bash
sudo apt update
sudo apt install -y python3 python3-pygame
cd ~/ledmatrix-pi
LEDMATRIX_HAL=web python3 main.py
```

Am Handy/PC im Browser öffnen: `http://<pi-ip>:8000/`
Es erscheint das 8×8-Gitter — jede Zelle ist gleichzeitig Anzeige **und**
Touch-Taster. Die Admin-Seite liegt unter `http://<pi-ip>:8000/admin`.

> Audio läuft immer lokal auf dem Pi (Klinke/HDMI), nicht über das Handy.

### Pi als eigener WLAN-Hotspot (damit das Handy ihn ohne Heim-WLAN findet)

Dafür gibt es das Helfer-Skript **`setup_hotspot.sh`** (nutzt `nmcli`,
auf Raspberry Pi OS Bookworm Standard):

```bash
cd ~/ledmatrix-pi
chmod +x setup_hotspot.sh
./setup_hotspot.sh on            # Hotspot "LEDMATRIX" / Passwort "ledmatrix", persistent
./setup_hotspot.sh status        # zeigt, ob der Hotspot läuft
./setup_hotspot.sh off           # wieder normales WLAN
# eigene Werte:  ./setup_hotspot.sh on MeineSSID meinpasswort wlan0
```

Danach Handy mit dem WLAN **LEDMATRIX** verbinden und im Browser öffnen:
`http://10.42.0.1:8000/` (Admin: `http://10.42.0.1:8000/admin`).

Manuell ginge es auch direkt:

```bash
sudo nmcli device wifi hotspot ifname wlan0 ssid LEDMATRIX password ledmatrix
sudo nmcli connection modify Hotspot connection.autoconnect yes
sudo nmcli connection modify Hotspot connection.autoconnect-priority 100
```

---

## 2. Die Hardware anschließen

Du brauchst:

- Raspberry Pi 3 (32- oder 64-Bit Raspberry Pi OS, WLAN onboard)
- **WS2812 / WS2812B (NeoPixel)** — **4 LEDs pro Taster**, 8×8 Taster =
  **256 LEDs** (z.B. vier 8×8-Panels oder 64 Vierer-Cluster). Die vier
  LEDs einer Zelle müssen in der Kette direkt hintereinander liegen.
- **64 Taster** (z.B. Cherry MX)
- **4× MCP23017** (16-Bit I²C-Port-Expander) — 4 × 16 = 64 Pins für 64 Taster
- Taster-Platinen mit eigenen Pull-Down-Widerständen nach GND (siehe 2b)
- WLAN ist beim Pi 3 onboard — für SSH/Admin-Seite/Hotspot-Modus genügt
  das eingebaute `wlan0`, kein USB-WLAN-Stick nötig (Ethernet geht auch)
- **5V-Netzteil für die LEDs** (jetzt **256 WS2812** — bei Vollweiß
  ~15 A, also ein kräftiges Netzteil; in der Praxis durch die geringe
  Helligkeit/wenige gleichzeitig an deutlich weniger, aber großzügig
  dimensionieren — niemals über den Pi speisen)
- Empfohlen: 330–470 Ω in die LED-Datenleitung, 1000 µF Kondensator über
  5V/GND der LEDs, ggf. Pegelwandler 3,3V→5V für die Datenleitung

### a) LED-Matrix (WS2812) — 3 Drähte

| LED-Matrix | Raspberry Pi |
|------------|--------------|
| **DIN** (Dateneingang) | **GPIO21** (Pin 40) — über 330–470 Ω |
| **5V / VCC** | **externes 5V-Netzteil +** (nicht über den Pi speisen — 256 LEDs!) |
| **GND** | **GND** (Pin 6) — Netzteil-GND **und** Pi-GND verbinden! |

**Vier LEDs pro Taster:** Die Datenkette läuft durch alle 256 LEDs. Die
ersten vier LEDs gehören zu Taster 1, die nächsten vier zu Taster 2 usw.
(`LEDS_PER_CELL = 4` in `config.py`). Der Code setzt die vier LEDs einer
Zelle immer gemeinsam auf dieselbe Farbe; wie die vier physisch angeordnet
sind (2×2-Cluster, Reihe, …) ist egal, solange sie in der Kette
zusammenhängen. Die Reihenfolge der **Zellen** untereinander folgt
weiterhin `LED_SERPENTINE` (Default: Zickzack, Start unten links).

GPIO21 statt dem naheliegenderen GPIO18, weil GPIO18 Hardware-PWM ist —
dieselbe PWM-Peripherie, über die der Pi auch Audio an der Klinke ausgibt.
Liefe die Matrix über GPIO18, gäbe es Konflikte mit Sound über die Klinke
(Knacken/Flackern). GPIO21 nutzt die PCM-Hardware und kollidiert nicht
damit. Wer nur HDMI-Audio nutzt, kann auf GPIO18 zurückwechseln
(`LED_PIN = 18` in `config.py`).

Wichtig: Auf der „DIN"-Seite einspeisen (Pfeilrichtung), nicht „DOUT". Wenn
die Matrix im Zickzack verlötet ist (Kette beginnt **unten links** und
läuft nach oben: unterste Reihe links→rechts, nächste rechts→links …),
`LED_SERPENTINE = True` lassen (Default), sonst auf `False` in `config.py`.

So liegen die **Zell-Indizes der Kette** auf dem Panel (physische Sicht, wie
an der Wand — Index 0 unten-links, Zickzack nach oben):

```
oben    63 62 61 60 59 58 57 56
        48 49 50 51 52 53 54 55
        47 46 45 44 43 42 41 40
        32 33 34 35 36 37 38 39
        31 30 29 28 27 26 25 24
        16 17 18 19 20 21 22 23
        15 14 13 12 11 10  9  8
unten    0  1  2  3  4  5  6  7
```

Das ist eine **Hardware-Konstante**; `FLIP_X`/`FLIP_Y` ändern nur, welche
logische Spielzelle auf welche Kachel fällt, nicht den Kettenverlauf. Jede
Zelle steht für 4 LEDs (`LEDS_PER_CELL = 4`), die gemeinsam leuchten.

### b) Taster über 4× MCP23017 — I²C

Alle vier MCP23017 teilen sich denselben I²C-Bus; jeder bekommt über seine
Adress-Pins **A0/A1/A2** eine eigene Adresse:

| MCP23017 | A2 | A1 | A0 | Adresse | Taster |
|----------|------|------|------|---------|--------|
| Chip 0  | n.c. | n.c. | n.c. | **0x20** | 0–15  |
| Chip 1  | n.c. | n.c. | 5V   | **0x21** | 16–31 |
| Chip 2  | n.c. | 5V   | n.c. | **0x22** | 32–47 |
| Chip 3  | 5V   | n.c. | n.c. | **0x24** | 48–63 |

**n.c. = nicht angeschlossen.** Die Breakout-Platine hält die Adress-Pins per
internem Pull-Down auf LOW (= GND = `0`), also muss man nur die Pins, die HIGH
sein sollen, auf **5V** legen. Adress-Pin nichts dran → `0`, an 5V → `1`.

Gemeinsame Pins aller Chips:

| MCP23017 | Anschluss |
|----------|-----------|
| **VDD** | **5V** (externes Netzteil, gemeinsame Masse mit dem Pi) |
| **VSS** | **GND** (Pin 9 am Pi, gemeinsamer Massepunkt) |
| **SDA** | **GPIO2 / SDA** (Pin 3) — über **BSS138-Pegelwandler** (MCP-Seite 5V, Pi-Seite 3,3V) |
| **SCL** | **GPIO3 / SCL** (Pin 5) — über **BSS138-Pegelwandler** (MCP-Seite 5V, Pi-Seite 3,3V) |
| **RESET** (Pin 18 des Chips) | **nicht angeschlossen** — die Breakout-Platine hält RESET per internem Pull-up auf HIGH |
| **INTA / INTB** | nicht beschaltet (ungenutzt) |

> Weil die MCPs mit **5V** laufen, liegen SDA/SCL auf 5V-Pegel — sie dürfen
> **nicht direkt** an den 3,3-V-Pi. Der **BSS138-Pegelwandler** setzt beide
> Leitungen sauber auf 3,3V um (HV-Seite = 5V, LV-Seite = Pi-3,3V).

Jeder Taster: eine Seite an einen Port-Pin **GPA0…GPB7** eines MCP23017,
die andere Seite an **5V**. Pull-Down nach GND ist schon auf den
Taster-Platinen verbaut — deshalb bleiben die internen Pull-Ups des
MCP23017 aus. Offener Taster liest `0`, gedrückter `1`.
Genau das wertet der Code aus.

Der Default in `config.py` legt die Taster zeilenweise 0…63 auf die vier
Chips (16 pro Chip): Reihen 0–1 → Chip 0, Reihen 2–3 → Chip 1, Reihen 4–5 →
Chip 2, Reihen 6–7 → Chip 3. Wenn du anders verdrahtest, passe `SWITCH_MAP`
in `config.py` an (Schlüssel `(x, y)` → `(chip_index 0..3, bit 0..15)`).

### c) I²C aktivieren und prüfen

```bash
sudo raspi-config         # Interface Options -> I2C -> Enable, dann reboot
sudo apt install -y i2c-tools
i2cdetect -y 1            # muss 0x20, 0x21, 0x22, 0x24 zeigen
```

### d) Python-Bibliotheken für die echte Hardware

```bash
sudo apt install -y python3-pip python3-pygame
sudo pip3 install adafruit-circuitpython-neopixel smbus2 --break-system-packages
```

### e) Starten mit echter Hardware

```bash
cd ~/ledmatrix-pi
sudo LEDMATRIX_HAL=real python3 main.py
```

`sudo` ist für die WS2812-Ansteuerung über GPIO21 nötig. Gespielt wird jetzt
auf der Matrix. Parallel läuft automatisch der **Admin-Server** —
im Browser unter `http://<pi-ip>:8000/admin` siehst du Highscores + Statistiken.

---

## 3. Welcher Modus? (`LEDMATRIX_HAL`)

| Wert | Wirkung |
|------|---------|
| `web` | Spielen im Handy-Browser. Admin unter `/admin`. (Nutzen, solange keine Hardware dran ist.) |
| `real` | Echte Matrix + Taster. Admin-Server läuft automatisch mit. |
| `sim` | Pygame-Fenster auf dem Desktop (Entwicklung auf Windows/Linux). |
| `auto` | (Default) `real` wenn `neopixel`+`smbus2` da sind, sonst `sim`. |

Weitere Env-Vars: `LEDMATRIX_HOST` (default `0.0.0.0`),
`LEDMATRIX_PORT` (default `8000`).

---

## 4. Autostart per systemd

`/etc/systemd/system/ledmatrix.service`:

```ini
[Unit]
Description=LED Matrix 8x8
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/ledmatrix-pi
Environment=LEDMATRIX_HAL=real
Environment=LEDMATRIX_PORT=8000
ExecStart=/usr/bin/python3 /home/pi/ledmatrix-pi/main.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

(Für reinen Browser-Betrieb `LEDMATRIX_HAL=web` und `User=pi`.)

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ledmatrix.service
journalctl -u ledmatrix -f
```

---

## Auf dem PC testen (ohne Pi)

- **Browser:** `LEDMATRIX_HAL=web python main.py`, dann `http://localhost:8000/`.
- **Pygame-Fenster:** `pip install pygame`, dann `LEDMATRIX_HAL=sim python main.py`
  (Linksklick = Taster, Drag = mehrere, Rechtsklick = klemmen, M = Menü, Esc = Ende).
- **Schneller Funktionscheck headless:** `python _smoke.py`.

---

## Dateibaum

```
ledmatrix-pi/
  main.py             Game-Loop: Menü -> Level -> Spiel -> Ergebnis
  config.py           8x8, Pin-/MCP-Belegung, Level-Anzahl, Audio
  hal.py              echter HAL (WS2812 + 4x MCP23017); startet Admin-Server
  web_hal.py          Handy-Bridge (HTTP+SSE) + Admin-Routen
  admin_server.py     reiner Admin-/Statistik-Server (Hardware-Modus)
  webcommon.py        gemeinsame Web-Routen (/admin, /api/stats)
  scoreboard.py       persistente Highscores/Statistiken (scores.json)
  sim_hal.py          Pygame-Fenster (Dev)
  framework.py        Game-Basisklasse + Farb-/Zeichen-Helfer
  menu.py             Menü (acht 4x2-Kacheln) + Quadranten-Helfer
  select_screens.py   Level-Auswahl (vier 4x4-Kacheln)
  score_screen.py     Ergebnis: zeigt die Zahl (Rekord = Regenbogen)
  songs.py            Melodien für Piano Tiles
  setup_pi3.sh        Einmal-Setup (I2C, Pakete, systemd-Dienst)
  setup_hotspot.sh    Pi-WLAN-Hotspot an/aus (nmcli)
  games/              piano_tiles, whack, lights_out, simon,
                      neon_link, labyrinth, flappy, heatmap
  static/index.html   Spiel-UI (Browser)
  static/admin.html   Admin-/Statistik-Seite (Highscores)
```

## Hinweise

- Highscores landen in `scores.json` (wird automatisch angelegt).
- Die konkreten Werte stehen auf `/admin`, auf der Matrix gibt es nach jedem
  Spiel nur kurzes Farb-Feedback (Rekord = Regenbogen).
