# SPRINT 3 — Qualidade de Código e Otimizações

Versão de referência: v0.1.0
Prioridade: baixa-média — não afeta funcionalidade imediata, mas impacta
manutenibilidade, performance e segurança a longo prazo

---

## Como usar este documento

Cada item contém código atual exato, código corrigido completo e passos
numerados sem ambiguidade. Aplicar cada item de forma independente — eles
não dependem um do outro.

---

## Qualidade 1: Duplicação entre `_find_preserve_txt()` e `_find_copy_files_txt()`

### Arquivo e localização

`fusectl/sdcard/preserve.py`, linhas 35-48 (função 1) e 103-119 (função 2)

### Código atual

```python
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
```

### Por que é duplicação

Ambas buscam um arquivo pelo mesmo algoritmo:
1. Tentar `config/<algo>-updater/<arquivo>` primeiro
2. Fallback para `<raiz>/<arquivo>`

A única diferença é o nome do arquivo (`"preserve.txt"` vs. `COPY_FILES_TXT`).

### Código corrigido

Extrair função genérica e substituir as duas:

```python
def _find_config_file(package_dir: Path, filename: str) -> Path | None:
    """Busca arquivo de configuração no pacote (config/*-updater/<filename> ou raiz).

    Retorna o primeiro match encontrado, ou None se não existir.
    """
    if (package_dir / "config").is_dir():
        for config_dir in (package_dir / "config").iterdir():
            if config_dir.is_dir() and config_dir.name.endswith("-updater"):
                candidate = config_dir / filename
                if candidate.is_file():
                    return candidate

    root_candidate = package_dir / filename
    if root_candidate.is_file():
        return root_candidate

    return None


def _find_preserve_txt(package_dir: Path) -> Path | None:
    """Busca preserve.txt no pacote."""
    return _find_config_file(package_dir, "preserve.txt")


def _find_copy_files_txt(package_dir: Path) -> Path | None:
    """Busca copy_files.txt no pacote."""
    return _find_config_file(package_dir, COPY_FILES_TXT)
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/sdcard/preserve.py`.

**Passo 2:** Localizar `_find_preserve_txt` (linha 35). Deletar as linhas 35-48
inteiras.

**Passo 3:** Localizar `_find_copy_files_txt` (linha 103, após a deleção será
renumerada). Deletar a função inteira (linhas 103-119 originais).

**Passo 4:** No lugar das duas funções deletadas, inserir as três funções do
código corrigido acima (`_find_config_file`, `_find_preserve_txt`,
`_find_copy_files_txt`).

**Passo 5:** Não alterar nada mais no arquivo — `load_preserve_list`,
`load_copy_files`, `should_preserve`, `execute_copy_files` permanecem intactos.

**Passo 6:** Executar testes:
```bash
.venv/bin/python -m pytest tests/test_preserve.py -v
```
Todos devem passar sem alteração.

### O que NÃO alterar

- Não modificar as funções públicas `load_preserve_list`, `load_copy_files`,
  `should_preserve`, `execute_copy_files`.
- Não alterar os imports no topo do arquivo.
- Não alterar a constante `COPY_FILES_TXT` (vem de `fusectl.core.config`).

### Critério de aceitação

- `_find_preserve_txt` e `_find_copy_files_txt` têm corpo de uma linha cada.
- `_find_config_file` encapsula a lógica de busca.
- Todos os testes existentes de `preserve.py` passam sem modificação.

---

## Qualidade 2: Regex compilada dentro de função

### Arquivo e localização

`fusectl/core/version.py`, linha 69

### Código atual

```python
def detect_firmware_version(firmware_dir: Path) -> Optional[str]:
    """Detecta versão do firmware pelo nome da pasta (padrão XX.Y.Z)."""
    if not firmware_dir.is_dir():
        return None

    version_re = re.compile(r"^\d+\.\d+\.\d+$")   # PROBLEMA: recompilada a cada chamada
    for child in sorted(firmware_dir.iterdir()):
        if child.is_dir() and version_re.match(child.name):
            log.info("Firmware detectado: %s", child.name)
            return child.name

    return None
```

### Contexto

O módulo já usa constantes de módulo para outras regexes (linhas 10-11):
```python
_VERSION_TAG_RE = re.compile(r"\{(\w+)\s+([\d]+\.[\d]+\.\d+(?:-[\d]+)?)\}")
_DIR_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:-\d+)?)")
```

Apenas `version_re` dentro de `detect_firmware_version` está fora do padrão.

O mesmo problema existe em `fusectl/firmware/manager.py`, linha 79:
```python
def detect_firmware_source(search_root: Path) -> Path | None:
    version_re = re.compile(r"^\d+\.\d+\.\d+$")   # também recompilada a cada chamada
```

