# Anschluss-Anleitung — LED-Matrix 8×8, 4 LEDs/Taster (lightsout) — v3.3 für Pi 3

Was wo an den Raspberry Pi kommt. Alles bezieht sich auf die Belegung in
`config.py` (Default). Wenn du anders verdrahtest, musst du dort `SWITCH_MAP`
bzw. die Pins anpassen.

Koordinaten: **x = Spalte 0–7** (links → rechts), **y = Zeile 0–7** (oben → unten).

> Diese Version ist für den **Raspberry Pi 3**. Zwei Annehmlichkeiten:
> - **WLAN onboard** — für SSH/Admin-Webseite/Hotspot-Modus genügt das
>   eingebaute `wlan0`, kein USB-WLAN-Stick nötig (es unterstützt den
>   AP-Modus für den Hotspot). Ethernet geht natürlich auch.
> - **32- oder 64-Bit-OS** — beim Flashen einfach die aktuelle
>   Raspberry-Pi-OS-Version wählen.

---

## 1. Was du brauchst

- Raspberry Pi 3
- **WS2812 / WS2812B (NeoPixel)** — **4 LEDs pro Taster**, 8×8 = **256 LEDs**.
  Die vier LEDs einer Zelle müssen in der Datenkette direkt hintereinander
  liegen (LED 1–4 → Taster 1, LED 5–8 → Taster 2, …).
- **64 Taster** (z. B. Cherry MX)
- **4× MCP23017** (16-Bit-I²C-Port-Expander) → 4 × 16 = 64 Taster-Eingänge
- Taster-Platinen mit **eigenen Pull-Down-Widerständen nach GND** (siehe
  Abschnitt 4 — wichtig für die Polarität im Code)
- Für SSH/Admin-Webseite/Hotspot genügt das **onboard-WLAN (`wlan0`)** des
  Pi 3 — kein USB-WLAN-Stick nötig (Ethernet geht auch)
- **5-V-Netzteil für die LEDs** — jetzt **256 WS2812** (bei Vollweiß
  theoretisch ~15 A). Kräftiges Netzteil einplanen und **niemals über den
  Pi speisen**.
- Empfohlen: 330–470 Ω Widerstand in die LED-Datenleitung, 1000 µF Kondensator
  über 5 V / GND der LEDs, optional Pegelwandler 3,3 V → 5 V für die Datenleitung

---

## 2. Raspberry-Pi-Pins (40-Pin-Header) — die gebrauchten

| Pi-Pin | Signal | geht an |
|--------|--------|---------|
| **Pin 1** | 3,3 V | VCC **aller** MCP23017 |
| **Pin 3** | GPIO2 / SDA | SDA **aller** MCP23017 |
| **Pin 5** | GPIO3 / SCL | SCL **aller** MCP23017 |
| **Pin 6** | GND | GND der LEDs **und** Netzteil-GND |
| **Pin 9** | GND | GND **aller** MCP23017 + Taster-Pull-Downs |
| **Pin 40** | GPIO21 | LED **DIN** (über 330–470 Ω) |

> Wichtig: **Alle Massen verbinden** — Pi-GND, Netzteil-GND, LED-GND und
> PCF-GND müssen auf einem gemeinsamen Massepunkt liegen.

> Warum GPIO21 (Pin 40) und nicht GPIO18 (Pin 12): GPIO18 ist Hardware-PWM
> (PWM0) — dieselbe PWM-Peripherie, über die der Pi auch das analoge
> Audiosignal an der Klinke ausgibt (intern auf GPIO40/41). Laufen beide
> gleichzeitig, gibt es Konflikte (Knacken im Sound und/oder Flackern auf
> der Matrix). GPIO21 läuft über die PCM-Hardware und kollidiert nicht mit
> der Klinke. Wer **kein** Audio über die Klinke braucht (z. B. nur HDMI),
> kann stattdessen auch GPIO18 nehmen — dann `LED_PIN = 18` in `config.py`.

---

## 3. LED-Matrix (WS2812) — 3 Drähte

| LED-Matrix | Anschluss |
|------------|-----------|
| **DIN** (Dateneingang, Pfeilrichtung!) | **GPIO21 / Pin 40** über 330–470 Ω |
| **5V / VCC** | **+ vom externen 5-V-Netzteil** (nicht über den Pi) |
| **GND** | **Netzteil-GND und Pi-GND (Pin 6)** zusammen |

