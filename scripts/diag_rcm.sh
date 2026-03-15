#!/usr/bin/env bash
# Diagnóstico completo do ambiente USB para injeção RCM.
# Rodar com o Switch conectado em modo RCM.
set -uo pipefail

echo "=== 1. Device USB ==="
lsusb -d 0955:7321 || echo "Device NAO encontrado"

echo -e "\n=== 2. Descritores USB ==="
lsusb -v -d 0955:7321 2>/dev/null | head -60

SYSFS=""
for entry in /sys/bus/usb/devices/*/idVendor; do
    if [ -f "$entry" ] && grep -q "0955" "$entry" 2>/dev/null; then
        dir=$(dirname "$entry")
        pid_file="$dir/idProduct"
        if [ -f "$pid_file" ] && grep -q "7321" "$pid_file" 2>/dev/null; then
            SYSFS="$dir"
            break
        fi
    fi
done

if [ -n "$SYSFS" ]; then
    echo -e "\n=== 3. Autosuspend ==="
    echo "sysfs_dir: $SYSFS"
    echo "autosuspend_delay_ms: $(cat "$SYSFS/power/autosuspend_delay_ms" 2>/dev/null)"
    echo "control: $(cat "$SYSFS/power/control" 2>/dev/null)"
    echo "runtime_status: $(cat "$SYSFS/power/runtime_status" 2>/dev/null)"

    echo -e "\n=== 4. Speed / Driver ==="
    echo "speed: $(cat "$SYSFS/speed" 2>/dev/null) Mbps"
    echo "configuration: $(cat "$SYSFS/bConfigurationValue" 2>/dev/null)"
    echo "driver: $(readlink "$SYSFS/driver" 2>/dev/null || echo 'nenhum')"

    BUS=$(cat "$SYSFS/busnum" 2>/dev/null)
    DEV=$(cat "$SYSFS/devnum" 2>/dev/null)

    if [ -n "$BUS" ] && [ -n "$DEV" ]; then
        DEV_NODE="/dev/bus/usb/$(printf '%03d' "$BUS")/$(printf '%03d' "$DEV")"

        echo -e "\n=== 5. Processos no device ==="
        sudo fuser -v "$DEV_NODE" 2>&1 || echo "Nenhum processo"
        sudo lsof "$DEV_NODE" 2>/dev/null || echo "Nenhum processo"

        echo -e "\n=== 6. Permissoes ==="
        ls -la "$DEV_NODE"
        getfacl "$DEV_NODE" 2>/dev/null
    fi
else
    echo -e "\n=== 3-6. SKIPPED (device não encontrado no sysfs) ==="
fi

echo -e "\n=== 7. Kernel logs USB (ultimos 30) ==="
dmesg | grep -iE "usb|tegra|0955|rcm|xhci" | tail -30

echo -e "\n=== 8. ModemManager ==="
systemctl is-active ModemManager 2>/dev/null || echo "inativo"

echo -e "\n=== 9. Regra udev instalada ==="
cat /etc/udev/rules.d/50-switch-rcm.rules 2>/dev/null || echo "NAO ENCONTRADA"

# "A simplicidade e a sofisticação definitiva." - Leonardo da Vinci
