import shutil
from pathlib import Path
from typing import Callable

from fusectl.core.config import CLEAN_INSTALL_FLAG, HEKATE_INI
from fusectl.core.logger import get_logger
from fusectl.core.version import read_installed_version, read_package_version
from fusectl.sdcard.installer import InstallError, _collect_files, _READONLY_FILES
from fusectl.sdcard.preserve import (
    execute_copy_files,
    load_preserve_list,
    should_preserve,
)

log = get_logger("sdcard.updater")


def update(
    package_dir: Path,
    sd_root: Path,
    force: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[str]:
    """Atualiza CFW no SD card.

    Compara versão instalada com versão do pacote.
    Remove arquivos obsoletos (boot2.flag, hekate_ctcaer antigos).
    Copia novos arquivos respeitando preserve.txt.

    Args:
        package_dir: Diretório do pacote CFW.
        sd_root: Ponto de montagem do SD card.
        force: Ignorar verificação de versão.
        progress_callback: Callback(current, total, filename).

    Returns:
        Lista de erros (vazia se tudo ok).
    """
    pkg_version = read_package_version(package_dir)
    sd_version = read_installed_version(sd_root)

    if not force and pkg_version and sd_version and pkg_version == sd_version:
        log.info("Versões idênticas (%s), nada a fazer", pkg_version)
        return []

    log.info("Atualizando: %s -> %s", sd_version or "desconhecido", pkg_version or "desconhecido")

    is_clean = _check_clean_install(sd_root)

    if not is_clean:
        _remove_sysmodule_flags(sd_root)
        _remove_old_hekate(sd_root)

    preserve_list = load_preserve_list(package_dir)
    files_to_copy = _collect_files(package_dir)
    total = len(files_to_copy)
    errors: list[str] = []

    for idx, relative in enumerate(files_to_copy):
        if progress_callback:
            progress_callback(idx, total, str(relative))

        if should_preserve(str(relative), sd_root, preserve_list):
            continue

        src = package_dir / relative
        dst = sd_root / relative

        relative_str = str(relative)
        if relative_str in _READONLY_FILES:
            dst = sd_root / (relative_str + ".apg")
            stale = sd_root / relative_str
            if stale.exists():
                try:
                    stale.unlink()
                    log.info("Removido arquivo stale: %s", stale)
                except OSError as exc:
                    log.warning("Falha ao remover arquivo stale %s: %s", stale, exc)

        dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src, dst)
        except OSError as exc:
            errors.append(f"Falha ao copiar {relative}: {exc}")
            log.error("Falha: %s: %s", relative, exc)

    copy_errors = execute_copy_files(sd_root, package_dir)
    errors.extend(copy_errors)

    _cleanup_clean_install_flag(sd_root)

    if progress_callback:
        progress_callback(total, total, "concluído")

    log.info("Atualização concluída: %d erros", len(errors))
    return errors


def _remove_sysmodule_flags(sd_root: Path) -> None:
    """Remove boot2.flag de todos os sysmodules em atmosphere/contents/."""
    contents = sd_root / "atmosphere" / "contents"
    if not contents.is_dir():
        return

    count = 0
    for flag in contents.rglob("boot2.flag"):
        try:
            flag.unlink()
            count += 1
        except OSError as exc:
            log.warning("Falha ao remover %s: %s", flag, exc)

    if count:
        log.info("Removidos %d arquivos boot2.flag", count)


def _remove_old_hekate(sd_root: Path) -> None:
    """Remove binários hekate_ctcaer antigos da raiz do SD."""
    count = 0
    for entry in list(sd_root.iterdir()):
        if entry.is_file() and entry.name.startswith("hekate_ctcaer_"):
            try:
                entry.unlink()
                count += 1
            except OSError as exc:
                log.warning("Falha ao remover %s: %s", entry, exc)

    if count:
        log.info("Removidos %d binários hekate antigos", count)


def _check_clean_install(sd_root: Path) -> bool:
    """Verifica se ha flag de clean install."""
    flag = sd_root / CLEAN_INSTALL_FLAG
    if flag.is_file():
        log.info("Flag de clean install detectada")
        return True
    return False


def _cleanup_clean_install_flag(sd_root: Path) -> None:
    """Remove flag de clean install após atualização."""
    flag = sd_root / CLEAN_INSTALL_FLAG
    if flag.is_file():
        try:
            flag.unlink()
            log.info("Flag de clean install removida")
        except OSError:
            pass
