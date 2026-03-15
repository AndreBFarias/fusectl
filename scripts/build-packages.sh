#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

usage() {
    echo "Uso: $0 {deb|flatpak|appimage|all}"
    exit 1
}

build_deb() {
    echo "=== Build .deb ==="
    cd "$PROJECT_ROOT"

    if [ ! -L debian ] && [ ! -d debian ]; then
        ln -s packaging/debian debian
    fi

    dpkg-buildpackage -us -uc -b
    echo "Pacote .deb gerado em $(dirname "$PROJECT_ROOT")/"
}

build_flatpak() {
    echo "=== Build Flatpak ==="
    cd "$PROJECT_ROOT"

    flatpak-builder --force-clean build-dir \
        packaging/flatpak/com.github.fusectl.fusectl.yml
    echo "Build Flatpak concluído em build-dir/"
}

build_appimage() {
    echo "=== Build AppImage ==="
    bash "$PROJECT_ROOT/packaging/appimage/build-appimage.sh"
}

if [ $# -eq 0 ]; then
    usage
fi

case "$1" in
    deb)      build_deb ;;
    flatpak)  build_flatpak ;;
    appimage) build_appimage ;;
    all)
        build_deb
        build_flatpak
        build_appimage
        ;;
    *) usage ;;
esac
