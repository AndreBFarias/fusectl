# SPRINT 5 — CI/CD e Packaging

Versão de referência: v0.1.0
Prioridade: alta para releases — os bugs aqui impedem que artefatos sejam publicados
corretamente no GitHub Releases

---

## Como usar este documento

Cada item contém:
- **Código atual** — trecho exato do arquivo com número de linha
- **O que está errado** — explicação técnica
- **Código corrigido** — substituição exata pronta para copiar
- **Passos numerados** — sem ambiguidade
- **Como verificar** — como confirmar que a correção funciona

---

## CI 1: Path de artefatos Flatpak incorreto no job de release

### Arquivo e localização

`.github/workflows/release.yml`, linha 103

### Código atual

```yaml
  release:
    needs: [build-deb, build-flatpak, build-appimage]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            deb-package/*.deb
            fusectl-x86_64.flatpak/*.flatpak    # PROBLEMA aqui
            appimage/*.AppImage
```

### Por que está errado

O job `build-flatpak` usa a action `flatpak/flatpak-github-actions/flatpak-builder@v6`
com `bundle: fusectl.flatpak`. Essa action faz upload do artefato com nome padrão
**"Flatpak Package"** — o nome do artefato no GitHub Actions é a string interna
usada pelo `actions/download-artifact`. O `download-artifact@v4` baixa o artefato
"Flatpak Package" para um diretório com o mesmo nome: `Flatpak Package/`.

O glob `fusectl-x86_64.flatpak/*.flatpak` nunca vai encontrar nada porque:
1. O diretório criado pelo download é `Flatpak Package/` (com espaço)
2. O arquivo dentro é `fusectl.flatpak`, não `*.flatpak` em `fusectl-x86_64.flatpak/`

### Verificação do nome real

Para confirmar o nome do artefato, olhar a action no GitHub:
- URL: https://github.com/flatpak/flatpak-github-actions
- O artefato é nomeado `"Flatpak Package"` por padrão na v6

### Código corrigido

```yaml
  release:
    needs: [build-deb, build-flatpak, build-appimage]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            deb-package/*.deb
            Flatpak Package/*.flatpak
            appimage/*.AppImage
          generate_release_notes: true
```

### Passos de implementação

**Passo 1:** Abrir `.github/workflows/release.yml`.

**Passo 2:** Localizar linha 103: `fusectl-x86_64.flatpak/*.flatpak`.

**Passo 3:** Substituir por: `Flatpak Package/*.flatpak`

**Nota importante:** se o espaço no nome causar problema com o YAML, usar aspas:
```yaml
          files: |
            deb-package/*.deb
            "Flatpak Package/*.flatpak"
            appimage/*.AppImage
```

**Passo 4:** Confirmar que o nome do artefato está correto fazendo um push de tag
de teste (`v0.1.0-rc1`) e verificando os artefatos no painel Actions do GitHub.

### Como verificar sem fazer release

```bash
# Inspecionar o workflow sem executar:
cat .github/workflows/release.yml | grep -A5 "download-artifact"

# Para testar localmente com act (se instalado):
act -j build-flatpak --dry-run
```

### Critério de aceitação

O arquivo `.flatpak` aparece nos artefatos do GitHub Release após um push de tag.

---

## CI 2: AppRun.sh com Python hardcoded

### Arquivo e localização

`packaging/appimage/AppRun`, linha 3

### Código atual

```bash
#!/bin/bash
APPDIR="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$APPDIR/usr/lib/python3.12/site-packages:$PYTHONPATH"
export PATH="$APPDIR/usr/bin:$PATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:${LD_LIBRARY_PATH:-}"
exec python3 -m fusectl "$@"
```

### Por que está errado

`python3.12` está hardcoded em `PYTHONPATH`. O `pyproject.toml` declara
`requires-python = ">=3.10"` e suporta 3.10, 3.11, 3.12. O job `build-appimage`
no CI usa Python 3.12, mas se alguém:
1. Construir o AppImage localmente com Python 3.10 ou 3.11
2. O AppImage rodar em um sistema onde `python3` resolve para 3.10 ou 3.11

O `PYTHONPATH` apontará para `python3.12/site-packages` mas os pacotes foram
instalados em `python3.10/site-packages`. Resultado: `ModuleNotFoundError` ao
executar `python3 -m fusectl`.

### Código corrigido

Detectar a versão dinamicamente:

```bash
#!/bin/bash
APPDIR="$(dirname "$(readlink -f "$0")")"
PYVER="$(python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')"
export PYTHONPATH="$APPDIR/usr/lib/$PYVER/site-packages:$PYTHONPATH"
export PATH="$APPDIR/usr/bin:$PATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:${LD_LIBRARY_PATH:-}"
exec python3 -m fusectl "$@"
```

### Passos de implementação

**Passo 1:** Abrir `packaging/appimage/AppRun`.