### Código corrigido

**Passo 1:** Adicionar constante no topo do arquivo, após as linhas 10-11 existentes:

```python
_VERSION_TAG_RE = re.compile(r"\{(\w+)\s+([\d]+\.[\d]+\.\d+(?:-[\d]+)?)\}")
_DIR_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:-\d+)?)")
_FIRMWARE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")   # ADICIONAR esta linha
```

**Passo 2:** Em `detect_firmware_version` (linha 69), remover a linha
`version_re = re.compile(r"^\d+\.\d+\.\d+$")` e substituir `version_re` pelo
nome da constante:

```python
def detect_firmware_version(firmware_dir: Path) -> Optional[str]:
    """Detecta versão do firmware pelo nome da pasta (padrão XX.Y.Z)."""
    if not firmware_dir.is_dir():
        return None

    for child in sorted(firmware_dir.iterdir()):
        if child.is_dir() and _FIRMWARE_VERSION_RE.match(child.name):
            log.info("Firmware detectado: %s", child.name)
            return child.name

    return None
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/core/version.py`.

**Passo 2:** Linha 11 — após `_DIR_VERSION_RE = re.compile(...)`, inserir nova linha:
```python
_FIRMWARE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
```

**Passo 3:** Linha 69 — deletar a linha `version_re = re.compile(r"^\d+\.\d+\.\d+$")`.

**Passo 4:** Linha 70 (agora 69) — substituir `version_re.match` por
`_FIRMWARE_VERSION_RE.match`.

**Passo 5:** Abrir `fusectl/firmware/manager.py`. Após os imports (linha 9), adicionar
constante de módulo:
```python
_FIRMWARE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
```

**Passo 6:** Em `detect_firmware_source` (linha 79), deletar
`version_re = re.compile(r"^\d+\.\d+\.\d+$")` e substituir `version_re.match` por
`_FIRMWARE_VERSION_RE.match`.

**Passo 7:** Executar:
```bash
.venv/bin/python -m pytest tests/test_version.py tests/test_firmware.py -v
```

### Critério de aceitação

Nenhuma chamada a `re.compile()` dentro de funções em `version.py` ou
`firmware/manager.py`. Todos os testes de versão e firmware passam.

---

## Qualidade 3: Error handling inconsistente entre módulos

### Arquivos afetados

- `fusectl/sdcard/installer.py` — `install()` retorna `list[str]`, lança `InstallError`
- `fusectl/sdcard/updater.py` — `update()` retorna `list[str]`, lança `InstallError`
- `fusectl/sdcard/firmware.py` — verifica comportamento
- `fusectl/rcm/injector.py` — `inject()` lança `RCMError`

### Problema

Existe um padrão híbrido não documentado:
- Erros **não-fatais** (falha ao copiar um arquivo, arquivo não encontrado):
  adicionados à lista de retorno
- Erros **fatais** (SD não existe, pacote inválido): lançam exceção

O problema não é o padrão em si — é que **não está documentado**. Quem mantém
o código não sabe quando esperar exceção vs. quando checar a lista retornada.

### O que fazer

Esta é uma correção de **documentação de código**, não de lógica. Nenhuma linha
de lógica deve ser alterada.

**Passo 1:** Verificar `install()` em `installer.py` (linha 48-62). A docstring
já documenta `Returns: Lista de erros (vazia se tudo ok)` mas não documenta as
exceções possíveis. Atualizar:

```python
def install(
    package_dir: Path,
    sd_root: Path,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[str]:
    """Instala pacote CFW no SD card.

    Args:
        package_dir: Diretório do pacote CFW (contém atmosphere/, bootloader/, etc.).
        sd_root: Ponto de montagem do SD card.
        progress_callback: Callback(current, total, filename) para progresso.

    Returns:
        Lista de strings de erro (vazia se tudo ok). Erros não-fatais: falha ao
        copiar arquivo individual, arquivo de origem ausente.

    Raises:
        InstallError: pacote inválido, SD não encontrado, ou espaço insuficiente.
    """
```

**Passo 2:** Verificar `update()` em `updater.py` (linha 18-37). A docstring já
existe. Adicionar seção `Raises`:

```python
    Returns:
        Lista de erros (vazia se tudo ok).

    Raises:
        InstallError: espaço insuficiente no SD.
    """
```

**Passo 3:** Verificar `inject()` em `injector.py` (linha 259). Adicionar
documentação de raises:

```python
    Raises:
        RCMError: device não encontrado, permissão negada, ou falha no ioctl.
    """
```

### Critério de aceitação

