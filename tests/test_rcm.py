import struct
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from fusectl.rcm.injector import (
    CHUNK_SIZE,
    MAX_PAYLOAD_LENGTH,
    RCM_CMD_LENGTH,
    RCM_PAYLOAD_ADDR,
    RCM_PAYLOAD_START,
    RCMError,
    STACK_SPRAY_END,
    STACK_SPRAY_START,
    USB_WRITE_EP,
    _build_payload,
    _switch_to_highbuf,
    inject,
)
from fusectl.rcm.intermezzo import INTERMEZZO


RCM_HEADER_SIZE = 680
PAYLOAD_BUF_OFFSET = (RCM_PAYLOAD_START - RCM_PAYLOAD_ADDR) + RCM_HEADER_SIZE
SPRAY_BUF_OFFSET = PAYLOAD_BUF_OFFSET + (STACK_SPRAY_START - RCM_PAYLOAD_START)
SPRAY_BUF_END = SPRAY_BUF_OFFSET + ((STACK_SPRAY_END - STACK_SPRAY_START) // 4) * 4


def test_build_payload_basic() -> None:
    data = b"\xAA" * 256
    payload = _build_payload(data)
    assert len(payload) % CHUNK_SIZE == 0
    assert len(payload) >= SPRAY_BUF_END

    header = struct.unpack("<I", payload[:4])[0]
    assert header == RCM_CMD_LENGTH

    assert payload[680 : 680 + len(INTERMEZZO)] == INTERMEZZO

    spray_addr = struct.pack("<I", RCM_PAYLOAD_ADDR)
    spray_region = payload[SPRAY_BUF_OFFSET:SPRAY_BUF_END]
    spray_count = (STACK_SPRAY_END - STACK_SPRAY_START) // 4
    assert spray_region == spray_addr * spray_count


def test_build_payload_too_large() -> None:
    data = b"\x00" * (MAX_PAYLOAD_LENGTH + 1)
    with pytest.raises(RCMError, match="tamanho máximo"):
        _build_payload(data)


def test_build_payload_intermezzo_offset() -> None:
    data = b"\xBB" * 128
    payload = _build_payload(data)
    assert payload[680 : 680 + len(INTERMEZZO)] == INTERMEZZO
    assert payload[680 + len(INTERMEZZO) : 680 + len(INTERMEZZO) + 4] == b"\x00" * 4


def test_build_payload_nop_sled() -> None:
    data = b"\xCC" * 64
    payload = _build_payload(data)
    nop_sled = payload[4:680]
    assert nop_sled == b"\x00" * 676


def test_build_payload_stack_spray_present() -> None:
    data = b"\xDD" * 512
    payload = _build_payload(data)

    spray_addr = struct.pack("<I", RCM_PAYLOAD_ADDR)
    spray_count = (STACK_SPRAY_END - STACK_SPRAY_START) // 4
    assert spray_count == 2160

    spray_region = payload[SPRAY_BUF_OFFSET:SPRAY_BUF_END]
    assert len(spray_region) == spray_count * 4

    for i in range(0, len(spray_region), 4):
        assert spray_region[i : i + 4] == spray_addr


def test_build_payload_small_payload() -> None:
    data = b"\xEE" * 128
    payload = _build_payload(data)

    user_region = payload[PAYLOAD_BUF_OFFSET : PAYLOAD_BUF_OFFSET + 128]
    assert user_region == data

    padding_region = payload[PAYLOAD_BUF_OFFSET + 128 : SPRAY_BUF_OFFSET]
    assert padding_region == b"\x00" * (SPRAY_BUF_OFFSET - PAYLOAD_BUF_OFFSET - 128)


def test_build_payload_large_payload() -> None:
    first_part_size = STACK_SPRAY_START - RCM_PAYLOAD_START
    data = b"\xFF" * (first_part_size + 256)
    payload = _build_payload(data)

    first_part = payload[PAYLOAD_BUF_OFFSET : PAYLOAD_BUF_OFFSET + first_part_size]
    assert first_part == data[:first_part_size]

    second_part = payload[SPRAY_BUF_END : SPRAY_BUF_END + 256]
    assert second_part == data[first_part_size:]


def test_build_payload_exact_max_length() -> None:
    data = b"\x00" * MAX_PAYLOAD_LENGTH
    payload = _build_payload(data)
    assert len(payload) % CHUNK_SIZE == 0
    assert len(payload) >= MAX_PAYLOAD_LENGTH


def test_switch_to_highbuf_already_high() -> None:
    device = MagicMock()
    result = _switch_to_highbuf(device, current_buffer=1)
    assert result == 1
    device.write.assert_not_called()


def test_switch_to_highbuf_from_low() -> None:
    device = MagicMock()
    result = _switch_to_highbuf(device, current_buffer=0)
    assert result == 1
    device.write.assert_called_once_with(
        USB_WRITE_EP, b"\x00" * CHUNK_SIZE, timeout=1000
    )


def test_inject_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        inject(tmp_path / "nope.bin")


@patch("fusectl.rcm.injector.find_rcm_device", return_value=None)
def test_inject_no_device(_mock: MagicMock, tmp_path: Path) -> None:
    payload = tmp_path / "test.bin"
    payload.write_bytes(b"\x00" * 128)
    with pytest.raises(RCMError, match="não detectado"):
        inject(payload)


@patch("fusectl.rcm.injector._trigger_vulnerability")
def test_inject_success(
    mock_trigger: MagicMock, tmp_path: Path, mock_usb_device: MagicMock
) -> None:
    payload = tmp_path / "test.bin"
    payload.write_bytes(b"\x00" * 256)

    inject(payload, device=mock_usb_device)

    mock_usb_device.read.assert_called_once()
    assert mock_usb_device.write.call_count > 0
    mock_trigger.assert_called_once()


@patch("fusectl.rcm.injector._trigger_vulnerability")
def test_inject_xhci_validation_runs(
    mock_trigger: MagicMock, tmp_path: Path, mock_usb_device: MagicMock
) -> None:
    payload = tmp_path / "test.bin"
    payload.write_bytes(b"\x00" * 256)

    inject(payload, device=mock_usb_device)

    args = mock_trigger.call_args
    assert args[0][0] is mock_usb_device
    assert isinstance(args[0][1], int)


@patch("fusectl.rcm.injector._trigger_vulnerability")
def test_inject_calls_switch_to_highbuf(
    mock_trigger: MagicMock, tmp_path: Path, mock_usb_device: MagicMock
) -> None:
    payload = tmp_path / "test.bin"
    payload.write_bytes(b"\x00" * 256)

    inject(payload, device=mock_usb_device)

    trigger_args = mock_trigger.call_args[0]
    assert trigger_args[1] == 1


def test_trigger_vulnerability_eperm_raises(mock_usb_device: MagicMock) -> None:
    """EPERM deve ser relançado como RCMError — não engolido silenciosamente."""
    import errno as errno_mod
    from fusectl.rcm.injector import _trigger_vulnerability

    err = OSError()
    err.errno = errno_mod.EPERM
    err.strerror = "Operation not permitted"

    with patch("fusectl.rcm.injector._validate_xhci"):
        with patch("fcntl.ioctl", side_effect=err):
            with patch("os.open", return_value=99):
                with patch("os.close"):
                    with pytest.raises(RCMError, match="Operation not permitted"):
                        _trigger_vulnerability(mock_usb_device, 1)


def test_trigger_vulnerability_enodev_ok(mock_usb_device: MagicMock) -> None:
    """ENODEV não deve lançar exceção — é o comportamento esperado após o smash."""
    import errno as errno_mod
    from fusectl.rcm.injector import _trigger_vulnerability

    err = OSError()
    err.errno = errno_mod.ENODEV
    err.strerror = "No such device"

    with patch("fusectl.rcm.injector._validate_xhci"):
        with patch("fcntl.ioctl", side_effect=err):
            with patch("os.open", return_value=99):
                with patch("os.close"):
                    _trigger_vulnerability(mock_usb_device, 1)
