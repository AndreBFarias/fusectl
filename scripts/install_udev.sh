#!/usr/bin/env bash
set -euo pipefail

RULES_SRC="$(dirname "$(readlink -f "$0")")/../udev/50-switch-rcm.rules"
RULES_DST="/etc/udev/rules.d/50-switch-rcm.rules"
OLD_RULES="/etc/udev/rules.d/99-switch-rcm.rules"

if [ "$(id -u)" -ne 0 ]; then
    echo "Execução requer root. Tentando com sudo..."
    exec sudo "$0" "$@"
fi

[ -f "$OLD_RULES" ] && rm -f "$OLD_RULES"

cp "$RULES_SRC" "$RULES_DST"
udevadm control --reload-rules
udevadm trigger

echo "Regra udev instalada: $RULES_DST"
echo "Reconecte o Switch em modo RCM para aplicar."
