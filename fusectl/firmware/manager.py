import re
import shutil
from pathlib import Path
from typing import Callable

from fusectl.core.config import FIRMWARE_DIR
from fusectl.core.logger import get_logger

log = get_logger("firmware.manager")


class FirmwareError(Exception):
    pass


def install_firmware(
    firmware_source: Path,
    sd_root: Path,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[str]:
    """Copia arquivos NCA de firmware para /firmware/ no SD.

    Args:
        firmware_source: Diretório contendo os NCAs (ex: 21.2.0/).
        sd_root: Ponto de montagem do SD card.
        progress_callback: Callback(current, total, filename).

    Returns:
        Lista de erros (vazia se tudo ok).
    """
    if not firmware_source.is_dir():
        raise FirmwareError(f"Diretório de firmware não encontrado: {firmware_source}")

    nca_files = _collect_nca_files(firmware_source)
    if not nca_files:
        raise FirmwareError(f"Nenhum arquivo NCA encontrado em {firmware_source}")

    fw_dest = sd_root / FIRMWARE_DIR
    if fw_dest.exists():
        shutil.rmtree(fw_dest)
        log.info("Diretório firmware anterior removido")

    fw_dest.mkdir(parents=True, exist_ok=True)

    total = len(nca_files)
    errors: list[str] = []

    log.info("Copiando %d arquivos NCA para %s", total, fw_dest)

    for idx, nca in enumerate(nca_files):
        if progress_callback:
            progress_callback(idx, total, nca.name)

        dst = fw_dest / nca.name
        try:
            shutil.copy2(nca, dst)
        except OSError as exc:
            errors.append(f"Falha ao copiar {nca.name}: {exc}")
            log.error("Falha NCA: %s: %s", nca.name, exc)

    if progress_callback:
        progress_callback(total, total, "concluído")

    log.info("Firmware copiado: %d arquivos, %d erros", total, len(errors))
    return errors


def _collect_nca_files(source: Path) -> list[Path]:
    """Lista arquivos .nca e .cnmt.nca em um diretório."""
    files: list[Path] = []
    for entry in sorted(source.iterdir()):
        if entry.is_file() and (entry.suffix == ".nca"):
            files.append(entry)
    return files


def detect_firmware_source(search_root: Path) -> Path | None:
    """Detecta diretório de firmware pelo padrão de nome (XX.Y.Z) em um diretório."""
    version_re = re.compile(r"^\d+\.\d+\.\d+$")

    if not search_root.is_dir():
        return None

    for child in sorted(search_root.iterdir()):
        if child.is_dir() and version_re.match(child.name):
            nca_count = sum(1 for f in child.iterdir() if f.suffix == ".nca")
            if nca_count > 0:
                log.info("Firmware detectado: %s (%d NCAs)", child.name, nca_count)
                return child

    return None


def find_firmware_dir(
    search_root: Path | None = None,
    package_dir: Path | None = None,
) -> Path | None:
    """Busca diretório de firmware por detecção estrutural (XX.Y.Z com NCAs).

    Busca em múltiplos locais, similar a find_package_dir:
    - Dentro do pacote CFW (subdiretório com NCAs)
    - No diretório pai do pacote (irmão do pacote)
    - No cwd e subdiretórios comuns (firmware/, cfw/)
    """
    if search_root is None:
        search_root = Path.cwd()

    search_root = search_root.resolve()
    seen: set[Path] = set()
    candidates: list[Path] = []

    if package_dir:
        candidates.append(package_dir.resolve())
        candidates.append(package_dir.resolve().parent)

    candidates.append(search_root)

    fw_dir = search_root / "firmware"
    if fw_dir.is_dir():
        candidates.append(fw_dir)

    cfw_dir = search_root / "cfw"
    if cfw_dir.is_dir():
        candidates.append(cfw_dir)

    for candidate in candidates:
        if candidate in seen or not candidate.is_dir():
            continue
        seen.add(candidate)
        result = detect_firmware_source(candidate)
        if result:
            return result

    return None
