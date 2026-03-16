# SPRINT 2 — Melhorias de UX/UI na TUI

Versão de referência: v0.1.0
Prioridade: média — impacta percepção de qualidade e confiança do usuário

---

## Como usar este documento

Cada item contém:
- **Comportamento atual** — o que acontece hoje, com referência de linha
- **Comportamento esperado** — o que deve acontecer após a correção
- **Implementação completa** — código pronto para copiar
- **Passos sequenciais** — sem ambiguidade
- **Teste verificável** — critério mensurável

---

## UX 1: Progress bar não inicializa em 0%

### Arquivos e localização

- `fusectl/sdcard/installer.py`, linhas 76-78
- `fusectl/sdcard/updater.py`, linhas 59-61

### Comportamento atual

```python
# installer.py, linha 76
for idx, relative in enumerate(files_to_copy):
    if progress_callback:
        progress_callback(idx, total, str(relative))  # idx=0 → primeiro arquivo
    # cópia aqui
```

A primeira chamada do callback é `progress_callback(0, total, "atmosphere/package3")`
— já com o nome do primeiro arquivo. A TUI recebe isso e renderiza "0/total —
atmosphere/package3". Visualmente a barra está em 0% mas o nome de arquivo já aparece,
dando a impressão de que a operação começou antes de ser exibida.

O comportamento esperado é: barra aparece zerada **sem nome de arquivo** por um
frame antes de começar a processar.

### Código corrigido

**installer.py** — adicionar `progress_callback(0, total, "")` antes do loop:

```python
    log.info("Iniciando instalação: %d arquivos de %s para %s", total, package_dir, sd_root)

    if progress_callback:                           # ADICIONAR estas duas linhas
        progress_callback(0, total, "")             # ADICIONAR antes do for

    for idx, relative in enumerate(files_to_copy):
        if progress_callback:
            progress_callback(idx, total, str(relative))
```

**updater.py** — aplicar a mesma mudança antes do loop (linha 59):

```python
    log.info("Atualizando: %s -> %s", sd_version or "desconhecido", pkg_version or "desconhecido")

    is_clean = _check_clean_install(sd_root)

    if not is_clean:
        _remove_sysmodule_flags(sd_root)
        _remove_old_hekate(sd_root)

    preserve_list = load_preserve_list(package_dir)
    files_to_copy = _collect_files(package_dir)
    total = len(files_to_copy)
    errors: list[str] = []

    if progress_callback:                           # ADICIONAR estas duas linhas
        progress_callback(0, total, "")             # ADICIONAR antes do for

    for idx, relative in enumerate(files_to_copy):
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/sdcard/installer.py`. Localizar `log.info("Iniciando
instalação..."` (linha 74). Na linha 76, antes do `for idx, relative in...`, inserir:
```python
    if progress_callback:
        progress_callback(0, total, "")
```

**Passo 2:** Abrir `fusectl/sdcard/updater.py`. Localizar `errors: list[str] = []`
(linha 57). Após essa linha, antes do `for idx, relative in...` (linha 59), inserir:
```python
    if progress_callback:
        progress_callback(0, total, "")
```

### Teste de regressão

O teste existente `test_install_progress_callback` verifica que callbacks são chamados.
Estender para verificar a chamada inicial:

```python
def test_install_progress_starts_at_zero(cnx_package: Path, sd_card: Path) -> None:
    """Primeiro callback deve ser (0, total, '') antes de qualquer arquivo."""
    calls: list[tuple[int, int, str]] = []
    install(cnx_package, sd_card, progress_callback=lambda c, t, f: calls.append((c, t, f)))

    assert len(calls) >= 1
    first = calls[0]
    assert first[0] == 0
    assert first[2] == ""   # sem nome de arquivo no primeiro callback
```

### Critério de aceitação

Primeiro argumento do primeiro callback é sempre `(0, total, "")`. Os testes
existentes de progress_callback continuam passando.

---

## UX 2: NavBar com status visual real

### Arquivo e localização

`fusectl/ui/app.py`, linhas 309-310 (ver também Sprint 1 Bug 1)

### Comportamento atual

```python
def _update_global_status(self, rcm_connected: bool) -> None:
    pass   # nunca atualiza nada
```

A `NavBar` (widgets.py linha 84) tem `update_status(text: str)` que atualiza o
label `#nav-status`. Mas:
1. `NavBar` não está sendo adicionada ao `compose()` — ela existe como widget mas
   nunca é instanciada
2. `_update_global_status` não chama nada

### Código corrigido

Este item é idêntico ao **Sprint 1 Bug 1** — eles resolvem o mesmo problema.

Se Sprint 1 Bug 1 já foi implementado, este item está resolvido. Se ainda não foi,
seguir os passos do Sprint 1 Bug 1 completamente.

### Verificação