**Passo 2:** Substituir a linha 3:
```bash
# De:
export PYTHONPATH="$APPDIR/usr/lib/python3.12/site-packages:$PYTHONPATH"

# Para (duas linhas — a detecção e o export):
PYVER="$(python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')"
export PYTHONPATH="$APPDIR/usr/lib/$PYVER/site-packages:$PYTHONPATH"
```

**Passo 3:** Verificar que o arquivo começa com `#!/bin/bash` e que `exec python3`
na última linha permanece intacto.

**Passo 4:** O arquivo final deve ser:
```bash
#!/bin/bash
APPDIR="$(dirname "$(readlink -f "$0")")"
PYVER="$(python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')"
export PYTHONPATH="$APPDIR/usr/lib/$PYVER/site-packages:$PYTHONPATH"
export PATH="$APPDIR/usr/bin:$PATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:${LD_LIBRARY_PATH:-}"
exec python3 -m fusectl "$@"
```

### Como verificar

```bash
# Testar a detecção isoladamente:
python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")'
# Deve retornar: python3.12 (ou a versão instalada)

# Verificar que o script é executável:
ls -la packaging/appimage/AppRun
# Deve ter +x

# Testar sintaxe bash:
bash -n packaging/appimage/AppRun
```

### Critério de aceitação

`packaging/appimage/AppRun` funciona com Python 3.10, 3.11 e 3.12. O caminho do
`PYTHONPATH` corresponde à versão real do Python disponível no sistema.

---

## CI 3: `sed` hardcoded no job de build-deb

### Arquivo e localização

`.github/workflows/release.yml`, linha 32

### Código atual

```yaml
  build-deb:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          sudo apt-get update
          sudo apt-get install -y build-essential debhelper dh-python python3-all python3-venv python3-pip
      - run: |
          VERSION="${GITHUB_REF_NAME#v}"
          sed -i "s/fusectl (0.1.0-1)/fusectl (${VERSION})/" packaging/debian/changelog
```

### Por que está errado

O sed busca literalmente `fusectl (0.1.0-1)` no changelog. Esse valor está hardcoded
para v0.1.0. No lançamento de v0.2.0:
1. `GITHUB_REF_NAME` será `v0.2.0`, portanto `VERSION=0.2.0`
2. O sed tentará substituir `fusectl (0.1.0-1)` por `fusectl (0.2.0)`
3. Se o changelog já foi atualizado para conter a versão anterior (`0.1.0`),
   a substituição pode funcionar uma vez, mas na segunda release (`0.3.0`) falha
   se o texto não foi atualizado.

O padrão correto é ter um placeholder no arquivo de changelog que nunca muda.

### Verificar o arquivo de changelog atual

```bash
head -3 /home/andrefarias/Desenvolvimento/fusectl/packaging/debian/changelog
```

O conteúdo atual deve ser algo como:
```
fusectl (0.1.0-1) unstable; urgency=low
```

### Código corrigido (duas opções)

**Opção A (recomendada):** Usar placeholder no changelog e substituir pelo tag:

1. Editar `packaging/debian/changelog` para usar placeholder:
```
fusectl (UNRELEASED) unstable; urgency=low

  * Release

 -- Maintainer <email>  Mon, 01 Jan 2024 00:00:00 +0000
```

2. Atualizar o sed no workflow para buscar o placeholder:
```yaml
      - run: |
          VERSION="${GITHUB_REF_NAME#v}"
          sed -i "s/fusectl (UNRELEASED)/fusectl (${VERSION}-1)/" packaging/debian/changelog
```

**Opção B (alternativa sem alterar changelog):** Buscar a primeira linha com o
padrão e substituir independente do número de versão:

```yaml
      - run: |
          VERSION="${GITHUB_REF_NAME#v}"
          sed -i "1s/fusectl ([^)]*)/fusectl (${VERSION}-1)/" packaging/debian/changelog
```

O `1s` aplica a substituição apenas na primeira linha. O regex `[^)]*` casa qualquer
versão existente.

### Passos de implementação para Opção A (recomendada)

**Passo 1:** Abrir `packaging/debian/changelog`.

**Passo 2:** Substituir o número de versão na primeira linha por `UNRELEASED`:
```
# De:
fusectl (0.1.0-1) unstable; urgency=low

# Para:
fusectl (UNRELEASED) unstable; urgency=low
```

**Passo 3:** Abrir `.github/workflows/release.yml`, linha 32. Substituir:
```yaml
# De:
          sed -i "s/fusectl (0.1.0-1)/fusectl (${VERSION})/" packaging/debian/changelog

# Para:
          sed -i "s/fusectl (UNRELEASED)/fusectl (${VERSION}-1)/" packaging/debian/changelog
```

### Como verificar

```bash
# Simular o que o CI faz:
VERSION="0.2.0"
cp packaging/debian/changelog /tmp/changelog_test
sed -i "s/fusectl (UNRELEASED)/fusectl (${VERSION}-1)/" /tmp/changelog_test
head -1 /tmp/changelog_test
# Deve retornar: fusectl (0.2.0-1) unstable; urgency=low
```

