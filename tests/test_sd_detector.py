from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from fusectl.sdcard.detector import (
    _find_fat_mounts,
    _is_switch_sd,
    _is_under_search_paths,
    find_switch_sd,
    get_sd_free_space,
)


class TestIsSwitchSd:

    def test_is_switch_sd_with_atmosphere(self, tmp_path: Path) -> None:
        (tmp_path / "atmosphere").mkdir()
        assert _is_switch_sd(tmp_path) is True

    def test_is_switch_sd_with_nintendo(self, tmp_path: Path) -> None:
        (tmp_path / "Nintendo").mkdir()
        assert _is_switch_sd(tmp_path) is True

    def test_is_switch_sd_without_markers(self, tmp_path: Path) -> None:
        (tmp_path / "qualquer_pasta").mkdir()
        assert _is_switch_sd(tmp_path) is False


class TestIsUnderSearchPaths:

    def test_under_media(self) -> None:
        assert _is_under_search_paths(Path("/media/usuario/sd")) is True

    def test_under_mnt(self) -> None:
        assert _is_under_search_paths(Path("/mnt/sd")) is True

    def test_under_run_media(self) -> None:
        assert _is_under_search_paths(Path("/run/media/usuario/sd")) is True

    def test_outside_search_paths(self) -> None:
        assert _is_under_search_paths(Path("/home/usuario/sd")) is False


class TestFindFatMounts:

    @patch("fusectl.sdcard.detector.Path")
    def test_parse_fat_entries(self, mock_path_cls: object) -> None:
        proc_mounts_content = (
            "/dev/sda1 /media/sd vfat rw 0 0\n"
            "/dev/sdb1 /mnt/backup ext4 rw 0 0\n"
            "/dev/sdc1 /media/exfat_sd exfat rw 0 0\n"
        )
        mock_proc = type(mock_path_cls).return_value = mock_path_cls("/proc/mounts")
        mock_path_cls.side_effect = lambda p: (
            SimpleNamespace(
                read_text=lambda encoding="utf-8", errors="replace": proc_mounts_content
            )
            if str(p) == "/proc/mounts"
            else Path(p)
        )

        resultado = _find_fat_mounts()
        caminhos = [str(m) for m in resultado]
        assert "/media/sd" in caminhos
        assert "/media/exfat_sd" in caminhos
        assert "/mnt/backup" not in caminhos


class TestGetSdFreeSpace:

    @patch("fusectl.sdcard.detector.os.statvfs")
    def test_get_sd_free_space(self, mock_statvfs: object) -> None:
        mock_statvfs.return_value = SimpleNamespace(f_bavail=1000, f_frsize=4096)
        resultado = get_sd_free_space(Path("/media/sd"))
        assert resultado == 1000 * 4096

    @patch("fusectl.sdcard.detector.os.statvfs", side_effect=OSError("disco removido"))
    def test_get_sd_free_space_error(self, mock_statvfs: object) -> None:
        resultado = get_sd_free_space(Path("/media/sd"))
        assert resultado == 0


class TestFindSwitchSd:

    @patch("fusectl.sdcard.detector._is_switch_sd")
    @patch("fusectl.sdcard.detector._is_under_search_paths")
    @patch("fusectl.sdcard.detector._find_fat_mounts")
    def test_find_switch_sd_with_mock_mounts(
        self,
        mock_fat_mounts: object,
        mock_under_paths: object,
        mock_is_switch: object,
    ) -> None:
        sd_path = Path("/media/usuario/sd")
        mock_fat_mounts.return_value = [sd_path]
        mock_under_paths.return_value = True
        mock_is_switch.return_value = True

        resultado = find_switch_sd()
        assert sd_path in resultado

    @patch("fusectl.sdcard.detector._is_switch_sd", return_value=False)
    @patch("fusectl.sdcard.detector._is_under_search_paths", return_value=False)
    @patch("fusectl.sdcard.detector._find_fat_mounts")
    @patch("fusectl.sdcard.detector._MOUNT_SEARCH_PATHS", new=())
    def test_find_switch_sd_sem_candidatos(
        self,
        mock_fat_mounts: object,
        mock_under_paths: object,
        mock_is_switch: object,
    ) -> None:
        mock_fat_mounts.return_value = []
        resultado = find_switch_sd()
        assert resultado == []
