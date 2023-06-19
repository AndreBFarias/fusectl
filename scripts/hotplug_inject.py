"""Monitora conexão USB e injeta payload imediatamente ao detectar Switch em RCM."""

import sys
import time
from pathlib import Path

import usb.core

TEGRA_VID = 0x0955
TEGRA_PID = 0x7321


def wait_and_inject(payload_path: str) -> int:
    path = Path(payload_path)
    if not path.is_file():
        sys.stderr.write(f"Payload não encontrado: {path}\n")
        return 1

    stale = usb.core.find(idVendor=TEGRA_VID, idProduct=TEGRA_PID)
    stale_id = (stale.bus, stale.address) if stale else None
    if stale_id:
        sys.stdout.write(f"Ignorando device stale: bus {stale_id[0]}, device {stale_id[1]}\n")
        sys.stdout.write("Desconecte e reconecte o Switch em RCM...\n")
    else:
        sys.stdout.write("Aguardando Switch em RCM...\n")
    sys.stdout.flush()

    dev = None
    while dev is None:
        dev = usb.core.find(idVendor=TEGRA_VID, idProduct=TEGRA_PID)
        if dev is not None and (dev.bus, dev.address) == stale_id:
            dev = None
        if dev is None:
            time.sleep(0.2)

    sys.stdout.write(f"Detectado: bus {dev.bus}, device {dev.address}\n")
    sys.stdout.flush()

    from fusectl.rcm.injector import inject, RCMError

    try:
        inject(path, device=dev)
        sys.stdout.write("Injeção concluída.\n")
        return 0
    except RCMError as exc:
        sys.stderr.write(f"Erro RCM: {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"Erro: {type(exc).__name__}: {exc}\n")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Uso: python hotplug_inject.py <payload.bin>\n")
        sys.exit(1)
    sys.exit(wait_and_inject(sys.argv[1]))