### Critério de aceitação

O sed funciona corretamente para qualquer versão sem modificar o workflow. A primeira
linha do changelog resultante é `fusectl (X.Y.Z-1) unstable; urgency=low`.

---

## CI 4: `asyncio_mode` ausente em `pyproject.toml`

### Arquivo e localização

`pyproject.toml`, linhas 42-44

### Código atual

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Por que precisa ser corrigido

`pytest-asyncio` >= 0.21 emite `PytestUnraisableExceptionWarning` e em versões
futuras exigirá que `asyncio_mode` seja declarado explicitamente. Sem isso:

1. Testes assíncronos podem falhar silenciosamente (não são reconhecidos como async)
2. `pytest-asyncio` 0.23+ exige o campo ou emite erro

O projeto já tem `pytest-asyncio>=0.21` em `[project.optional-dependencies].dev`
(linha 33).

### Código corrigido

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Passos de implementação

**Passo 1:** Abrir `pyproject.toml`.

**Passo 2:** Localizar `[tool.pytest.ini_options]` (linha 42). Adicionar a linha
após `testpaths = ["tests"]`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**Passo 3:** Executar os testes para verificar que nada quebrou:
```bash
cd /home/andrefarias/Desenvolvimento/fusectl
.venv/bin/python -m pytest tests/ -v 2>&1 | head -30
```

**Passo 4:** Verificar que nenhum warning de `PytestUnraisableExceptionWarning`
aparece na saída.

### O que é `asyncio_mode = "auto"`

Com `"auto"`, pytest-asyncio automaticamente detecta e trata coroutines como testes
assíncronos sem precisar do decorator `@pytest.mark.asyncio` em cada função. Testes
síncronos existentes não são afetados — o modo `"auto"` só se aplica a funções
`async def`.

### Verificar testes assíncronos existentes

```bash
grep -n "async def test_" tests/*.py
```

Se houver testes `async def`, eles devem rodar sem `@pytest.mark.asyncio` após
adicionar `asyncio_mode = "auto"`. Se algum teste usa o decorator, ele pode ser
removido (redundante), mas não é obrigatório.

### Critério de aceitação

- `pyproject.toml` tem `asyncio_mode = "auto"` em `[tool.pytest.ini_options]`
- Todos os 120 testes passam
- Nenhum `PytestUnraisableExceptionWarning` na saída do pytest

---

## Verificação adicional: regex compilada em `firmware/manager.py`

Este item não foi incluído no Sprint 3 mas foi identificado durante a leitura do código.

### Arquivo e localização

`fusectl/firmware/manager.py`, linha 79

### Código

```python
def detect_firmware_source(search_root: Path) -> Path | None:
    """Detecta diretório de firmware pelo padrão de nome (XX.Y.Z) em um diretório."""
    version_re = re.compile(r"^\d+\.\d+\.\d+$")   # recompilada a cada chamada
```

### Fix

Mesmo padrão do Sprint 3 Qualidade 2. Mover para constante de módulo após os imports:

```python
_FIRMWARE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
```

E substituir `version_re.match` por `_FIRMWARE_VERSION_RE.match` em
`detect_firmware_source`.

Embora seja o mesmo padrão que `_FIRMWARE_VERSION_RE` em `version.py`, manter
uma constante em cada módulo é preferível a importar entre módulos não relacionados.

---

## Resumo dos arquivos alterados

| Arquivo | Item | Tipo de mudança |
|---|---|---|
| `.github/workflows/release.yml` | CI 1, CI 3 | Corrigir glob + corrigir sed |
| `packaging/appimage/AppRun` | CI 2 | Detecção dinâmica de versão Python |
| `packaging/debian/changelog` | CI 3 | Substituir versão por UNRELEASED |
| `pyproject.toml` | CI 4 | Adicionar asyncio_mode |
| `fusectl/firmware/manager.py` | Extra | Mover regex para constante |

## Ordem de implementação recomendada

1. CI 4 — mudança de uma linha em pyproject.toml, verificar imediatamente
2. CI 2 — mudança em AppRun, testável localmente
3. CI 3 — duas mudanças (changelog + sed), testável com simulação local
4. CI 1 — requer push de tag para verificar completamente

## Executar verificação local

```bash
# Verificar testes após CI 4:
cd /home/andrefarias/Desenvolvimento/fusectl
.venv/bin/python -m pytest tests/ -v

# Verificar AppRun após CI 2:
bash -n packaging/appimage/AppRun

# Simular sed após CI 3:
VERSION="0.2.0"
cp packaging/debian/changelog /tmp/cl_test
sed -i "s/fusectl (UNRELEASED)/fusectl (${VERSION}-1)/" /tmp/cl_test
head -1 /tmp/cl_test
```
