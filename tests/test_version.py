from pathlib import Path

from fusectl.core.version import (
    detect_firmware_version,
    read_installed_version,
    read_package_version,
)


def test_read_package_version(cnx_package: Path) -> None:
    version = read_package_version(cnx_package)
    assert version == "21.2.0-0"


def test_read_package_version_missing(tmp_path: Path) -> None:
    version = read_package_version(tmp_path)
    assert version is None


def test_read_installed_version(sd_card: Path) -> None:
    version = read_installed_version(sd_card)
    assert version == "20.1.0-0"


def test_read_installed_version_no_tag(tmp_path: Path) -> None:
    bootloader = tmp_path / "bootloader"
    bootloader.mkdir()
    (bootloader / "hekate_ipl.ini").write_text("[config]\nautoboot=0\n")
    version = read_installed_version(tmp_path)
    assert version is None


def test_detect_firmware_version(tmp_path: Path) -> None:
    fw_dir = tmp_path / "firmware"
    fw_dir.mkdir()
    (fw_dir / "19.0.1").mkdir()
    version = detect_firmware_version(fw_dir)
    assert version == "19.0.1"


def test_detect_firmware_version_missing(tmp_path: Path) -> None:
    version = detect_firmware_version(tmp_path / "nope")
    assert version is None


def test_read_package_version_via_hekate_tag(tmp_path: Path) -> None:
    """Pacote sem arquivo de versão, mas com tag no hekate_ipl.ini."""
    pkg = tmp_path / "pack-generico"
    pkg.mkdir()
    (pkg / "atmosphere").mkdir()
    bootloader = pkg / "bootloader"
    bootloader.mkdir()
    (bootloader / "hekate_ipl.ini").write_text(
        "[config]\nautoboot=0\n\n{KEFIR 2.0.0}\n\n[ATMOSPHERE]\n{}\n"
    )
    version = read_package_version(pkg)
    assert version == "2.0.0"


def test_read_package_version_via_dir_name(tmp_path: Path) -> None:
    """Pacote sem arquivo de versão e sem tag, versão extraida do nome."""
    pkg = tmp_path / "AIO-19.0.1-3"
    pkg.mkdir()
    (pkg / "atmosphere").mkdir()
    version = read_package_version(pkg)
    assert version == "19.0.1-3"


def test_read_installed_version_tag_generico(tmp_path: Path) -> None:
    """Tag de versão no SD com formato diferente de CNX."""
    bootloader = tmp_path / "bootloader"
    bootloader.mkdir()
    (bootloader / "hekate_ipl.ini").write_text(
        "[config]\n\n{DEEPSEA 1.5.0}\n\n[ATMOSPHERE]\n{}\n"
    )
    version = read_installed_version(tmp_path)
    assert version == "1.5.0"