- Auf der **DIN**-Seite einspeisen, nicht „DOUT".
- **Vier LEDs pro Taster:** Die Kette läuft durch alle 256 LEDs. LED 1–4
  gehören zu Taster 1, LED 5–8 zu Taster 2 usw. (`LEDS_PER_CELL = 4` in
  `config.py`). Der Code setzt die vier LEDs einer Zelle immer gemeinsam
  auf dieselbe Farbe — wie sie physisch angeordnet sind (2×2-Cluster,
  Vierer-Reihe …) ist egal, Hauptsache sie hängen in der Kette zusammen.
- Die Reihenfolge der **Zellen** untereinander folgt `LED_SERPENTINE`:
  Zickzack, Kette beginnt **unten links** und läuft nach oben (unterste
  Zeile links→rechts, nächste rechts→links, …) → `True` lassen (Default).
  Bei „alle Zeilen gleich" auf `False`. Verläuft deine Kette anders,
  `_xy_to_cell()` / `_cell_led_indices()` in `hal.py` anpassen.
- Empfohlen: 1000 µF Elko direkt über 5 V / GND an der Matrix.

---

## 4. Taster über 4× MCP23017 (I²C)

Alle vier Chips hängen am **selben** I²C-Bus (SDA/SCL/VCC/GND gemeinsam).
Jeder Chip bekommt über seine Adress-Pins **A0/A1/A2** eine eigene Adresse:

| Chip | A2 | A1 | A0 | I²C-Adresse | Tasterzeilen |
|------|----|----|----|-------------|--------------|
| Chip 0 | GND | GND | GND | **0x20** | y = 0 und 1 |
| Chip 1 | GND | GND | 3V3 | **0x21** | y = 2 und 3 |
| Chip 2 | GND | 3V3 | GND | **0x22** | y = 4 und 5 |
| Chip 3 | GND | 3V3 | 3V3 | **0x23** | y = 6 und 7 |

Gemeinsam an **jedem** MCP23017:

| MCP23017-Pin | geht an |
|--------------|---------|
| VDD | Pi 3,3 V (Pin 1) |
| VSS | Pi GND (Pin 9) |
| SDA | Pi GPIO2 / SDA (Pin 3) |
| SCL | Pi GPIO3 / SCL (Pin 5) |
| **RESET (Pin 18)** | **3,3 V** (Pi Pin 1) — anders als beim PCF8575 muss dieser Pin auf HIGH liegen, sonst bleibt der Chip im Reset |
| INTA / INTB | nicht beschaltet (ungenutzt) |

**Jeder Taster:** eine Seite an einen Port-Pin (**GPA0…GPB7**) des Chips,
die andere Seite an **3,3 V**. Eure Taster-Platinen haben bereits eigene
Pull-Down-Widerstände vom Port-Pin nach GND — deshalb **keine** internen
Pull-Ups im MCP23017 aktivieren (macht der Code auch nicht mehr). Offener
Taster = `0` (vom Pull-Down nach Masse gezogen), gedrückter Taster = `1`
(zieht den Pin auf VCC). Genau das wertet der Code so aus.

---

## 5. Welcher Taster an welchen Chip-Pin (Default-Belegung)

Pin-Namen des MCP23017: Port A = **GPA0…GPA7**, Port B = **GPB0…GPB7**.
(Im Code: Byte 0 = GPA0–GPA7, Byte 1 = GPB0–GPB7.)

### Chip 0 — Adresse 0x20
| Taster (x,y) | Pin |  | Taster (x,y) | Pin |
|---|---|---|---|---|
| (0,0) | GPA0 | | (0,1) | GPB0 |
| (1,0) | GPA1 | | (1,1) | GPB1 |
| (2,0) | GPA2 | | (2,1) | GPB2 |
| (3,0) | GPA3 | | (3,1) | GPB3 |
| (4,0) | GPA4 | | (4,1) | GPB4 |
| (5,0) | GPA5 | | (5,1) | GPB5 |
| (6,0) | GPA6 | | (6,1) | GPB6 |
| (7,0) | GPA7 | | (7,1) | GPB7 |

