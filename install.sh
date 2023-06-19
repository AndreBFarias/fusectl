#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=== fusectl - Instalação ==="
echo ""

# --- Verificação de Python >= 3.10 ---
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Python >= 3.10 não encontrado. Instale e tente novamente."
    exit 1
fi

PYTHON_VER="$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")"
echo "Python encontrado: $PYTHON_CMD ($PYTHON_VER)"

# --- Dependencia de sistema: libusb ---
if command -v apt-get &>/dev/null; then
    echo "Verificando libusb (apt)..."
    dpkg -s libusb-1.0-0 &>/dev/null || {
        echo "Instalando libusb-1.0-0..."
        sudo apt-get update -qq && sudo apt-get install -y -qq libusb-1.0-0
    }
elif command -v pacman &>/dev/null; then
    echo "Verificando libusb (pacman)..."
    pacman -Qi libusb &>/dev/null || {
        echo "Instalando libusb..."
        sudo pacman -S --noconfirm libusb
    }
elif command -v dnf &>/dev/null; then
    echo "Verificando libusb (dnf)..."
    rpm -q libusb1 &>/dev/null || {
        echo "Instalando libusb..."
        sudo dnf install -y libusb1
    }
else
    echo "Gerenciador de pacotes não reconhecido."
    echo "Instale libusb manualmente antes de continuar."
fi

# --- Flag --reinstall ---
if [ "${1:-}" = "--reinstall" ] && [ -d "$VENV_DIR" ]; then
    echo ""
    echo "Recriando ambiente virtual (--reinstall)..."
    rm -rf "$VENV_DIR"
fi

# --- Ambiente virtual ---
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Criando ambiente virtual..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

echo ""
echo "Instalando dependências Python..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR"

# --- Verificação de import ---
"$VENV_DIR/bin/python" -c "import fusectl" || {
    echo "Falha ao importar fusectl apos instalação."
    exit 1
}
echo "Pacote fusectl instalado e verificado."

# --- Regra udev ---
echo ""
RULES_SRC="$SCRIPT_DIR/udev/50-switch-rcm.rules"
RULES_DST="/etc/udev/rules.d/50-switch-rcm.rules"
OLD_RULES="/etc/udev/rules.d/99-switch-rcm.rules"

[ -f "$OLD_RULES" ] && sudo rm -f "$OLD_RULES"

if [ ! -f "$RULES_DST" ] || ! diff -q "$RULES_SRC" "$RULES_DST" &>/dev/null; then
    echo "Instalando regra udev para acesso USB sem root..."
    sudo cp "$RULES_SRC" "$RULES_DST"
    sudo udevadm control --reload-rules
    sudo udevadm trigger --action=change --subsystem-match=usb
    echo "Regra udev instalada."
else
    echo "Regra udev ja instalada."
fi

# --- Grupo plugdev ---
if ! id -nG | grep -qw plugdev; then
    echo "Adicionando usuario ao grupo plugdev..."
    sudo usermod -aG plugdev "$(whoami)"
    echo "Grupo plugdev adicionado (faca logout/login ou use ./run.sh que aplica automáticamente)."
else
    echo "Grupo plugdev: OK"
fi

echo ""
echo "=== Instalação concluída ==="
echo ""
echo "Para executar:"
echo "  ./run.sh           # abre a interface TUI"
echo "  ./run.sh --help    # lista comandos disponíveis"
