import argparse
import sys
from pathlib import Path

from fusectl.core.logger import setup_logging


def cmd_rcm_inject(args: argparse.Namespace) -> int:
    from fusectl.rcm.injector import RCMError, inject

    payload = Path(args.payload)
    try:
        inject(payload)
    except FileNotFoundError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except RCMError as exc:
        sys.stderr.write(f"Erro RCM: {exc}\n")
        return 1
    return 0


def cmd_rcm_status(_args: argparse.Namespace) -> int:
    from fusectl.rcm.detector import find_rcm_device

    device = find_rcm_device()
    if device:
        sys.stdout.write(
            f"Switch detectado em modo RCM (bus {device.bus}, device {device.address})\n"
        )
        return 0
    sys.stdout.write("Nenhum Switch em modo RCM detectado\n")
    return 1


def cmd_version(args: argparse.Namespace) -> int:
    from fusectl.core.config import find_package_dir
    from fusectl.core.version import read_installed_version, read_package_version

    if args.package:
        pkg_dir = Path(args.package)
    else:
        pkg_dir = find_package_dir()

    if pkg_dir:
        pkg_ver = read_package_version(pkg_dir)
        sys.stdout.write(f"Pacote: {pkg_ver or 'desconhecido'} ({pkg_dir})\n")

    if args.sdcard:
        sd_ver = read_installed_version(Path(args.sdcard))
        sys.stdout.write(f"Instalado: {sd_ver or 'desconhecido'}\n")

    return 0


def cmd_install(args: argparse.Namespace) -> int:
    from fusectl.sdcard.installer import InstallError, install

    package_dir = Path(args.package)
    sd_root = Path(args.sdcard)

    def progress(current: int, total: int, filename: str) -> None:
        if total > 0:
            pct = current * 100 // total
            sys.stdout.write(f"\r[{pct:3d}%] {filename[:60]:<60}")
            if current == total:
                sys.stdout.write("\n")
            sys.stdout.flush()

    try:
        errors = install(package_dir, sd_root, progress_callback=progress)
    except InstallError as exc:
        sys.stderr.write(f"Erro: {exc}\n")
        return 1

    if errors:
        sys.stderr.write(f"\n{len(errors)} erro(s):\n")
        for e in errors:
            sys.stderr.write(f"  - {e}\n")
        return 1

    sys.stdout.write("Instalação concluída com sucesso\n")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    from fusectl.sdcard.updater import update

    package_dir = Path(args.package)
    sd_root = Path(args.sdcard)

    def progress(current: int, total: int, filename: str) -> None:
        if total > 0:
            pct = current * 100 // total
            sys.stdout.write(f"\r[{pct:3d}%] {filename[:60]:<60}")
            if current == total:
                sys.stdout.write("\n")
            sys.stdout.flush()

    errors = update(package_dir, sd_root, force=args.force, progress_callback=progress)

    if errors:
        sys.stderr.write(f"\n{len(errors)} erro(s):\n")
        for e in errors:
            sys.stderr.write(f"  - {e}\n")
        return 1

    sys.stdout.write("Atualização concluída com sucesso\n")
    return 0


def cmd_firmware(args: argparse.Namespace) -> int:
    from fusectl.firmware.manager import FirmwareError, install_firmware

    firmware_source = Path(args.firmware)
    sd_root = Path(args.sdcard)

    def progress(current: int, total: int, filename: str) -> None:
        if total > 0:
            pct = current * 100 // total
            sys.stdout.write(f"\r[{pct:3d}%] {filename[:60]:<60}")
            if current == total:
                sys.stdout.write("\n")
            sys.stdout.flush()

    try:
        errors = install_firmware(firmware_source, sd_root, progress_callback=progress)
    except FirmwareError as exc:
        sys.stderr.write(f"Erro: {exc}\n")
        return 1

    if errors:
        sys.stderr.write(f"\n{len(errors)} erro(s):\n")
        for e in errors:
            sys.stderr.write(f"  - {e}\n")
        return 1

    sys.stdout.write("Firmware copiado com sucesso\n")
    return 0


def cmd_sd_detect(_args: argparse.Namespace) -> int:
    from fusectl.sdcard.detector import find_switch_sd

    cards = find_switch_sd()
    if not cards:
        sys.stdout.write("Nenhum SD de Switch detectado\n")
        return 1

    for sd in cards:
        sys.stdout.write(f"  {sd}\n")
    return 0


def cmd_payloads(args: argparse.Namespace) -> int:
    from fusectl.core.config import find_package_dir, list_payloads

    if args.package:
        pkg_dir = Path(args.package)
    else:
        pkg_dir = find_package_dir()

    if not pkg_dir:
        sys.stderr.write("Pacote CFW não encontrado\n")
        return 1

    payloads = list_payloads(pkg_dir)
    if not payloads:
        sys.stdout.write("Nenhum payload encontrado\n")
        return 1

    for p in payloads:
        sys.stdout.write(f"  {p.name} ({p.relative_to(pkg_dir)})\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fusectl",
        description="Gerenciador Linux para Custom Firmware Nintendo Switch",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="saída detalhada")

    sub = parser.add_subparsers(dest="command")

    rcm = sub.add_parser("rcm", help="operações RCM")
    rcm.set_defaults(_rcm_parser=rcm)
    rcm_sub = rcm.add_subparsers(dest="rcm_command")

    inject = rcm_sub.add_parser("inject", help="injetar payload no Switch")
    inject.add_argument("payload", help="caminho para o arquivo .bin")

    rcm_sub.add_parser("status", help="verificar se Switch está em modo RCM")

    ver = sub.add_parser("version", help="exibir versões detectadas")
    ver.add_argument("-p", "--package", help="caminho para o pacote CFW")
    ver.add_argument("-s", "--sdcard", help="ponto de montagem do SD")

    pay = sub.add_parser("payloads", help="listar payloads disponíveis")
    pay.add_argument("-p", "--package", help="caminho para o pacote CFW")

    inst = sub.add_parser("install", help="instalar pacote CFW no SD")
    inst.add_argument("package", help="caminho para o pacote CFW")
    inst.add_argument("sdcard", help="ponto de montagem do SD")

    upd = sub.add_parser("update", help="atualizar CFW no SD")
    upd.add_argument("package", help="caminho para o pacote CFW")
    upd.add_argument("sdcard", help="ponto de montagem do SD")
    upd.add_argument("-f", "--force", action="store_true", help="forçar mesmo com versão igual")

    fw = sub.add_parser("firmware", help="copiar firmware para SD")
    fw.add_argument("firmware", help="diretório com arquivos NCA")
    fw.add_argument("sdcard", help="ponto de montagem do SD")

    sub.add_parser("sd-detect", help="detectar SD de Switch montado")

    return parser


def main() -> int:
    import logging

    parser = build_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level)

    handlers = {
        ("rcm", "inject"): cmd_rcm_inject,
        ("rcm", "status"): cmd_rcm_status,
        ("version", None): cmd_version,
        ("payloads", None): cmd_payloads,
        ("install", None): cmd_install,
        ("update", None): cmd_update,
        ("firmware", None): cmd_firmware,
        ("sd-detect", None): cmd_sd_detect,
    }

    if args.command == "rcm":
        key = ("rcm", args.rcm_command)
    elif args.command:
        key = (args.command, None)
    else:
        from fusectl.ui.app import FuseCtlApp
        app = FuseCtlApp()
        app.run()
        return 0

    handler = handlers.get(key)
    if handler is None:
        if args.command == "rcm" and args.rcm_command is None:
            args._rcm_parser.print_help()
        else:
            parser.print_help()
        return 0

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
