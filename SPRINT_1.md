# SPRINT 1 — Bugs Críticos de Funcionalidade

Versão de referência: v0.1.0
Prioridade: alta — todos os itens afetam comportamento observável ou integridade de dados

---

## Como usar este documento

Cada bug contém:
- **Código atual** — trecho exato do arquivo, com número de linha
- **Por que é um bug** — explicação técnica do problema
- **Código corrigido** — implementação completa e pronta para substituição
- **Passos de implementação** — sequência numerada sem ambiguidade
- **Teste de regressão** — código de teste a adicionar em `tests/`

Nunca altere partes do arquivo que não estão descritas aqui.

---

## Bug 1: `_update_global_status()` não implementado

### Arquivo e localização

`fusectl/ui/app.py`, linhas 309-310

### Código atual (copiar exatamente para comparar)

```python
def _update_global_status(self, rcm_connected: bool) -> None:
    pass
```

### Por que é um bug

O método é chamado a cada 1,5 s por `_poll_status()` (linha 317). Ele recebe
`rcm_connected` e tem acesso a `self._sd_paths`. Mas o corpo é `pass` — o esqueleto
foi criado e nunca implementado. A `NavBar` (definida em `fusectl/ui/widgets.py`,
linha 84) tem o método `update_status(text: str)` que atualiza o label `#nav-status`,
mas essa widget não está sendo adicionada ao `compose()` do app — outro passo
necessário.

### Passos de implementação

**Passo 1:** Abrir `fusectl/ui/app.py`.

**Passo 2:** Localizar os imports no topo do arquivo (linhas 1-21). Adicionar `NavBar`
ao import de `fusectl.ui.widgets`:

```python
# linha atual:
from fusectl.ui.widgets import InfoPanel, Toolbar

# substituir por:
from fusectl.ui.widgets import InfoPanel, NavBar, Toolbar
```

**Passo 3:** Localizar o método `compose()` (linha 285). Adicionar `NavBar` como
primeiro widget filho:

```python
# código atual do compose():
def compose(self) -> ComposeResult:
    yield Toolbar(id="toolbar")
    with ContentSwitcher(id="content", initial="view-home"):
        with VerticalScroll(id="view-home"):
            yield HomeScreen()
        with VerticalScroll(id="view-ops"):
            yield RCMScreen()
            yield InstallScreen()
            yield UpdateScreen()
            yield FirmwareScreen()

# substituir por:
def compose(self) -> ComposeResult:
    yield NavBar(id="navbar")
    yield Toolbar(id="toolbar")
    with ContentSwitcher(id="content", initial="view-home"):
        with VerticalScroll(id="view-home"):
            yield HomeScreen()
        with VerticalScroll(id="view-ops"):
            yield RCMScreen()
            yield InstallScreen()
            yield UpdateScreen()
            yield FirmwareScreen()
```

**Passo 4:** Localizar `_update_global_status` (linha 309). Substituir `pass` pela
implementação:

```python
# código atual:
def _update_global_status(self, rcm_connected: bool) -> None:
    pass

# substituir por:
def _update_global_status(self, rcm_connected: bool) -> None:
    rcm_text = "conectado" if rcm_connected else "desconectado"
    if self._sd_paths:
        sd_text = self._sd_paths[0].name
    else:
        sd_text = "não detectado"
    try:
        self.query_one(NavBar).update_status(f"RCM: {rcm_text}  |  SD: {sd_text}")
    except Exception as exc:
        log.debug("Falha ao atualizar NavBar: %s", exc)
```

### O que NÃO alterar

- Não modificar o método `_poll_status()` nem seus chamadores.
- Não remover o `Toolbar` — ele continua presente.
- Não alterar o CSS existente.

### Teste de regressão

Adicionar em `tests/test_tui_e2e.py` ou criar `tests/test_app_status.py`:

```python
import pytest
from fusectl.ui.app import FuseCtlApp
from fusectl.ui.widgets import NavBar


@pytest.mark.asyncio
async def test_update_global_status_rcm_connected() -> None:
    app = FuseCtlApp()
    async with app.run_test() as pilot:
        app._sd_paths = []
        app._update_global_status(rcm_connected=True)
        navbar = app.query_one(NavBar)
        assert "conectado" in navbar._status_text


@pytest.mark.asyncio
async def test_update_global_status_sd_detected(tmp_path) -> None:
    (tmp_path / "sdcard").mkdir()
    app = FuseCtlApp()
    async with app.run_test() as pilot:
        app._sd_paths = [tmp_path / "sdcard"]
        app._update_global_status(rcm_connected=False)
        navbar = app.query_one(NavBar)
        assert "sdcard" in navbar._status_text
```

