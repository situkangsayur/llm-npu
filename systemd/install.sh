#!/usr/bin/env bash
# Install unit systemd untuk stack FLM (FLM NPU server + Open WebUI).
#
# PENTING: unit di-install & di-daemon-reload, TAPI TIDAK di-enable.
#          Jadi stack TIDAK auto-start saat boot — start manual saja.
#
# Pakai:  sudo bash systemd/install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Jalankan dengan sudo:  sudo bash systemd/install.sh" >&2
  exit 1
fi

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST=/etc/systemd/system

for unit in flm.service open-webui.service flm-stack.target; do
  install -m 0644 "$SRC/$unit" "$DEST/$unit"
  echo "  -> $DEST/$unit"
done

systemctl daemon-reload
echo
echo "Unit ter-install (TIDAK di-enable -> tidak auto-start saat boot)."
echo
echo "START seluruh stack :  sudo systemctl start flm-stack.target"
echo "STOP  seluruh stack :  sudo systemctl stop  flm-stack.target"
echo "STATUS              :  systemctl status flm.service open-webui.service"
echo "LOG FLM             :  journalctl -u flm.service -f"
echo
echo "Open WebUI -> http://localhost:3000   |   API FLM -> http://localhost:52625"