Todas as funções públicas de `sdcard/` e `rcm/` têm docstrings com seção `Raises`
documentando as exceções possíveis. Nenhuma lógica é alterada.

---

## Qualidade 4: Cache para leitura de `/proc/mounts`

### Arquivo e localização

`fusectl/sdcard/detector.py`, linhas 18-36

### Código atual

```python
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
```

### Por que otimizar

`_find_fat_mounts` é chamada por `find_switch_sd()`, que é chamada por `_detect_sd()`
em `app.py`, que é chamada a cada 1,5 s pelo timer de polling. O arquivo
`/proc/mounts` muda apenas quando um volume é montado ou desmontado — raramente
durante uso normal. Reler a cada 1,5 s é desnecessário.

### Código corrigido

Adicionar cache com TTL usando `time.monotonic()`:

```python
import time   # adicionar no topo do arquivo junto com 'import os'

# Variáveis de cache — definir no escopo do módulo após as constantes
_mounts_cache: list[Path] = []
_mounts_cache_ts: float = 0.0
_MOUNTS_CACHE_TTL: float = 4.0  # segundos


def _find_fat_mounts() -> list[Path]:
    """Lista pontos de montagem FAT32/exFAT via /proc/mounts (com cache de 4 s)."""
    global _mounts_cache, _mounts_cache_ts

    now = time.monotonic()
    if now - _mounts_cache_ts < _MOUNTS_CACHE_TTL:
        return list(_mounts_cache)  # retornar cópia para evitar mutação externa

    mounts: list[Path] = []
    try:
        content = Path("/proc/mounts").read_text(encoding="utf-8", errors="replace")
    except OSError:
        log.warning("Falha ao ler /proc/mounts")
        _mounts_cache = mounts
        _mounts_cache_ts = now
        return mounts

    for line in content.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mount_point = Path(parts[1])
        fs_type = parts[2]
        if fs_type in _FAT_FILESYSTEMS:
            mounts.append(mount_point)

    _mounts_cache = mounts
    _mounts_cache_ts = now
    return list(mounts)
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/sdcard/detector.py`.

**Passo 2:** Linha 1 — adicionar `import time` após `import os`:
```python
import os
import time
```

**Passo 3:** Após as constantes `_FAT_FILESYSTEMS` (linha 15), antes de
`_find_fat_mounts` (linha 18), inserir as três variáveis de cache:
```python
_mounts_cache: list[Path] = []
_mounts_cache_ts: float = 0.0
_MOUNTS_CACHE_TTL: float = 4.0
```

**Passo 4:** Substituir o corpo de `_find_fat_mounts` (linhas 18-36) pela versão
com cache acima.

**Passo 5:** Executar:
```bash
.venv/bin/python -m pytest tests/test_sd_detector.py -v
```

### Atenção: cache entre testes

O cache usa variáveis de módulo. Testes que chamam `_find_fat_mounts` podem
interferir entre si se não resetarem o cache. Para isso, em testes que precisam
de comportamento fresco:

```python
import fusectl.sdcard.detector as det

def setup_function():
    det._mounts_cache_ts = 0.0  # forçar leitura fresh
```

### Critério de aceitação

`/proc/mounts` é lido no máximo uma vez a cada 4 s durante polling contínuo.
Todos os testes existentes de `test_sd_detector.py` passam.

---

## Qualidade 5: Path traversal em `execute_copy_files()`

### Arquivo e localização

`fusectl/sdcard/preserve.py`, linhas 122-148

### Código atual

```python
def execute_copy_files(sd_root: Path, package_dir: Path) -> list[str]:
    copies = load_copy_files(package_dir)
    errors: list[str] = []

    for src_rel, dst_rel in copies:
        src = sd_root / src_rel      # src_rel vem do pacote, apenas lstrip("/") aplicado
        dst = sd_root / dst_rel
```

### Por que é uma vulnerabilidade

Em `load_copy_files` (linha 75), os paths vêm de `copy_files.txt` do pacote CFW.
O processamento aplica `lstrip("/")` (linha 94-95), o que remove apenas barras
iniciais. Um path como `../../etc/cron.d/evil` sobrevive ao lstrip e, quando
combinado com `/media/SD/../../etc/cron.d/evil`, resolve para `/etc/cron.d/evil`.

O pacote CFW é um arquivo ZIP de terceiros que o usuário baixa — um pacote
comprometido poderia sobrescrever arquivos do sistema.

### Função auxiliar de validação

```python
def _safe_resolve(base: Path, rel: str) -> Path | None:
    """Resolve path relativo dentro de base, rejeitando traversal.

    Retorna o Path resolvido se seguro, ou None se o path escapar de base.
    """
    try:
        resolved = (base / rel).resolve()
        resolved.relative_to(base.resolve())
        return resolved
    except ValueError:
        return None
```