### Critério de aceitação

Após a mudança: NavBar exibe "RCM: conectado | SD: sdcard" (ou equivalente) após
cada ciclo de polling quando dispositivos estão presentes. Visível sem trocar de aba.

---

## Bug 2: `OSError` silenciosa em `_trigger_vulnerability()`

### Arquivo e localização

`fusectl/rcm/injector.py`, linhas 249-253

### Código atual

```python
    fd = os.open(dev_path, os.O_RDWR)
    try:
        fcntl.ioctl(fd, ioctl_number, request, True)
    except OSError:
        pass
    finally:
        os.close(fd)

    log.info("Vulnerabilidade acionada")
```

### Por que é um bug

O kernel retorna `ENODEV` após o smash bem-sucedido — o device desaparece do bus,
o que causa `OSError` com `errno.ENODEV`. Isso é **comportamento esperado** e o
`pass` foi colocado para isso. O problema: `EPERM` (sem permissão), `EACCES`
(regra udev não aplicada), `EIO` (hardware problem), `ENOENT` (device path sumiu
antes do ioctl) também caem no mesmo `except OSError: pass`. O usuário tenta
injetar, não acontece nada, TUI não mostra erro. O log mostra "Vulnerabilidade
acionada" mesmo quando falhou.

### Código corrigido

```python
import errno  # adicionar no topo do arquivo junto com os outros imports

    fd = os.open(dev_path, os.O_RDWR)
    try:
        fcntl.ioctl(fd, ioctl_number, request, True)
    except OSError as exc:
        if exc.errno == errno.ENODEV:
            log.debug("ENODEV após ioctl: smash bem-sucedido (esperado)")
        else:
            log.error("Falha no ioctl USBDEVFS_SUBMITURB: errno=%d (%s)", exc.errno, exc.strerror)
            raise RCMError(f"Falha ao acionar vulnerabilidade: {exc.strerror} (errno {exc.errno})") from exc
    finally:
        os.close(fd)

    log.info("Vulnerabilidade acionada")
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/rcm/injector.py`.

**Passo 2:** Verificar imports no topo (linhas 13-17). O módulo `errno` não está
importado. Adicionar na sequência alfabética existente:
```python
import ctypes
import errno    # adicionar aqui
import fcntl
import os
import struct
```

**Passo 3:** Localizar o `except OSError: pass` dentro de `_trigger_vulnerability()`
(linha 251). Substituir o bloco `try/except/finally` conforme o código corrigido acima.

**Passo 4:** Verificar que `log.info("Vulnerabilidade acionada")` na linha após o
bloco permanece — ele só é atingido se não houver exceção relançada.

### O que NÃO alterar

- Não modificar `_validate_xhci()`, a construção do `setup_packet`, a estrutura
  `_SubmitURB`, nem nada antes do `os.open`.
- Não alterar o comportamento em caso de `ENODEV` — continua sem exceção.

### Teste de regressão

Adicionar em `tests/test_rcm.py`:

```python
import errno
import os
from unittest.mock import MagicMock, patch
import pytest

from fusectl.rcm.injector import RCMError, _trigger_vulnerability


def test_trigger_vulnerability_eperm_raises(mock_usb_device) -> None:
    """EPERM deve ser relançado como RCMError."""
    mock_usb_device.bus = 1
    mock_usb_device.address = 10

    err = OSError()
    err.errno = errno.EPERM
    err.strerror = "Operation not permitted"

    with patch("fcntl.ioctl", side_effect=err):
        with patch("os.open", return_value=99):
            with patch("os.close"):
                with pytest.raises(RCMError, match="Operation not permitted"):
                    _trigger_vulnerability(mock_usb_device, 1)


def test_trigger_vulnerability_enodev_ok(mock_usb_device) -> None:
    """ENODEV não deve lançar exceção (comportamento esperado do smash)."""
    mock_usb_device.bus = 1
    mock_usb_device.address = 10

    err = OSError()
    err.errno = errno.ENODEV
    err.strerror = "No such device"

    with patch("fcntl.ioctl", side_effect=err):
        with patch("os.open", return_value=99):
            with patch("os.close"):
                _trigger_vulnerability(mock_usb_device, 1)  # não deve lançar
```

### Critério de aceitação

- Falha com `EPERM` ou `EACCES` resulta em `RCMError` visível na TUI com mensagem
  descritiva.
- `ENODEV` continua sem exceção (smash bem-sucedido).
- Log de `ERROR` aparece no arquivo de log para erros não-ENODEV.

---

## Bug 3: Iteração insegura sobre diretório durante remoção

### Arquivo e localização

