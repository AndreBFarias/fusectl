from typing import Optional

import usb.core

from fusectl.core.config import TEGRA_RCM_PID, TEGRA_RCM_VID
from fusectl.core.logger import get_logger

log = get_logger("rcm.detector")


def find_rcm_device() -> Optional[usb.core.Device]:
    """Detecta Nintendo Switch em modo RCM via USB (Tegra X1: 0955:7321)."""
    device = usb.core.find(idVendor=TEGRA_RCM_VID, idProduct=TEGRA_RCM_PID)
    if device is not None:
        log.info(
            "Switch detectado em modo RCM: bus %d, device %d",
            device.bus,
            device.address,
        )
    return device


def is_rcm_available() -> bool:
    """Retorna True se um Switch em modo RCM está conectado."""
    return find_rcm_device() is not None
