from pathlib import Path
from unittest.mock import patch

import pytest

from fusectl.firmware.manager import (
    FirmwareError,
    _collect_nca_files,
    detect_firmware_source,
    install_firmware,
)


def _create_firmware_dir(base: Path, version: str = "21.2.0", nca_count: int = 3) -> Path:
    fw = base / version
    fw.mkdir(parents=True, exist_ok=True)
    for i in range(nca_count):
        (fw / f"00000000000000000000000000{i:06d}.nca").write_bytes(b"")
    return fw


def test_install_firmware_happy_path(tmp_path: Path) -> None:
    fw_source = _create_firmware_dir(tmp_path / "source")
    sd_root = tmp_path / "sdcard"
    sd_root.mkdir()

    errors = install_firmware(fw_source, sd_root)

    assert errors == []

    fw_dest = sd_root / "firmware"
    assert fw_dest.is_dir()

    copied = sorted(f.name for f in fw_dest.iterdir())
    original = sorted(f.name for f in fw_source.iterdir())
    assert copied == original


def test_install_firmware_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "inexistente"
    sd_root = tmp_path / "sdcard"
    sd_root.mkdir()

    with pytest.raises(FirmwareError, match="não encontrado"):
        install_firmware(missing, sd_root)


def test_install_firmware_no_ncas(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_fw"
    empty_dir.mkdir()
    (empty_dir / "readme.txt").write_text("não eh nca")

    sd_root = tmp_path / "sdcard"
    sd_root.mkdir()

    with pytest.raises(FirmwareError, match="Nenhum arquivo NCA"):
        install_firmware(empty_dir, sd_root)


def test_install_firmware_copy_error(tmp_path: Path) -> None:
    fw_source = _create_firmware_dir(tmp_path / "source", nca_count=2)
    sd_root = tmp_path / "sdcard"
    sd_root.mkdir()

    with patch("fusectl.firmware.manager.shutil.copy2", side_effect=OSError("disco cheio")):
        errors = install_firmware(fw_source, sd_root)

    assert len(errors) == 2
    assert all("disco cheio" in e for e in errors)


def test_detect_firmware_source(tmp_path: Path) -> None:
    (tmp_path / "random_dir").mkdir()
    (tmp_path / "not_version").mkdir()
    _create_firmware_dir(tmp_path, version="18.1.0", nca_count=5)

    result = detect_firmware_source(tmp_path)

    assert result is not None
    assert result.name == "18.1.0"


def test_detect_firmware_source_no_match(tmp_path: Path) -> None:
    (tmp_path / "no_version").mkdir()
    result = detect_firmware_source(tmp_path)
    assert result is None


def test_detect_firmware_source_missing_root(tmp_path: Path) -> None:
    result = detect_firmware_source(tmp_path / "inexistente")
    assert result is None


def test_collect_nca_files(tmp_path: Path) -> None:
    (tmp_path / "alpha.nca").write_bytes(b"")
    (tmp_path / "beta.nca").write_bytes(b"")
    (tmp_path / "gamma.txt").write_bytes(b"")
    (tmp_path / "delta.bin").write_bytes(b"")
    (tmp_path / "subdir").mkdir()

    result = _collect_nca_files(tmp_path)

    names = [f.name for f in result]
    assert "alpha.nca" in names
    assert "beta.nca" in names
    assert len(result) == 2
    assert all(f.suffix == ".nca" for f in result)


def test_install_firmware_removes_previous(tmp_path: Path) -> None:
    fw_source = _create_firmware_dir(tmp_path / "source", nca_count=1)
    sd_root = tmp_path / "sdcard"
    old_fw = sd_root / "firmware"
    old_fw.mkdir(parents=True)
    (old_fw / "old_file.nca").write_bytes(b"antigo")

    install_firmware(fw_source, sd_root)

    assert not (old_fw / "old_file.nca").exists()
    assert old_fw.is_dir()


def test_install_firmware_progress_callback(tmp_path: Path) -> None:
    fw_source = _create_firmware_dir(tmp_path / "source", nca_count=3)
    sd_root = tmp_path / "sdcard"
    sd_root.mkdir()

    calls: list[tuple[int, int, str]] = []
    install_firmware(fw_source, sd_root, progress_callback=lambda c, t, f: calls.append((c, t, f)))

    assert len(calls) == 4
    assert calls[-1] == (3, 3, "concluído")
    assert all(c[1] == 3 for c in calls)