`fusectl/sdcard/updater.py`, linha 114

### Código atual

```python
def _remove_old_hekate(sd_root: Path) -> None:
    """Remove binários hekate_ctcaer antigos da raiz do SD."""
    count = 0
    for entry in sd_root.iterdir():          # gerador — linha 114
        if entry.is_file() and entry.name.startswith("hekate_ctcaer_"):
            try:
                entry.unlink()
                count += 1
            except OSError as exc:
                log.warning("Falha ao remover %s: %s", entry, exc)

    if count:
        log.info("Removidos %d binários hekate antigos", count)
```

### Por que é um bug

`Path.iterdir()` retorna um gerador que internamente chama `readdir()` sob demanda,
lendo entradas do diretório uma a uma. Em sistemas FAT32/exFAT (que são exatamente
os SDs de Switch), o `readdir()` mantém um cursor na tabela de alocação. Ao deletar
um arquivo enquanto o cursor está ativo:
- Pode-se pular a entrada seguinte (se a deleção compacta a tabela)
- Pode-se retornar a mesma entrada duas vezes em kernels antigos
- O comportamento é indefinido pela especificação POSIX

O efeito prático: se houver dois arquivos `hekate_ctcaer_*.bin` no SD, apenas um
pode ser removido.

### Código corrigido

Mudança de uma linha — materializar o gerador em lista antes de iterar:

```python
def _remove_old_hekate(sd_root: Path) -> None:
    """Remove binários hekate_ctcaer antigos da raiz do SD."""
    count = 0
    for entry in list(sd_root.iterdir()):    # list() materializa antes de iterar
        if entry.is_file() and entry.name.startswith("hekate_ctcaer_"):
            try:
                entry.unlink()
                count += 1
            except OSError as exc:
                log.warning("Falha ao remover %s: %s", entry, exc)

    if count:
        log.info("Removidos %d binários hekate antigos", count)
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/sdcard/updater.py`.

**Passo 2:** Localizar `_remove_old_hekate` (linha 111). Alterar apenas a linha 114:
- De: `for entry in sd_root.iterdir():`
- Para: `for entry in list(sd_root.iterdir()):`

Nenhuma outra linha muda.

### Teste de regressão

Adicionar em `tests/test_updater.py`:

```python
def test_remove_old_hekate_removes_all(tmp_path: Path) -> None:
    """Todos os arquivos hekate_ctcaer_* devem ser removidos em uma passagem."""
    sd = tmp_path / "sd"
    sd.mkdir()

    # criar múltiplos arquivos hekate
    (sd / "hekate_ctcaer_5.9.0_ctcaer_0.6.5.bin").write_bytes(b"\x00")
    (sd / "hekate_ctcaer_6.0.1_ctcaer_0.7.0.bin").write_bytes(b"\x00")
    (sd / "hekate_ctcaer_6.1.0_ctcaer_0.8.0.bin").write_bytes(b"\x00")
    (sd / "atmosphere").mkdir()  # arquivo que NÃO deve ser removido

    from fusectl.sdcard.updater import _remove_old_hekate
    _remove_old_hekate(sd)

    remaining = list(sd.iterdir())
    assert len(remaining) == 1
    assert remaining[0].name == "atmosphere"
```

### Critério de aceitação

`_remove_old_hekate` remove **todos** os arquivos `hekate_ctcaer_*` presentes,
independente de quantos existam, sem afetar outros arquivos.

---

## Bug 4: Índice negativo não verificado em `update_payloads()`

### Arquivo e localização

`fusectl/ui/screens/rcm.py`, linha 77

### Código atual

```python
prev_idx = option_list.highlighted
prev_name = self._payloads[prev_idx].name if prev_idx is not None and prev_idx < len(self._payloads) else None
```

### Por que é um bug

A condição verifica `prev_idx is not None` e `prev_idx < len(self._payloads)`, mas
não `prev_idx >= 0`. A API `OptionList.highlighted` do Textual retorna `int | None`.
Em uso normal retorna não-negativo, mas a invariante não está documentada e pode
mudar entre versões. Se retornar `-1` (que em Python mapeia para o último elemento
da lista), o acesso `self._payloads[-1]` funcionaria aparentemente mas selecionaria
o item errado silenciosamente.

### Código corrigido

```python
prev_idx = option_list.highlighted
prev_name = (
    self._payloads[prev_idx].name
    if prev_idx is not None and 0 <= prev_idx < len(self._payloads)
    else None
)
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/ui/screens/rcm.py`.

**Passo 2:** Localizar `update_payloads` (linha 72). Localizar a linha 77 com a
expressão condicional. Substituir `prev_idx < len(self._payloads)` por
`0 <= prev_idx < len(self._payloads)`.

