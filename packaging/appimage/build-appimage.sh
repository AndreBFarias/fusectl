#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/../.."
BUILD_DIR="$PROJECT_ROOT/build"
APPDIR="$BUILD_DIR/AppDir"
SITE_PACKAGES="$APPDIR/usr/lib/python3.12/site-packages"

rm -rf "$APPDIR"
mkdir -p "$SITE_PACKAGES" "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/metainfo"

pip install --target="$SITE_PACKAGES" "$PROJECT_ROOT"

cp "$SCRIPT_DIR/AppRun" "$APPDIR/"
chmod +x "$APPDIR/AppRun"

sed 's/Exec=fusectl-launcher/Exec=fusectl/' \
    "$PROJECT_ROOT/packaging/fusectl.desktop" > "$APPDIR/usr/share/applications/fusectl.desktop"
cp "$APPDIR/usr/share/applications/fusectl.desktop" "$APPDIR/fusectl.desktop"

cp "$PROJECT_ROOT/assets/logo.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/fusectl.png"
cp "$PROJECT_ROOT/assets/logo.png" "$APPDIR/fusectl.png"

cp "$SCRIPT_DIR/fusectl.appdata.xml" "$APPDIR/usr/share/metainfo/"

APPIMAGETOOL="$BUILD_DIR/appimagetool"
if [ ! -f "$APPIMAGETOOL" ]; then
    curl -sSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

export ARCH=x86_64

if "$APPIMAGETOOL" --appimage-extract-and-run --no-appstream "$APPDIR" \
    "$BUILD_DIR/fusectl-x86_64.AppImage" 2>/dev/null; then
    :
else
    "$APPIMAGETOOL" --appimage-extract > /dev/null 2>&1
    "$BUILD_DIR/squashfs-root/AppRun" --no-appstream "$APPDIR" \
        "$BUILD_DIR/fusectl-x86_64.AppImage"
    rm -rf "$BUILD_DIR/squashfs-root"
fi

echo "AppImage gerado: $BUILD_DIR/fusectl-x86_64.AppImage"
