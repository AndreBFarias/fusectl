#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# --- Verificação do ambiente virtual ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Ambiente virtual não encontrado. Execute ./install.sh primeiro."
    exit 1
fi

# --- Verificação de Python >= 3.10 ---
if ! "$VENV_DIR/bin/python" -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "Python >= 3.10 necessário. Recrie o venv: ./install.sh --reinstall"
    exit 1
fi

# --- Verificação de import ---
if ! "$VENV_DIR/bin/python" -c "import fusectl" 2>/dev/null; then
    echo "Pacote fusectl não importável. Execute ./install.sh para reinstalar."
    exit 1
fi

# --- Verificação de libusb (dependencia runtime do pyusb) ---
_check_libusb() {
    if ldconfig -p 2>/dev/null | grep -q libusb-1.0; then
        return 0
    fi
    if [ -f /usr/lib/libusb-1.0.so ] || [ -f /usr/lib64/libusb-1.0.so ]; then
        return 0
    fi
    if [ -f /usr/lib/x86_64-linux-gnu/libusb-1.0.so.0 ]; then
        return 0
    fi
    return 1
}

if ! _check_libusb; then
    echo "libusb não encontrada. Execute ./install.sh ou instale manualmente."
    echo "  apt: sudo apt install libusb-1.0-0"
    echo "  dnf: sudo dnf install libusb1"
    echo "  pacman: sudo pacman -S libusb"
    exit 1
fi

# --- Permissoes USB (Tegra RCM) ---
RULES_SRC="$SCRIPT_DIR/udev/50-switch-rcm.rules"
RULES_DST="/etc/udev/rules.d/50-switch-rcm.rules"
OLD_RULES="/etc/udev/rules.d/99-switch-rcm.rules"
UDEV_CHANGED=0
GROUP_CHANGED=0

if [ -f "$OLD_RULES" ]; then
    sudo rm -f "$OLD_RULES"
    UDEV_CHANGED=1
fi

if [ -f "$RULES_SRC" ]; then
    if [ ! -f "$RULES_DST" ]; then
        echo "Instalando regra udev para acesso USB ao Switch..."
        sudo cp "$RULES_SRC" "$RULES_DST"
        UDEV_CHANGED=1
    elif ! diff -q "$RULES_SRC" "$RULES_DST" &>/dev/null; then
        echo "Atualizando regra udev..."
        sudo cp "$RULES_SRC" "$RULES_DST"
        UDEV_CHANGED=1
    fi
fi

if [ "$UDEV_CHANGED" -eq 1 ]; then
    sudo udevadm control --reload-rules
    sudo udevadm trigger --action=change --subsystem-match=usb
    echo "Regra udev aplicada."
fi

if ! id -nG | grep -qw plugdev; then
    echo "Adicionando usuario ao grupo plugdev..."
    sudo usermod -aG plugdev "$(whoami)"
    GROUP_CHANGED=1
    echo "Grupo plugdev adicionado."
fi

# --- Execução ---
if [ "$GROUP_CHANGED" -eq 1 ]; then
    exec sg plugdev -c "$(printf '%q ' "$VENV_DIR/bin/python" -m fusectl "$@")"
fi

exec "$VENV_DIR/bin/python" -m fusectl "$@"
