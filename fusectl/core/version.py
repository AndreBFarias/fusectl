import re
from pathlib import Path
from typing import Optional

from fusectl.core.config import HEKATE_INI, find_version_file
from fusectl.core.logger import get_logger

log = get_logger("version")

_VERSION_TAG_RE = re.compile(r"\{(\w+)\s+([\d]+\.[\d]+\.\d+(?:-[\d]+)?)\}")
_DIR_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:-\d+)?)")


def read_package_version(package_dir: Path) -> Optional[str]:
    """Le versão do pacote CFW usando fallback chain:
    1. Arquivo de versão conhecido (cnx.txt, version.txt, etc.)
    2. Tag de versão em hekate_ipl.ini
    3. Padrao de versão no nome do diretório
    """
    version_file = find_version_file(package_dir)
    if version_file:
        version = version_file.read_text(encoding="utf-8").strip()
        if version:
            log.info("Versão do pacote (via %s): %s", version_file.name, version)
            return version

    ini_path = package_dir / HEKATE_INI
    if ini_path.is_file():
        content = ini_path.read_text(encoding="utf-8", errors="replace")
        match = _VERSION_TAG_RE.search(content)
        if match:
            version = match.group(2).strip()
            log.info("Versão do pacote (via hekate_ipl.ini): %s", version)
            return version

    match = _DIR_VERSION_RE.search(package_dir.name)
    if match:
        version = match.group(1)
        log.info("Versão do pacote (via nome do diretório): %s", version)
        return version

    log.warning("Versão do pacote não detectada em %s", package_dir)
    return None


def read_installed_version(sd_root: Path) -> Optional[str]:
    """Le versão instalada no SD via tag de versão em hekate_ipl.ini."""
    ini_path = sd_root / HEKATE_INI
    if not ini_path.is_file():
        log.warning("Arquivo %s não encontrado", ini_path)
        return None

    content = ini_path.read_text(encoding="utf-8", errors="replace")
    match = _VERSION_TAG_RE.search(content)
    if not match:
        log.warning("Tag de versão não encontrada em %s", ini_path)
        return None

    version = match.group(2).strip()
    log.info("Versão instalada no SD: %s", version)
    return version


def detect_firmware_version(firmware_dir: Path) -> Optional[str]:
    """Detecta versão do firmware pelo nome da pasta (padrão XX.Y.Z)."""
    if not firmware_dir.is_dir():
        return None

    version_re = re.compile(r"^\d+\.\d+\.\d+$")
    for child in sorted(firmware_dir.iterdir()):
        if child.is_dir() and version_re.match(child.name):
            log.info("Firmware detectado: %s", child.name)
            return child.name

    return None
