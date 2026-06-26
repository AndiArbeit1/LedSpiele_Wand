#!/usr/bin/env bash
#
# Macht aus dem Raspberry Pi einen eigenen WLAN-Hotspot, damit man OHNE
# Heim-WLAN mit dem Handy zum Spielen/Testen verbinden kann (Web-Modus).
#
# Verwendung:
#   ./setup_hotspot.sh on   [SSID] [PASSWORT] [IFACE]   Hotspot anschalten (persistent)
#   ./setup_hotspot.sh off                              Hotspot aus, normales WLAN
#   ./setup_hotspot.sh status                           Status anzeigen
#
# Default: SSID=LEDMATRIX  Passwort=ledmatrix  IFACE=wlan0
# Nach dem Anschalten: Handy mit dem WLAN "LEDMATRIX" verbinden und im
# Browser http://10.42.0.1:8000/ oeffnen.
#
# Voraussetzung: NetworkManager (nmcli) -- auf Raspberry Pi OS Bookworm Default.

set -euo pipefail

CMD="${1:-status}"
SSID="${2:-LEDMATRIX}"
PASS="${3:-ledmatrix}"
IFACE="${4:-wlan0}"

case "$CMD" in
  on)
    if [ "${#PASS}" -lt 8 ]; then
      echo "Passwort muss mindestens 8 Zeichen haben." >&2
      exit 1
    fi
    echo "Schalte Hotspot '$SSID' auf $IFACE an ..."
    sudo nmcli device wifi hotspot ifname "$IFACE" ssid "$SSID" password "$PASS"
    # Persistent machen (ueberlebt Reboot).
    sudo nmcli connection modify Hotspot connection.autoconnect yes || true
    sudo nmcli connection modify Hotspot connection.autoconnect-priority 100 || true
    echo
    echo "Fertig. Handy mit WLAN '$SSID' (Passwort '$PASS') verbinden,"
    echo "dann im Browser oeffnen:  http://10.42.0.1:8000/"
    echo "Admin/Statistik:          http://10.42.0.1:8000/admin"
    ;;
  off)
    echo "Schalte Hotspot aus ..."
    sudo nmcli connection down Hotspot 2>/dev/null || true
    sudo nmcli connection modify Hotspot connection.autoconnect no 2>/dev/null || true
    echo "Hotspot aus. Der Pi verbindet sich wieder mit normalem WLAN (falls konfiguriert)."
    ;;
  status)
    echo "Aktive Verbindungen:"
    nmcli -t -f NAME,TYPE,DEVICE connection show --active || true
    echo
    if nmcli -t -f NAME connection show --active | grep -q '^Hotspot$'; then
      echo "-> Hotspot ist AKTIV. Spielen: http://10.42.0.1:8000/"
    else
      echo "-> Hotspot ist AUS."
    fi
    ;;
  *)
    echo "Verwendung: $0 {on|off|status} [SSID] [PASSWORT] [IFACE]" >&2
    exit 1
    ;;
esac
