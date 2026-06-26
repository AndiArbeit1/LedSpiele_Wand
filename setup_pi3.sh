#!/usr/bin/env bash
#
# Einmal-Setup fuer den Raspberry Pi 3 -- erledigt alles, was Raspberry Pi
# Imager beim Flashen NICHT macht (Hostname/User/Passwort/SSH/WLAN setzt
# ihr im Imager unter "Einstellungen bearbeiten", siehe ANSCHLUSS.md).
# Dieses Skript macht den Rest, einmalig, auf dem schon gebooteten Pi:
#   1. I2C aktivieren
#   2. Pakete installieren (apt + pip)
#   3. Dieses Projekt nach /home/pi/ledmatrix-pi kopieren
#   4. systemd-Dienst "ledmatrix" anlegen, aktivieren, starten
#
# MODUS (Argument, optional):
#   ./setup_pi3.sh            -> web   (Default): im Handy-Browser spielen,
#                                solange noch keine LED-Matrix gebaut ist.
#                                Laeuft als User 'pi', Hotspot via
#                                setup_hotspot.sh. -> http://10.42.0.1:8000/
#   ./setup_pi3.sh real       -> echte Matrix + Taster (spaeter, wenn die
#                                Hardware dran ist). Laeuft als root (GPIO),
#                                Spiel auf der Matrix, Browser nur /admin.
#
# Anders als beim Pi 2: der Pi 3 hat WLAN ONBOARD -- kein USB-WLAN-Stick
# noetig, weder fuers Internet beim Setup noch fuer den Hotspot-Modus.
# 32- oder 64-Bit Raspberry Pi OS (auch Lite) laeuft.
#
# Voraussetzung: Pi hat beim Setup Internet (onboard-WLAN oder Ethernet) --
# fuer apt/pip. Dieses Skript liegt im Projektordner und wird AUF DEM PI
# ausgefuehrt (Konsole am Bildschirm oder per SSH):
#   cd ~/ledmatrix-pi
#   chmod +x setup_pi3.sh
#   ./setup_pi3.sh            # bzw. ./setup_pi3.sh real

set -euo pipefail

MODE="${1:-web}"
case "$MODE" in
  web)  RUN_USER="pi" ;;
  real) RUN_USER="root" ;;   # GPIO/WS2812 brauchen root
  *) echo "Unbekannter Modus '$MODE' -- nutze 'web' oder 'real'." >&2; exit 1 ;;
esac

PROJECT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/home/pi/ledmatrix-pi"

echo "== Modus: $MODE  (Dienst laeuft als '$RUN_USER') =="

echo "== 1/4: I2C aktivieren =="
sudo raspi-config nonint do_i2c 0

echo "== 2/4: Pakete installieren (apt + pip) =="
sudo apt update
sudo apt install -y python3-pip python3-pygame i2c-tools
sudo pip3 install adafruit-circuitpython-neopixel smbus2 --break-system-packages

echo "== 3/4: Projekt nach $TARGET_DIR kopieren =="
sudo mkdir -p "$TARGET_DIR"
sudo rsync -a --exclude '__pycache__' --exclude 'setup_pi3.sh' \
  "$PROJECT_SRC"/ "$TARGET_DIR"/
sudo chown -R pi:pi "$TARGET_DIR"

echo "== 4/4: systemd-Dienst anlegen ($MODE) =="
sudo tee /etc/systemd/system/ledmatrix.service > /dev/null <<EOF
[Unit]
Description=LED Matrix 8x8
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=/home/pi/ledmatrix-pi
Environment=LEDMATRIX_HAL=$MODE
Environment=LEDMATRIX_PORT=8000
ExecStart=/usr/bin/python3 /home/pi/ledmatrix-pi/main.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ledmatrix.service

echo
echo "Fertig ($MODE-Modus). Status pruefen mit:"
echo "  journalctl -u ledmatrix -f"
if [ "$MODE" = "web" ]; then
  echo "Im Browser spielen: http://$(hostname -I | awk '{print $1}'):8000/"
  echo "Fuer Standalone-WLAN jetzt noch:  ./setup_hotspot.sh on"
  echo "  -> danach:  http://10.42.0.1:8000/"
else
  echo "Admin-Seite:  http://$(hostname -I | awk '{print $1}'):8000/admin"
fi