```python
# Após implementar Sprint 1 Bug 1, verificar manualmente:
# 1. Iniciar a TUI: .venv/bin/python -m fusectl
# 2. Conectar Switch em modo RCM via USB
# 3. Após 1,5 s, NavBar deve exibir "RCM: conectado  |  SD: <nome>"
# 4. Desconectar — deve voltar para "RCM: desconectado"
```

---

## UX 3: Validação de espaço em disco antes de operações

### Arquivos e localização

- `fusectl/sdcard/installer.py` — função `install()`, linha 48
- `fusectl/sdcard/updater.py` — função `update()`, linha 18
- `fusectl/sdcard/detector.py` — `get_sd_free_space()` já existe (linha 97)

### Comportamento atual

Nenhuma verificação de espaço. Se o SD estiver quase cheio:
1. `install()` começa a copiar arquivos
2. Depois de N arquivos, `shutil.copy2` lança `OSError: [Errno 28] No space left`
3. O erro é capturado e adicionado à lista `errors`, mas os arquivos parcialmente
   copiados ficam no SD
4. O SD fica em estado inconsistente (install incompleta)

### Implementação completa

**Passo 1:** Criar função auxiliar `_calculate_copy_size` em `installer.py`:

```python
def _calculate_copy_size(package_dir: Path, files: list[Path]) -> int:
    """Retorna o tamanho total em bytes dos arquivos a copiar."""
    total = 0
    for relative in files:
        src = package_dir / relative
        try:
            total += src.stat().st_size
        except OSError:
            pass
    return total
```

Adicionar essa função após `_collect_files` (linha 109), antes do fim do arquivo.

**Passo 2:** Adicionar import de `get_sd_free_space` em `installer.py`:

```python
# No topo do arquivo, junto com os outros imports de fusectl.sdcard:
from fusectl.sdcard.detector import get_sd_free_space
```

**Passo 3:** Adicionar verificação de espaço em `install()` após coletar arquivos:

```python
# Código atual (linha 70-72):
    preserve_list = load_preserve_list(package_dir)
    files_to_copy = _collect_files(package_dir)
    total = len(files_to_copy)
    errors: list[str] = []

# Substituir por:
    preserve_list = load_preserve_list(package_dir)
    files_to_copy = _collect_files(package_dir)
    total = len(files_to_copy)
    errors: list[str] = []

    required = _calculate_copy_size(package_dir, files_to_copy)
    available = get_sd_free_space(sd_root)
    if available > 0 and required > available:
        deficit_mb = (required - available) / (1024 * 1024)
        raise InstallError(
            f"Espaço insuficiente no SD: necessário {required // (1024*1024)} MB, "
            f"disponível {available // (1024*1024)} MB "
            f"(faltam {deficit_mb:.1f} MB)"
        )
```

**Passo 4:** Aplicar a mesma lógica em `updater.py`. Adicionar import no topo:

```python
from fusectl.sdcard.detector import get_sd_free_space
```

Adicionar verificação em `update()` após `files_to_copy = _collect_files(package_dir)`:

```python
    files_to_copy = _collect_files(package_dir)
    total = len(files_to_copy)
    errors: list[str] = []

    from fusectl.sdcard.installer import _calculate_copy_size, InstallError
    required = _calculate_copy_size(package_dir, files_to_copy)
    available = get_sd_free_space(sd_root)
    if available > 0 and required > available:
        deficit_mb = (required - available) / (1024 * 1024)
        raise InstallError(
            f"Espaço insuficiente no SD: necessário {required // (1024*1024)} MB, "
            f"disponível {available // (1024*1024)} MB "
            f"(faltam {deficit_mb:.1f} MB)"
        )
```

### Atenção: `available > 0` na condição

A condição `if available > 0 and required > available` garante que:
- Se `get_sd_free_space` retornar 0 por falha (OSError interno), não bloqueia
  a operação (fail open)
- Só bloqueia se conseguimos medir o espaço e ele for insuficiente

### Teste de regressão

```python
def test_install_raises_on_insufficient_space(cnx_package: Path, sd_card: Path) -> None:
    """InstallError deve ser lançado se SD não tiver espaço suficiente."""
    from unittest.mock import patch
    from fusectl.sdcard.installer import InstallError, install

    # simular SD com apenas 1 byte livre
    with patch("fusectl.sdcard.installer.get_sd_free_space", return_value=1):
        with pytest.raises(InstallError, match="Espaço insuficiente"):
            install(cnx_package, sd_card)


def test_install_proceeds_when_space_check_fails(cnx_package: Path, sd_card: Path) -> None:
    """Se get_sd_free_space retornar 0, instalação deve prosseguir (fail open)."""
    from unittest.mock import patch

    with patch("fusectl.sdcard.installer.get_sd_free_space", return_value=0):
        errors = install(cnx_package, sd_card)
        assert errors == []
```

### Critério de aceitação

Operação falha imediatamente com `InstallError` (mensagem com MBs) se o SD não
tiver espaço. Nenhum arquivo é modificado antes do erro. Se a medição falhar,
a operação prossegue normalmente.

---

## UX 4: Seleção de payload por path completo

