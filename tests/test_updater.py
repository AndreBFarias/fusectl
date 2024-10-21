from pathlib import Path

from fusectl.sdcard.updater import update


def test_update_same_version_noop(cnx_package: Path, sd_card: Path) -> None:
    (sd_card / "bootloader" / "hekate_ipl.ini").write_text(
        "[config]\n\n{CNX 21.2.0-0}\n\n[ATMOSPHERE]\n{}\n"
    )
    errors = update(cnx_package, sd_card)
    assert errors == []


def test_update_different_version(cnx_package: Path, sd_card: Path) -> None:
    errors = update(cnx_package, sd_card)
    assert errors == []
    assert (sd_card / "bootloader" / "hekate_ipl.ini").is_file()


def test_update_removes_boot2_flags(cnx_package: Path, sd_card: Path) -> None:
    contents = sd_card / "atmosphere" / "contents" / "0100000000000042"
    contents.mkdir(parents=True, exist_ok=True)
    flag = contents / "boot2.flag"
    flag.write_text("")

    update(cnx_package, sd_card)
    assert not flag.exists()


def test_update_removes_old_hekate(cnx_package: Path, sd_card: Path) -> None:
    old_hekate = sd_card / "hekate_ctcaer_5.0.0.bin"
    old_hekate.write_bytes(b"\x00" * 32)

    update(cnx_package, sd_card)
    assert not old_hekate.exists()


def test_update_force(cnx_package: Path, sd_card: Path) -> None:
    (sd_card / "bootloader" / "hekate_ipl.ini").write_text(
        "[config]\n\n{CNX 21.2.0-0}\n\n[ATMOSPHERE]\n{}\n"
    )
    calls: list[tuple] = []
    errors = update(cnx_package, sd_card, force=True, progress_callback=lambda c, t, f: calls.append((c, t, f)))
    assert errors == []
    assert len(calls) > 0


def test_remove_old_hekate_removes_all(tmp_path: Path) -> None:
    """Todos os arquivos hekate_ctcaer_* devem ser removidos em uma passagem."""
    from fusectl.sdcard.updater import _remove_old_hekate

    sd = tmp_path / "sd"
    sd.mkdir()
    (sd / "hekate_ctcaer_5.9.0_ctcaer_0.6.5.bin").write_bytes(b"\x00")
    (sd / "hekate_ctcaer_6.0.1_ctcaer_0.7.0.bin").write_bytes(b"\x00")
    (sd / "hekate_ctcaer_6.1.0_ctcaer_0.8.0.bin").write_bytes(b"\x00")
    (sd / "atmosphere").mkdir()

    _remove_old_hekate(sd)

    remaining = list(sd.iterdir())
    assert len(remaining) == 1
    assert remaining[0].name == "atmosphere"


def test_update_clean_install_flag(cnx_package: Path, sd_card: Path) -> None:
    flag = sd_card / "cleaninstall.flag"
    flag.write_text("cnx-updater")

    contents = sd_card / "atmosphere" / "contents" / "0100000000000042"
    contents.mkdir(parents=True, exist_ok=True)
    boot2 = contents / "boot2.flag"
    boot2.write_text("")

    update(cnx_package, sd_card)

    assert boot2.exists()
    assert not flag.exists()
