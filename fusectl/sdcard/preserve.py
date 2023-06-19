import shutil
from pathlib import Path

from fusectl.core.config import COPY_FILES_TXT, PRESERVE_ALWAYS
from fusectl.core.logger import get_logger

log = get_logger("sdcard.preserve")


def load_preserve_list(package_dir: Path) -> set[str]:
    """Carrega lista de paths a preservar do preserve.txt + hardcoded.

    Paths retornados sao relativos a raiz do SD, sem barra inicial.
    """
    preserved: set[str] = set()

    for p in PRESERVE_ALWAYS:
        preserved.add(p)

    preserve_file = _find_preserve_txt(package_dir)
    if preserve_file and preserve_file.is_file():
        for line in preserve_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            normalized = line.lstrip("/")
            if normalized:
                preserved.add(normalized)
                log.debug("Preservar: %s", normalized)

    log.info("Total de paths preservados: %d", len(preserved))
    return preserved


def _find_preserve_txt(package_dir: Path) -> Path | None:
    """Busca preserve.txt no pacote (config/cnx-updater/preserve.txt ou raiz)."""
    if (package_dir / "config").is_dir():
        for config_dir in (package_dir / "config").iterdir():
            if config_dir.is_dir() and config_dir.name.endswith("-updater"):
                candidate = config_dir / "preserve.txt"
                if candidate.is_file():
                    return candidate

    root_candidate = package_dir / "preserve.txt"
    if root_candidate.is_file():
        return root_candidate

    return None


def should_preserve(relative_path: str, sd_root: Path, preserve_list: set[str]) -> bool:
    """Verifica se um arquivo deve ser preservado durante instalação/atualização.

    Um arquivo e preservado se:
    - Esta na lista de preservacao E ja existe no SD
    - Pertence aos paths de tinfoil (sempre preservados) E ja existe no SD
    - E um arquivo dentro de switch/tinfoil/themes/ E ja existe no SD
    """
    normalized = relative_path.lstrip("/")

    if normalized.startswith("switch/tinfoil/themes/"):
        dest = sd_root / normalized
        if dest.exists():
            return True

    if normalized in preserve_list:
        dest = sd_root / normalized
        if dest.exists():
            log.debug("Preservado (ja existe): %s", normalized)
            return True

    return False


def load_copy_files(package_dir: Path) -> list[tuple[str, str]]:
    """Carrega lista de copias adicionais de copy_files.txt.

    Formato: /origem|/destino (paths relativos a raiz do SD).
    Retorna lista de tuplas (origem, destino) com paths normalizados.
    """
    copies: list[tuple[str, str]] = []

    copy_file = _find_copy_files_txt(package_dir)
    if not copy_file or not copy_file.is_file():
        return copies

    for line in copy_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|", maxsplit=1)
        if len(parts) != 2:
            continue
        src = parts[0].strip().lstrip("/")
        dst = parts[1].strip().lstrip("/")
        if src and dst:
            copies.append((src, dst))
            log.debug("Copy file: %s -> %s", src, dst)

    return copies


def _find_copy_files_txt(package_dir: Path) -> Path | None:
    """Busca copy_files.txt no pacote."""
    candidates = [
        package_dir / COPY_FILES_TXT,
    ]
    if (package_dir / "config").is_dir():
        for config_dir in (package_dir / "config").iterdir():
            if config_dir.is_dir() and config_dir.name.endswith("-updater"):
                candidate = config_dir / COPY_FILES_TXT
                if candidate.is_file():
                    return candidate

    for c in candidates:
        if c.is_file():
            return c

    return None


def execute_copy_files(sd_root: Path, package_dir: Path) -> list[str]:
    """Executa copias definidas em copy_files.txt.

    Origem e relativa ao SD (pos-instalação). Destino também.
    Retorna lista de erros (vazia se tudo ok).
    """
    copies = load_copy_files(package_dir)
    errors: list[str] = []

    for src_rel, dst_rel in copies:
        src = sd_root / src_rel
        dst = sd_root / dst_rel

        if not src.is_file():
            errors.append(f"Origem não encontrada: {src_rel}")
            log.warning("Copy file: origem não encontrada: %s", src)
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
            log.info("Copiado: %s -> %s", src_rel, dst_rel)
        except OSError as exc:
            errors.append(f"Falha ao copiar {src_rel} -> {dst_rel}: {exc}")
            log.error("Copy file falhou: %s -> %s: %s", src_rel, dst_rel, exc)

    return errors