### Arquivo e localização

`fusectl/ui/screens/rcm.py`, linhas 72-88

### Comportamento atual

```python
def update_payloads(self, payloads: list[Path]) -> None:
    if payloads == self._payloads:
        return
    option_list = self.query_one("#payload-list", OptionList)
    prev_idx = option_list.highlighted
    prev_name = self._payloads[prev_idx].name if prev_idx is not None and prev_idx < len(self._payloads) else None

    self._payloads = payloads
    option_list.clear_options()
    restore_idx = None
    for i, p in enumerate(payloads):
        option_list.add_option(Option(f"{p.name}", id=str(p)))
        if p.name == prev_name:          # compara só o filename
            restore_idx = i
```

### Cenário de falha

Estrutura de arquivos:
```
payloads/
  fusee.bin
  extras/
    fusee.bin   ← mesmo nome, path diferente
```

Usuário seleciona `payloads/fusee.bin`. Ao próximo polling, `update_payloads` é
chamado. `prev_name = "fusee.bin"`. O loop itera e encontra `extras/fusee.bin`
primeiro (dependendo da ordem de `list_payloads`). `p.name == "fusee.bin"` é True
para o arquivo errado. Seleção muda silenciosamente para o payload errado.

### Código corrigido

```python
def update_payloads(self, payloads: list[Path]) -> None:
    if payloads == self._payloads:
        return
    option_list = self.query_one("#payload-list", OptionList)
    prev_idx = option_list.highlighted
    prev_path = (
        self._payloads[prev_idx]
        if prev_idx is not None and 0 <= prev_idx < len(self._payloads)
        else None
    )

    self._payloads = payloads
    option_list.clear_options()
    restore_idx = None
    for i, p in enumerate(payloads):
        option_list.add_option(Option(f"{p.name}", id=str(p)))
        if p == prev_path:              # compara path completo
            restore_idx = i

    if restore_idx is not None:
        option_list.highlighted = restore_idx
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/ui/screens/rcm.py`. Localizar `update_payloads` (linha 72).

**Passo 2:** Substituir as linhas 72-88 pelo código corrigido acima.

**Nota:** A mudança de `prev_name` para `prev_path` também incorpora a correção do
Sprint 1 Bug 4 (verificação `0 <= prev_idx`). Se o Bug 4 já foi corrigido, a
condição já está lá — apenas mover de comparação por nome para comparação por path.

### Teste de regressão

```python
@pytest.mark.asyncio
async def test_update_payloads_preserves_selection_by_path(tmp_path: Path) -> None:
    """Seleção deve usar path completo, não nome, para restaurar posição."""
    from pathlib import Path
    from fusectl.ui.screens.rcm import RCMScreen

    dir_a = tmp_path / "payloads"
    dir_a.mkdir()
    dir_b = tmp_path / "extras"
    dir_b.mkdir()

    payload_a = dir_a / "fusee.bin"
    payload_b = dir_b / "fusee.bin"  # mesmo nome, path diferente
    payload_a.write_bytes(b"\x00")
    payload_b.write_bytes(b"\x00")

    from fusectl.ui.app import FuseCtlApp
    app = FuseCtlApp()
    async with app.run_test() as pilot:
        rcm_screen = app.query_one(RCMScreen)

        # primeiro load: ambos os payloads
        rcm_screen.update_payloads([payload_a, payload_b])
        option_list = rcm_screen.query_one("#payload-list")
        option_list.highlighted = 0  # selecionar payload_a

        # segundo load: mesma lista (simula polling)
        rcm_screen.update_payloads([payload_a, payload_b])

        # seleção deve continuar em 0 (payload_a), não mover para payload_b
        assert option_list.highlighted == 0
```

### Critério de aceitação

Seleção de payload persiste corretamente mesmo quando dois payloads têm o mesmo
nome de arquivo. A comparação é feita por `Path` completo.

---

## Resumo dos arquivos alterados

| Arquivo | Item | Tipo de mudança |
|---|---|---|
| `fusectl/sdcard/installer.py` | UX 1, UX 3 | Inserção de linhas + nova função |
| `fusectl/sdcard/updater.py` | UX 1, UX 3 | Inserção de linhas |
| `fusectl/ui/app.py` | UX 2 | Ver Sprint 1 Bug 1 |
| `fusectl/ui/screens/rcm.py` | UX 4 | Substituição de bloco |
| `fusectl/sdcard/detector.py` | UX 3 | Nenhuma alteração (usa função existente) |

## Ordem de implementação recomendada

1. UX 4 — mudança de lógica clara, sem novos imports
2. UX 1 — duas inserções de duas linhas
3. UX 2 — coberto pelo Sprint 1 Bug 1
4. UX 3 — maior mudança, requer nova função e imports

## Executar testes

```bash
cd /home/andrefarias/Desenvolvimento/fusectl
.venv/bin/python -m pytest tests/ -v
```

Todos os 120 testes existentes devem continuar passando.
