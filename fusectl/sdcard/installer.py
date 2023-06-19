import shutil
from pathlib import Path
from typing import Callable

from fusectl.core.config import KNOWN_VERSION_FILES, is_cfw_package
from fusectl.core.logger import get_logger
from fusectl.sdcard.preserve import (
    execute_copy_files,
    load_preserve_list,
    should_preserve,
)

log = get_logger("sdcard.installer")

_READONLY_FILES = frozenset({
    "atmosphere/stratosphere.romfs",
    "atmosphere/package3",
})

_SKIP_FILES = frozenset(KNOWN_VERSION_FILES) | frozenset({
    "AVISO_LEGAL.txt",
})

_PACKAGE_DIRS = frozenset({
    "atmosphere",
    "bootloader",
    "config",
    "switch",
    "emuiibo",
    "pegascape",
    "tegraexplorer",
    "warmboot_mariko",
})

_PACKAGE_ROOT_FILES = frozenset({
    "boot.dat",
    "boot.ini",
    "exosphere.ini",
    "hbmenu.nro",
    "payload.bin",
})


class InstallError(Exception):
    pass


def install(
    package_dir: Path,
    sd_root: Path,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[str]:
    """Instala pacote CFW no SD card.

    Args:
        package_dir: Diretório do pacote CFW (contém atmosphere/, bootloader/, etc.).
        sd_root: Ponto de montagem do SD card.
        progress_callback: Callback(current, total, filename) para progresso.

    Returns:
        Lista de erros (vazia se tudo ok).
    """
    if not is_cfw_package(package_dir):
        raise InstallError(f"Pacote CFW inválido: {package_dir}")

    if not sd_root.is_dir():
        raise InstallError(f"SD card não encontrado: {sd_root}")

    preserve_list = load_preserve_list(package_dir)
    files_to_copy = _collect_files(package_dir)
    total = len(files_to_copy)
    errors: list[str] = []

    log.info("Iniciando instalação: %d arquivos de %s para %s", total, package_dir, sd_root)

    for idx, relative in enumerate(files_to_copy):
        if progress_callback:
            progress_callback(idx, total, str(relative))

        if should_preserve(str(relative), sd_root, preserve_list):
            log.debug("Preservado: %s", relative)
            continue

        src = package_dir / relative
        dst = sd_root / relative

        relative_str = str(relative)
        if relative_str in _READONLY_FILES:
            dst = sd_root / (relative_str + ".apg")

        dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src, dst)
        except OSError as exc:
            errors.append(f"Falha ao copiar {relative}: {exc}")
            log.error("Falha ao copiar %s: %s", relative, exc)

    copy_errors = execute_copy_files(sd_root, package_dir)
    errors.extend(copy_errors)

    if progress_callback:
        progress_callback(total, total, "concluído")

    log.info("Instalação concluída: %d erros", len(errors))
    return errors


def _collect_files(package_dir: Path) -> list[Path]:
    """Lista todos os arquivos do pacote que devem ser copiados."""
    files: list[Path] = []

    for name in _PACKAGE_ROOT_FILES:
        path = package_dir / name
        if path.is_file():
            files.append(Path(name))

    for dir_name in _PACKAGE_DIRS:
        dir_path = package_dir / dir_name
        if not dir_path.is_dir():
            continue
        for file_path in sorted(dir_path.rglob("*")):
            if file_path.is_file():
                relative = file_path.relative_to(package_dir)
                if str(relative) not in _SKIP_FILES:
                    files.append(relative)

    return files