**Passo 3:** Formatar em múltiplas linhas conforme o código corrigido para manter
legibilidade (o pylint/flake8 pode reclamar de linha longa).

### O que NÃO alterar

- Não modificar o restante de `update_payloads` nem `get_selected_payload`.
- Não alterar a lógica de restore por nome de arquivo (`prev_name == p.name`).

### Critério de aceitação

Nenhuma `IndexError` ao atualizar lista de payloads. O teste unitário deve passar
com `highlighted` retornando `None`, `0`, valor válido e valor fora do range.

---

## Bug 5: Arquivo não-apg stale após instalação/atualização

### Arquivo e localização

`fusectl/sdcard/installer.py`, linhas 87-94 (e mesma lógica em `updater.py`, linhas 69-72)

### Código atual (installer.py)

```python
        relative_str = str(relative)
        if relative_str in _READONLY_FILES:
            dst = sd_root / (relative_str + ".apg")

        dst.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src, dst)
```

### Por que é um bug

`_READONLY_FILES` contém `atmosphere/package3` e `atmosphere/stratosphere.romfs`.
Para esses arquivos, o destino é redirecionado para `<arquivo>.apg`.

O problema: o installer não remove `sd_root / relative_str` se ele existir. Cenários
que causam o problema:
1. Instalação manual anterior copiou `atmosphere/package3` sem extensão
2. Outra ferramenta (Hekate USB Tools, fusee-nano) escreveu a versão não-apg
3. Usuário copiou o pacote manualmente

Com ambos `atmosphere/package3` e `atmosphere/package3.apg` presentes, o Atmosphere
em algumas versões prioriza o sem extensão, causando boot com firmware desatualizado.

### Código corrigido (installer.py — mesma correção em updater.py)

```python
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
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/sdcard/installer.py`. Localizar linhas 87-94. Substituir
pelo bloco corrigido acima.

**Passo 2:** Abrir `fusectl/sdcard/updater.py`. Localizar linhas 69-76 (mesma lógica,
mesmo padrão). Aplicar a mesma correção.

**Passo 3:** Verificar que `_READONLY_FILES` em `installer.py` (linha 15-18) ainda
contém:
```python
_READONLY_FILES = frozenset({
    "atmosphere/stratosphere.romfs",
    "atmosphere/package3",
})
```
Se diferente, ajustar o teste abaixo.

### Teste de regressão

Adicionar em `tests/test_installer.py`:

```python
def test_install_removes_stale_non_apg(cnx_package: Path, sd_card: Path) -> None:
    """Arquivo atmosphere/package3 sem .apg deve ser removido antes de criar .apg."""
    (cnx_package / "atmosphere" / "package3").write_bytes(b"\xFF" * 64)

    # simular instalação manual prévia — arquivo sem extensão já existe no SD
    stale = sd_card / "atmosphere" / "package3"
    stale.write_bytes(b"\xAA" * 32)

    errors = install(cnx_package, sd_card)
    assert errors == []

    # .apg deve existir com o conteúdo novo
    apg = sd_card / "atmosphere" / "package3.apg"
    assert apg.is_file()
    assert apg.read_bytes() == b"\xFF" * 64

    # versão sem extensão NÃO deve mais existir
    assert not stale.exists()
```

### Critério de aceitação

Após instalação ou atualização, nenhum arquivo listado em `_READONLY_FILES` existe
no SD sem a extensão `.apg`.

---

## Resumo dos arquivos alterados

| Arquivo | Bug | Linhas afetadas |
|---|---|---|
| `fusectl/ui/app.py` | Bug 1 | 9 (import), 285-295 (compose), 309-310 |
| `fusectl/rcm/injector.py` | Bug 2 | 14 (import errno), 249-253 |
| `fusectl/sdcard/updater.py` | Bug 3, Bug 5 | 114, 69-76 |
| `fusectl/ui/screens/rcm.py` | Bug 4 | 77 |
| `fusectl/sdcard/installer.py` | Bug 5 | 87-94 |

## Ordem de implementação recomendada

1. Bug 3 — mudança de uma linha, zero risco, fácil de verificar
2. Bug 4 — mudança de uma linha, zero risco
3. Bug 5 — dois arquivos, lógica simples, tem teste direto
4. Bug 2 — requer novo import, lógica de errno, testar manualmente
5. Bug 1 — maior mudança (compose + import + implementação), testar na TUI

## Executar testes após cada bug

```bash
cd /home/andrefarias/Desenvolvimento/fusectl
.venv/bin/python -m pytest tests/ -v
```

Todos os 120 testes existentes devem continuar passando após cada bug.
