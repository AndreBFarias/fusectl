from pathlib import Path

from fusectl.sdcard.preserve import (
    execute_copy_files,
    load_copy_files,
    load_preserve_list,
    should_preserve,
)


def test_load_preserve_list_always_includes_tinfoil(cnx_package: Path) -> None:
    preserved = load_preserve_list(cnx_package)
    assert "switch/tinfoil/credentials.json" in preserved
    assert "switch/tinfoil/gdrive.token" in preserved


def test_load_preserve_list_from_file(cnx_package: Path) -> None:
    config_dir = cnx_package / "config" / "cnx-updater"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "preserve.txt").write_text("/my/custom/file.txt\n/another/file.cfg\n")

    preserved = load_preserve_list(cnx_package)
    assert "my/custom/file.txt" in preserved
    assert "another/file.cfg" in preserved


def test_should_preserve_existing_file(cnx_package: Path, sd_card: Path) -> None:
    cred = sd_card / "switch" / "tinfoil" / "credentials.json"
    cred.parent.mkdir(parents=True, exist_ok=True)
    cred.write_text("{}")

    preserved = load_preserve_list(cnx_package)
    assert should_preserve("switch/tinfoil/credentials.json", sd_card, preserved)


def test_should_not_preserve_nonexistent(cnx_package: Path, sd_card: Path) -> None:
    preserved = load_preserve_list(cnx_package)
    assert not should_preserve("switch/tinfoil/credentials.json", sd_card, preserved)


def test_load_copy_files(cnx_package: Path) -> None:
    config_dir = cnx_package / "config" / "cnx-updater"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "copy_files.txt").write_text(
        "/bootloader/update.bin|/bootloader/payloads/hekate.bin\n"
    )

    copies = load_copy_files(cnx_package)
    assert len(copies) == 1
    assert copies[0] == ("bootloader/update.bin", "bootloader/payloads/hekate.bin")


def test_execute_copy_files(cnx_package: Path, sd_card: Path) -> None:
    config_dir = cnx_package / "config" / "cnx-updater"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "copy_files.txt").write_text(
        "/bootloader/update.bin|/bootloader/payloads/hekate_copy.bin\n"
    )

    (sd_card / "bootloader" / "update.bin").write_bytes(b"\xFF" * 64)
    (sd_card / "bootloader" / "payloads").mkdir(parents=True, exist_ok=True)

    errors = execute_copy_files(sd_card, cnx_package)
    assert errors == []
    assert (sd_card / "bootloader" / "payloads" / "hekate_copy.bin").is_file()


def test_should_preserve_tinfoil_themes(cnx_package: Path, sd_card: Path) -> None:
    """Arquivos em switch/tinfoil/themes/ sao preservados."""
    theme = sd_card / "switch" / "tinfoil" / "themes" / "dark.json"
    theme.parent.mkdir(parents=True, exist_ok=True)
    theme.write_text('{"theme": "dark"}')

    preserved = load_preserve_list(cnx_package)
    assert should_preserve("switch/tinfoil/themes/dark.json", sd_card, preserved)
