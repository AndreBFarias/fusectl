from pathlib import Path

import pytest

from fusectl.firmware.manager import install_firmware
from fusectl.sdcard.installer import install
from fusectl.sdcard.updater import update


class TestInstallLargePackage:

    def test_install_large_package(self, cnx_package: Path, sd_card: Path) -> None:
        contents = cnx_package / "atmosphere" / "contents"

        for i in range(500):
            tid = f"{0x0100000000001000 + i:016X}"
            module_dir = contents / tid / "flags"
            module_dir.mkdir(parents=True, exist_ok=True)
            (module_dir / "boot2.flag").write_bytes(b"\x00")

        errors = install(cnx_package, sd_card)

        assert errors == []

        copied_count = sum(
            1 for _ in (sd_card / "atmosphere" / "contents").rglob("boot2.flag")
        )
        assert copied_count == 500


class TestUpdateManyBoot2Flags:

    def test_update_many_boot2_flags(self, cnx_package: Path, sd_card: Path) -> None:
        sd_contents = sd_card / "atmosphere" / "contents"

        for i in range(50):
            tid = f"{0x0100000000000001 + i:016X}"
            flag_dir = sd_contents / tid
            flag_dir.mkdir(parents=True, exist_ok=True)
            (flag_dir / "boot2.flag").write_bytes(b"\x00")

        pre_count = sum(1 for _ in sd_contents.rglob("boot2.flag"))
        assert pre_count == 50

        errors = update(cnx_package, sd_card, force=True)

        assert errors == []

        remaining = sum(1 for _ in sd_contents.rglob("boot2.flag"))
        assert remaining == 0


class TestUpdateManyOldHekate:

    def test_update_many_old_hekate(self, cnx_package: Path, sd_card: Path) -> None:
        for i in range(20):
            major = 5 + (i // 10)
            minor = i % 10
            name = f"hekate_ctcaer_{major}.{minor}.0.bin"
            (sd_card / name).write_bytes(b"\x00" * 64)

        pre_count = sum(
            1 for f in sd_card.iterdir()
            if f.name.startswith("hekate_ctcaer_")
        )
        assert pre_count == 20

        errors = update(cnx_package, sd_card, force=True)

        assert errors == []

        remaining = sum(
            1 for f in sd_card.iterdir()
            if f.name.startswith("hekate_ctcaer_")
        )
        assert remaining == 0


class TestInstallDeepNesting:

    def test_install_deep_nesting(self, cnx_package: Path, sd_card: Path) -> None:
        nested = cnx_package / "config"
        for level in range(10):
            nested = nested / f"level_{level}"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "deep_file.txt").write_text("deep content")

        errors = install(cnx_package, sd_card)

        assert errors == []

        expected = sd_card / "config"
        for level in range(10):
            expected = expected / f"level_{level}"
        assert (expected / "deep_file.txt").is_file()
        assert (expected / "deep_file.txt").read_text() == "deep content"


class TestFirmwareManyNcas:

    def test_firmware_many_ncas(self, tmp_path: Path) -> None:
        fw_source = tmp_path / "19.0.0"
        fw_source.mkdir()

        for i in range(200):
            nca_name = f"{i:032x}.nca"
            (fw_source / nca_name).write_bytes(b"\xff")

        sd_root = tmp_path / "sdcard"
        sd_root.mkdir()

        errors = install_firmware(fw_source, sd_root)

        assert errors == []

        fw_dest = sd_root / "firmware"
        installed = list(fw_dest.glob("*.nca"))
        assert len(installed) == 200


# "A simplicidade e a sofisticacao suprema." -- Leonardo da Vinci
