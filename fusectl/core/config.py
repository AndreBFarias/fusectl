from pathlib import Path
from typing import Optional

from fusectl.core.logger import get_logger

log = get_logger("config")

KNOWN_VERSION_FILES = ("cnx.txt", "version.txt", "pack.txt")
STRUCTURE_MARKERS = ("atmosphere",)
SD_MARKERS = ("atmosphere", "Nintendo")
HEKATE_INI = Path("bootloader") / "hekate_ipl.ini"
PAYLOAD_DEFAULT = "payload.bin"
PAYLOADS_DIR = Path("bootloader") / "payloads"
FIRMWARE_DIR = Path("firmware")
COPY_FILES_TXT = "copy_files.txt"

PRESERVE_ALWAYS = frozenset({
    "switch/tinfoil/credentials.json",
    "switch/tinfoil/gdrive.token",
    "switch/tinfoil/locations.conf",
    "switch/tinfoil/options.json",
})

TEGRA_RCM_VID = 0x0955
TEGRA_RCM_PID = 0x7321

CLEAN_INSTALL_FLAG = "cleaninstall.flag"


def is_cfw_package(path: Path) -> bool:
    """Verifica se o diretório contém um pacote CFW válido (qualquer all-in-one pack)."""
    if not path.is_dir():
        return False
    return any((path / m).is_dir() for m in STRUCTURE_MARKERS)


def find_version_file(package_dir: Path) -> Optional[Path]:
    """Busca arquivo de versão conhecido no pacote."""
    for name in KNOWN_VERSION_FILES:
        path = package_dir / name
        if path.is_file():
            return path
    return None


def find_package_dir(search_root: Optional[Path] = None) -> Optional[Path]:
    """Busca diretório de pacote CFW por detecção estrutural (atmosphere/, bootloader/, etc.)."""
    if search_root is None:
        search_root = Path.cwd()

    search_root = search_root.resolve()

    if is_cfw_package(search_root):
        log.info("Pacote CFW encontrado em %s", search_root)
        return search_root

    for child in sorted(search_root.iterdir()):
        if child.is_dir() and is_cfw_package(child):
            log.info("Pacote CFW encontrado em %s", child)
            return child

    cfw_dir = search_root / "cfw"
    if cfw_dir.is_dir():
        if is_cfw_package(cfw_dir):
            log.info("Pacote CFW encontrado em %s", cfw_dir)
            return cfw_dir
        for child in sorted(cfw_dir.iterdir()):
            if child.is_dir() and is_cfw_package(child):
                log.info("Pacote CFW encontrado em %s", child)
                return child

    log.warning("Pacote CFW não encontrado a partir de %s", search_root)
    return None


def list_payloads(package_dir: Path) -> list[Path]:
    """Lista payloads disponíveis no pacote."""
    payloads: list[Path] = []

    root_payload = package_dir / PAYLOAD_DEFAULT
    if root_payload.is_file():
        payloads.append(root_payload)

    payloads_dir = package_dir / PAYLOADS_DIR
    if payloads_dir.is_dir():
        for p in sorted(payloads_dir.iterdir()):
            if p.suffix == ".bin" and p.is_file():
                payloads.append(p)

    return payloads