### Chip 1 — Adresse 0x21
| Taster (x,y) | Pin |  | Taster (x,y) | Pin |
|---|---|---|---|---|
| (0,2) | GPA0 | | (0,3) | GPB0 |
| (1,2) | GPA1 | | (1,3) | GPB1 |
| (2,2) | GPA2 | | (2,3) | GPB2 |
| (3,2) | GPA3 | | (3,3) | GPB3 |
| (4,2) | GPA4 | | (4,3) | GPB4 |
| (5,2) | GPA5 | | (5,3) | GPB5 |
| (6,2) | GPA6 | | (6,3) | GPB6 |
| (7,2) | GPA7 | | (7,3) | GPB7 |

### Chip 2 — Adresse 0x22
| Taster (x,y) | Pin |  | Taster (x,y) | Pin |
|---|---|---|---|---|
| (0,4) | GPA0 | | (0,5) | GPB0 |
| (1,4) | GPA1 | | (1,5) | GPB1 |
| (2,4) | GPA2 | | (2,5) | GPB2 |
| (3,4) | GPA3 | | (3,5) | GPB3 |
| (4,4) | GPA4 | | (4,5) | GPB4 |
| (5,4) | GPA5 | | (5,5) | GPB5 |
| (6,4) | GPA6 | | (6,5) | GPB6 |
| (7,4) | GPA7 | | (7,5) | GPB7 |

### Chip 3 — Adresse 0x23
| Taster (x,y) | Pin |  | Taster (x,y) | Pin |
|---|---|---|---|---|
| (0,6) | GPA0 | | (0,7) | GPB0 |
| (1,6) | GPA1 | | (1,7) | GPB1 |
| (2,6) | GPA2 | | (2,7) | GPB2 |
| (3,6) | GPA3 | | (3,7) | GPB3 |
| (4,6) | GPA4 | | (4,7) | GPB4 |
| (5,6) | GPA5 | | (5,7) | GPB5 |
| (6,6) | GPA6 | | (6,7) | GPB6 |
| (7,6) | GPA7 | | (7,7) | GPB7 |

Merkregel: **gerade Zeile (y) → Port A (GPA0–GPA7)**, **ungerade Zeile →
Port B (GPB0–GPB7)**; die Spalte x ist die Pin-Nummer 0–7 innerhalb des
Ports.

> Wenn du anders verdrahtest, einfach `SWITCH_MAP` in `config.py` anpassen:
> Schlüssel `(x, y)` → `(chip_index 0..3, bit 0..15)`, wobei bit 0–7 =
> GPA0–GPA7 und bit 8–15 = GPB0–GPB7.

---

## 6. I²C aktivieren und prüfen

```bash
sudo raspi-config          # Interface Options -> I2C -> Enable, dann reboot
sudo apt install -y i2c-tools
i2cdetect -y 1             # muss 0x20 0x21 0x22 0x23 zeigen
```

---

## 7. Software für die echte Hardware

```bash
sudo apt install -y python3-pip python3-pygame
sudo pip3 install adafruit-circuitpython-neopixel smbus2 --break-system-packages
```

Auf echten Betrieb umstellen — in `/etc/systemd/system/ledmatrix.service`:
```ini
Environment=LEDMATRIX_HAL=real
```
Dann:
```bash
sudo systemctl restart ledmatrix
journalctl -u ledmatrix -f      # Log mitlesen
```

Schneller Test ohne systemd:
```bash
cd ~/ledmatrix-pi
sudo LEDMATRIX_HAL=real python3 main.py
```
(`sudo` ist für die WS2812-Ansteuerung über GPIO21 nötig.) Highscores/Statistik
laufen dann automatisch unter `http://lightsout:8000/admin`.

---

## 8. Schnell-Checkliste

1. [ ] 5-V-Netzteil an LED-5V/GND, **GND mit Pi-GND verbunden**
2. [ ] LED-DIN über Widerstand an GPIO21 (Pin 40)
3. [ ] 4× MCP23017: VDD→3,3V, VSS→GND, SDA→Pin 3, SCL→Pin 5, **RESET→3,3V**
4. [ ] MCP-Adressen per A0/A1/A2 auf 0x20/0x21/0x22/0x23 gestrappt
5. [ ] 64 Taster: je 1 Pin am MCP (siehe Tabellen), andere Seite an 3,3V
   (Pull-Down nach GND ist schon auf den Taster-Platinen)
6. [ ] `i2cdetect -y 1` zeigt 0x20–0x23
7. [ ] `LEDMATRIX_HAL=real`, Dienst neu gestartet
