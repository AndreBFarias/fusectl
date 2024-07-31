import shutil
from pathlib import Path
from unittest.mock import patch

from fusectl.sdcard.installer import InstallError, install

import pytest


def test_install_copies_files(cnx_package: Path, sd_card: Path) -> None:
    errors = install(cnx_package, sd_card)
    assert errors == []

    assert (sd_card / "payload.bin").is_file()
    assert (sd_card / "atmosphere").is_dir()
    assert (sd_card / "bootloader" / "hekate_ipl.ini").is_file()


def test_install_invalid_package(tmp_path: Path, sd_card: Path) -> None:
    with pytest.raises(InstallError, match="inválido"):
        install(tmp_path, sd_card)


def test_install_missing_sd(cnx_package: Path, tmp_path: Path) -> None:
    with pytest.raises(InstallError, match="não encontrado"):
        install(cnx_package, tmp_path / "nope")


def test_install_preserves_tinfoil(cnx_package: Path, sd_card: Path) -> None:
    cred = sd_card / "switch" / "tinfoil" / "credentials.json"
    cred.parent.mkdir(parents=True, exist_ok=True)
    cred.write_text('{"original": true}')

    (cnx_package / "switch" / "tinfoil").mkdir(parents=True, exist_ok=True)
    (cnx_package / "switch" / "tinfoil" / "credentials.json").write_text('{"new": true}')

    install(cnx_package, sd_card)

    content = cred.read_text()
    assert '"original"' in content


def test_install_progress_callback(cnx_package: Path, sd_card: Path) -> None:
    calls: list[tuple[int, int, str]] = []
    install(cnx_package, sd_card, progress_callback=lambda c, t, f: calls.append((c, t, f)))
    assert len(calls) > 0
    last = calls[-1]
    assert last[0] == last[1]


def test_install_readonly_files_renamed(cnx_package: Path, sd_card: Path) -> None:
    """Arquivos em _READONLY_FILES são renomeados para .apg."""
    (cnx_package / "atmosphere" / "package3").write_bytes(b"\xFF" * 64)

    errors = install(cnx_package, sd_card)
    assert errors == []
    assert (sd_card / "atmosphere" / "package3.apg").is_file()


def test_install_removes_stale_non_apg(cnx_package: Path, sd_card: Path) -> None:
    """Arquivo atmosphere/package3 sem .apg deve ser removido antes de criar .apg."""
    (cnx_package / "atmosphere" / "package3").write_bytes(b"\xFF" * 64)
    stale = sd_card / "atmosphere" / "package3"
    stale.write_bytes(b"\xAA" * 32)

    errors = install(cnx_package, sd_card)
    assert errors == []

    apg = sd_card / "atmosphere" / "package3.apg"
    assert apg.is_file()
    assert apg.read_bytes() == b"\xFF" * 64
    assert not stale.exists()


def test_install_copy_error(cnx_package: Path, sd_card: Path) -> None:
    """Erros de cópia são acumulados sem interromper."""
    call_count = 0
    original_copy2 = shutil.copy2

    def failing_copy(src, dst, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("disco cheio")
        return original_copy2(src, dst, **kwargs)

    with patch("fusectl.sdcard.installer.shutil.copy2", side_effect=failing_copy):
        errors = install(cnx_package, sd_card)

    assert len(errors) >= 1
    assert "disco cheio" in errors[0]
