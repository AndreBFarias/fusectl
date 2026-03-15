from pathlib import Path

import pytest

from fusectl.core.config import find_package_dir, is_cfw_package, list_payloads


class TestFindPackageDir:

    def test_find_package_dir_root(self, cnx_package: Path) -> None:
        resultado = find_package_dir(search_root=cnx_package)
        assert resultado == cnx_package

    def test_find_package_dir_child(self, cnx_package: Path) -> None:
        diretório_pai = cnx_package.parent
        resultado = find_package_dir(search_root=diretório_pai)
        assert resultado == cnx_package

    def test_find_package_dir_not_found(self, tmp_path: Path) -> None:
        diretório_vazio = tmp_path / "vazio"
        diretório_vazio.mkdir()
        resultado = find_package_dir(search_root=diretório_vazio)
        assert resultado is None

    def test_find_package_sem_version_file(self, tmp_path: Path) -> None:
        """Pacote sem cnx.txt mas com atmosphere/ e detectado."""
        pkg = tmp_path / "meu-pack"
        pkg.mkdir()
        (pkg / "atmosphere").mkdir()
        (pkg / "bootloader").mkdir()
        resultado = find_package_dir(search_root=pkg)
        assert resultado == pkg

    def test_is_cfw_package_válido(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pack"
        pkg.mkdir()
        (pkg / "atmosphere").mkdir()
        assert is_cfw_package(pkg) is True

    def test_is_cfw_package_inválido(self, tmp_path: Path) -> None:
        pkg = tmp_path / "não-e-cfw"
        pkg.mkdir()
        assert is_cfw_package(pkg) is False


class TestListPayloads:

    def test_list_payloads_with_payloads(self, cnx_package: Path) -> None:
        resultado = list_payloads(cnx_package)

        assert len(resultado) == 3

        nomes = [p.name for p in resultado]
        assert nomes[0] == "payload.bin"
        assert "fusee.bin" in nomes
        assert "TegraExplorer.bin" in nomes

    def test_list_payloads_empty(self, tmp_path: Path) -> None:
        pacote_vazio = tmp_path / "pacote_sem_payloads"
        pacote_vazio.mkdir()
        resultado = list_payloads(pacote_vazio)
        assert resultado == []