### Código corrigido para `execute_copy_files`

```python
def execute_copy_files(sd_root: Path, package_dir: Path) -> list[str]:
    """Executa cópias definidas em copy_files.txt.

    Origem é relativa ao SD (pós-instalação). Destino também.
    Paths que escapem da raiz do SD são rejeitados.
    Retorna lista de erros (vazia se tudo ok).
    """
    copies = load_copy_files(package_dir)
    errors: list[str] = []

    for src_rel, dst_rel in copies:
        src = _safe_resolve(sd_root, src_rel)
        dst = _safe_resolve(sd_root, dst_rel)

        if src is None:
            errors.append(f"Path de origem inválido (traversal): {src_rel}")
            log.warning("Copy file: path inválido rejeitado: %s", src_rel)
            continue

        if dst is None:
            errors.append(f"Path de destino inválido (traversal): {dst_rel}")
            log.warning("Copy file: path destino inválido rejeitado: %s", dst_rel)
            continue

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
```

### Passos de implementação

**Passo 1:** Abrir `fusectl/sdcard/preserve.py`.

**Passo 2:** Antes de `execute_copy_files` (linha 122), inserir a função auxiliar
`_safe_resolve` com o código acima.

**Passo 3:** Substituir o corpo de `execute_copy_files` (linhas 122-148) pela
versão corrigida acima.

**Passo 4:** O restante do arquivo (`load_preserve_list`, `_find_preserve_txt`,
`should_preserve`, `load_copy_files`, `_find_copy_files_txt`) permanece intacto.

### Teste de regressão

```python
def test_execute_copy_files_rejects_traversal(tmp_path: Path) -> None:
    """Paths com traversal devem ser rejeitados com erro, não executados."""
    sd = tmp_path / "sd"
    sd.mkdir()
    pkg = tmp_path / "pkg"
    pkg.mkdir()

    # criar copy_files.txt com path malicioso
    copy_txt = pkg / "copy_files.txt"
    copy_txt.write_text("switch/file.nro|../../etc/cron.d/evil\n")

    from fusectl.sdcard.preserve import execute_copy_files
    errors = execute_copy_files(sd, pkg)

    assert len(errors) == 1
    assert "traversal" in errors[0] or "inválido" in errors[0]

    # arquivo fora do SD não deve existir
    assert not (tmp_path / "etc" / "cron.d" / "evil").exists()


def test_execute_copy_files_accepts_valid_paths(tmp_path: Path) -> None:
    """Paths válidos dentro do SD devem ser copiados normalmente."""
    sd = tmp_path / "sd"
    sd.mkdir()
    (sd / "switch").mkdir()
    (sd / "switch" / "source.nro").write_bytes(b"\x00" * 64)

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    copy_txt = pkg / "copy_files.txt"
    copy_txt.write_text("switch/source.nro|switch/dest.nro\n")

    from fusectl.sdcard.preserve import execute_copy_files
    errors = execute_copy_files(sd, pkg)

    assert errors == []
    assert (sd / "switch" / "dest.nro").is_file()
```

### Critério de aceitação

- Paths com `../` ou absolutos são rejeitados com mensagem de erro descritiva
- Nenhum arquivo é escrito fora de `sd_root`
- Paths válidos continuam funcionando normalmente
- Todos os testes existentes de `test_preserve.py` passam

---

## Resumo dos arquivos alterados

| Arquivo | Item | Tipo de mudança |
|---|---|---|
| `fusectl/sdcard/preserve.py` | Q1, Q5 | Refatoração + nova função |
| `fusectl/core/version.py` | Q2 | Mover constante |
| `fusectl/firmware/manager.py` | Q2 | Mover constante |
| `fusectl/sdcard/installer.py` | Q3 | Docstring |
| `fusectl/sdcard/updater.py` | Q3 | Docstring |
| `fusectl/sdcard/detector.py` | Q4 | Cache + novo import |
| `fusectl/rcm/injector.py` | Q3 | Docstring |

## Ordem de implementação recomendada

1. Q2 — mudança de duas linhas, zero risco
2. Q1 — refatoração isolada, coberta pelos testes existentes
3. Q3 — apenas docstrings, sem risco
4. Q4 — cache com estado global, testar isolamento entre testes
5. Q5 — segurança, requer testes novos antes de implementar

## Executar testes após cada item

```bash
cd /home/andrefarias/Desenvolvimento/fusectl
.venv/bin/python -m pytest tests/ -v
```

Todos os 120 testes existentes devem continuar passando após cada item.
