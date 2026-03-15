#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
RULES_50="/etc/udev/rules.d/50-switch-rcm.rules"
RULES_99="/etc/udev/rules.d/99-switch-rcm.rules"
LOG_DIR="$HOME/.local/share/fusectl"

echo "=== fusectl - Desinstalação ==="
echo ""

if [ -d "$VENV_DIR" ]; then
    echo "Removendo ambiente virtual..."
    rm -rf "$VENV_DIR"
    echo "Ambiente virtual removido."
else
    echo "Ambiente virtual não encontrado."
fi

UDEV_REMOVED=0
for rules_file in "$RULES_50" "$RULES_99"; do
    if [ -f "$rules_file" ]; then
        echo "Removendo regra udev: $rules_file"
        sudo rm -f "$rules_file"
        UDEV_REMOVED=1
    fi
done

if [ "$UDEV_REMOVED" -eq 1 ]; then
    sudo udevadm control --reload-rules
    echo "Regras udev removidas."
else
    echo "Nenhuma regra udev encontrada."
fi

if [ -d "$LOG_DIR" ]; then
    echo "Removendo logs..."
    rm -rf "$LOG_DIR"
    echo "Logs removidos."
fi

echo ""
echo "=== Desinstalação concluída ==="
echo "Os arquivos do projeto permanecem em: $SCRIPT_DIR"
echo "Para remover completamente: rm -rf $SCRIPT_DIR"
