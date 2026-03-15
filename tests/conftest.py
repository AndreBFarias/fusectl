from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def cnx_package(tmp_path: Path) -> Path:
    """Cria estrutura minima de pacote CFW para testes."""
    pkg = tmp_path / "CFW.21.2.0-0"
    pkg.mkdir()

    (pkg / "cnx.txt").write_text("21.2.0-0\n")

    bootloader = pkg / "bootloader"
    bootloader.mkdir()
    (bootloader / "hekate_ipl.ini").write_text(
        "[config]\nautoboot=0\n\n{CNX 21.2.0-0}\n\n[ATMOSPHERE]\npkg3=atmosphere/package3\n{}\n"
    )

    payloads = bootloader / "payloads"
    payloads.mkdir()
    (payloads / "fusee.bin").write_bytes(b"\x00" * 256)
    (payloads / "TegraExplorer.bin").write_bytes(b"\x00" * 128)

    (pkg / "payload.bin").write_bytes(b"\x00" * 512)

    (pkg / "atmosphere").mkdir()
    (pkg / "atmosphere" / "contents").mkdir()

    (pkg / "config").mkdir()
    (pkg / "switch").mkdir()

    return pkg


@pytest.fixture
def sd_card(tmp_path: Path) -> Path:
    """Cria estrutura minima de SD card de Switch."""
    sd = tmp_path / "sdcard"
    sd.mkdir()

    (sd / "atmosphere").mkdir()
    (sd / "Nintendo").mkdir()

    bootloader = sd / "bootloader"
    bootloader.mkdir()
    (bootloader / "hekate_ipl.ini").write_text(
        "[config]\nautoboot=0\n\n{CNX 20.1.0-0}\n\n[ATMOSPHERE]\n{}\n"
    )

    return sd


@pytest.fixture
def mock_usb_device() -> MagicMock:
    """Mock de dispositivo USB Tegra RCM."""
    device = MagicMock()
    device.bus = 1
    device.address = 42
    device.idVendor = 0x0955
    device.idProduct = 0x7321
    device.read.return_value = MagicMock(tobytes=lambda: b"\xAA" * 16)
    device.write.return_value = None
    device.ctrl_transfer.return_value = None
    device.set_configuration.return_value = None
    return device
