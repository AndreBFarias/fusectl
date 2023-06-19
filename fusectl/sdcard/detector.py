import os
from pathlib import Path

from fusectl.core.config import SD_MARKERS
from fusectl.core.logger import get_logger

log = get_logger("sdcard.detector")

_MOUNT_SEARCH_PATHS = (
    Path("/media"),
    Path("/mnt"),
    Path("/run/media"),
)

_FAT_FILESYSTEMS = frozenset({"vfat", "exfat", "fuseblk"})


def _find_fat_mounts() -> list[Path]:
    """Lista pontos de montagem FAT32/exFAT via /proc/mounts."""
    mounts: list[Path] = []
    try:
        content = Path("/proc/mounts").read_text(encoding="utf-8", errors="replace")
    except OSError:
        log.warning("Falha ao ler /proc/mounts")
        return mounts

    for line in content.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mount_point = Path(parts[1])
        fs_type = parts[2]
        if fs_type in _FAT_FILESYSTEMS:
            mounts.append(mount_point)

    return mounts


def _is_under_search_paths(path: Path) -> bool:
    """Verifica se o path está dentro dos diretórios de busca conhecidos."""
    for search in _MOUNT_SEARCH_PATHS:
        try:
            path.relative_to(search)
            return True
        except ValueError:
            continue
    return False


def _is_switch_sd(mount_point: Path) -> bool:
    """Valida se o volume montado e um SD de Switch."""
    for marker in SD_MARKERS:
        if (mount_point / marker).is_dir():
            return True
    return False


def find_switch_sd() -> list[Path]:
    """Detecta microSD de Switch montados no sistema.

    Busca volumes FAT32/exFAT em /media/, /mnt/, /run/media/ que contenham
    atmosphere/ ou Nintendo/.
    """
    candidates = _find_fat_mounts()
    results: list[Path] = []

    for mount in candidates:
        if not _is_under_search_paths(mount):
            continue
        if _is_switch_sd(mount):
            log.info("SD de Switch detectado: %s", mount)
            results.append(mount)

    if not results:
        for search in _MOUNT_SEARCH_PATHS:
            if not search.is_dir():
                continue
            try:
                for child in search.iterdir():
                    if child.is_dir() and child not in candidates and _is_switch_sd(child):
                        log.info("SD de Switch detectado (sem FAT no /proc/mounts): %s", child)
                        results.append(child)
                    if child.is_dir():
                        try:
                            for subchild in child.iterdir():
                                if subchild.is_dir() and subchild not in candidates and _is_switch_sd(subchild):
                                    log.info("SD de Switch detectado: %s", subchild)
                                    results.append(subchild)
                        except PermissionError:
                            continue
            except PermissionError:
                continue

    return results


def get_sd_free_space(sd_root: Path) -> int:
    """Retorna espaço livre em bytes no ponto de montagem."""
    try:
        st = os.statvfs(sd_root)
        return st.f_bavail * st.f_frsize
    except OSError as exc:
        log.warning("Falha ao obter espaço livre de %s: %s", sd_root, exc)
        return 0
