# SPRINT 4 — Documentação

Versão de referência: v0.1.0
Prioridade: baixa — não afeta funcionalidade, mas afeta adoção, manutenção e
qualidade percebida do projeto

---

## Como usar este documento

Cada item define exatamente o que criar ou modificar, onde, e o conteúdo esperado.
Não há código de produção a alterar neste sprint — apenas documentação.

---

## Doc 1: Atualizar README.md

### Arquivo

`README.md` (raiz do projeto)

### Problemas identificados

1. **Seção de instalação:** referencia `<repo-url>` hardcoded sem o URL real do
   repositório GitHub (linha 31). Deve ser substituído pelo URL real quando
   publicado.

2. **Atalhos desatualizados:** o README lista `1-5` para trocar de aba (linha 82)
   e `d` para alternar tema (linha 85). Verificar se esses atalhos ainda estão
   implementados em `app.py`. O binding para `d` não aparece em `app.py` linhas
   274-278:
   ```python
   BINDINGS = [
       Binding("ctrl+q", "quit", "Sair", show=False),
       Binding("f5", "refresh", "Atualizar", show=False),
       Binding("delete", "clear_all", "Limpar", show=False),
   ]
   ```
   O atalho `d` para alternar tema e `1-5` para abas **não estão no código atual**
   — a documentação descreve comportamento não implementado.

3. **Seção de contribuição ausente:** não há seção explicando como contribuir,
   rodar testes, ou estrutura de desenvolvimento.

4. **Seção de testes incompleta:** a seção "Testes" (linha 229-233) mostra apenas
   como rodar, sem mencionar estrutura dos testes ou como adicionar novos.

### O que adicionar

**Passo 1:** Corrigir ou remover os atalhos `1-5` e `d` da seção "Atalhos" se
não estiverem implementados. Não documentar comportamento inexistente.

**Passo 2:** Atualizar a seção "Testes" para incluir:
```markdown
## Testes

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

O projeto tem 120 testes cobrindo:
- `tests/test_installer.py` — instalação de pacotes CFW
- `tests/test_updater.py` — atualização de CFW
- `tests/test_preserve.py` — preserve.txt e copy_files.txt
- `tests/test_version.py` — detecção de versão
- `tests/test_firmware.py` — cópia de NCAs
- `tests/test_sd_detector.py` — detecção de SD montado
- `tests/test_rcm.py` — injeção RCM (requer mocks)
- `tests/test_tui_e2e.py` — testes end-to-end da TUI
- `tests/test_config.py` — configuração e detecção de pacotes
- `tests/test_stress.py` — testes de stress

Para rodar apenas um módulo:
```bash
python -m pytest tests/test_installer.py -v
```

Para ver cobertura:
```bash
python -m pytest tests/ --cov=fusectl --cov-report=term-missing
```
```

**Passo 3:** Adicionar seção "Contribuindo" antes de "Licença":
```markdown
## Contribuindo

### Configurar ambiente de desenvolvimento

```bash
git clone <url> fusectl
cd fusectl
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Estrutura do projeto

```
fusectl/
  core/       config.py, logger.py, version.py
  rcm/        detector.py, injector.py, intermezzo.py
  sdcard/     detector.py, installer.py, updater.py, preserve.py
  firmware/   manager.py
  ui/
    screens/  home.py, rcm.py, install.py, update.py, firmware.py
    widgets.py, app.py
tests/
packaging/
  debian/
  flatpak/
  appimage/
```

### Antes de abrir um PR

- `python -m pytest tests/ -v` — todos devem passar
- Sem `print()` no código de produção — usar `get_logger()`
- Sem hardcoded paths — usar `Path` relativo ou `tmp_path` nos testes
```

### Critério de aceitação

- Nenhuma seção do README descreve comportamento inexistente
- Seção de testes inclui como rodar cobertura
- Seção de contribuição explica setup do ambiente

---

## Doc 2: Criar CHANGELOG.md

### Arquivo a criar

`CHANGELOG.md` (raiz do projeto)

### Formato

Usar [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

### Conteúdo inicial

```markdown
# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento semântico conforme [SemVer](https://semver.org/lang/pt-BR/).

---

## [Não lançado]

### Adicionado
- (próximas mudanças vão aqui)

---

## [0.1.0] — 2025-10-01

### Adicionado
- Injeção de payload RCM via USB (CVE-2018-6242, Tegra X1 Erista)
- Interface TUI com tema Dracula: abas Home, RCM, Instalar, Atualizar, Firmware
- CLI completa: `fusectl rcm inject`, `fusectl install`, `fusectl update`,
  `fusectl firmware`, `fusectl sd-detect`, `fusectl version`, `fusectl payloads`
- Detecção automática de SD montado (FAT32/exFAT em /media, /mnt, /run/media)
- Detecção automática de pacote CFW por estrutura (atmosphere/, bootloader/)
- Detecção de versão instalada via hekate_ipl.ini
- Preservação de arquivos configurada via preserve.txt do pacote
- Suporte a copy_files.txt para cópias adicionais pós-instalação
- Arquivos _READONLY_FILES (package3, stratosphere.romfs) redirecionados para .apg
- Cópia de firmware NCA para /firmware/ no SD
- Empacotamento: .deb, Flatpak, AppImage
- 120 testes automatizados cobrindo todos os módulos principais
- Regra udev para acesso USB sem root
- Scripts de diagnóstico e hotplug
- Devlog de engenharia em docs/devlog-rcm-injection.md

[Não lançado]: https://github.com/USER/fusectl/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/USER/fusectl/releases/tag/v0.1.0
```

### Passos de implementação

**Passo 1:** Criar o arquivo `CHANGELOG.md` na raiz do projeto com o conteúdo acima.

**Passo 2:** Substituir `USER` pelo usuário real do GitHub quando disponível.

**Passo 3:** Ajustar a data `2025-10-01` para a data real do primeiro commit
(verificar com `git log --oneline | tail -1`).

### Critério de aceitação

`CHANGELOG.md` existe na raiz, lista as funcionalidades do v0.1.0 e tem a seção
`[Não lançado]` vazia para próximas mudanças.

---

## Doc 3: Docstrings nas funções públicas de sdcard/ e rcm/

### Arquivos e funções sem docstring adequada

Após inspeção do código, as seguintes funções precisam de docstrings com `Args`,
`Returns` e `Raises`:

**`fusectl/sdcard/installer.py`** — `install()` já tem docstring mas sem `Raises`.
Ver Sprint 3 Qualidade 3 para o texto exato.

**`fusectl/sdcard/updater.py`** — `update()` já tem docstring mas sem `Raises`.
Ver Sprint 3 Qualidade 3.

**`fusectl/rcm/injector.py`** — `inject()` (linha 259) já tem docstring descritiva
mas sem `Args`, `Returns`, `Raises` formatados.

**`fusectl/firmware/manager.py`** — `install_firmware()` (linha 16) já tem docstring
completa. `detect_firmware_source()` (linha 77) e `find_firmware_dir()` (linha 94)
têm docstrings mas sem `Args`/`Returns`.

### O que adicionar em `inject()` (injector.py, linha 259)

```python
def inject(payload_path: Path, device: Optional[usb.core.Device] = None) -> None:
    """Injeta payload no Switch em modo RCM.

    Segue a mesma sequência do fusee-launcher original (CTCaer):
    1. Localizar device RCM via USB (VID 0x0955 / PID 0x7321)
    2. Ler device ID (16 bytes) para iniciar protocolo
    3. Construir payload: intermezzo (124 bytes) + payload real, alinhado a 0x1000
    4. Enviar em chunks de 0x1000 bytes via USB bulk transfer
    5. Acionar vulnerabilidade via ioctl USBDEVFS_SUBMITURB (>4096 bytes)

    Args:
        payload_path: Path para o arquivo .bin do payload (ex: fusee.bin).
        device: Dispositivo USB já aberto. Se None, detecta automaticamente.

    Returns:
        None. Injeção bem-sucedida quando o Switch inicializa o payload.

    Raises:
        RCMError: Switch não encontrado, permissão negada (/dev/bus/usb/),
                  payload inválido, ou falha no ioctl (ver errno no log).
    """
```

### Passos de implementação

**Passo 1:** Para cada função listada, abrir o arquivo correspondente.

**Passo 2:** Localizar a docstring existente. Se tiver apenas texto descritivo
sem `Args`/`Returns`/`Raises`, adicionar as seções faltantes mantendo o texto
existente.

**Passo 3:** Não alterar nenhuma linha de código — apenas a docstring entre aspas
triplas.

### Critério de aceitação

Todas as funções públicas de `sdcard/`, `rcm/` e `firmware/` têm docstrings com:
- Descrição de uma linha
- `Args:` com tipo e descrição de cada parâmetro
- `Returns:` com o que é retornado
- `Raises:` com as exceções e condições

---

## Doc 4: Criar `docs/architecture.md`

### Arquivo a criar

`docs/architecture.md`

### Verificar que o diretório existe

O diretório `docs/` deve existir (tem `devlog-rcm-injection.md`). Verificar:
```bash
ls /home/andrefarias/Desenvolvimento/fusectl/docs/
```

### Conteúdo

```markdown
# Arquitetura do fusectl

## Visão geral

```
fusectl/
├── core/           Utilitários compartilhados
│   ├── config.py       Constantes, detecção de pacote CFW
│   ├── logger.py       Logger rotacionado centralizado
│   └── version.py      Detecção de versão instalada e do pacote
│
├── rcm/            Protocolo RCM (USB / exploit)
│   ├── detector.py     Detecção do Switch em modo RCM via libusb
│   ├── injector.py     Injeção de payload (protocolo fusee-launcher)
│   └── intermezzo.py   Payload intermediário hardcoded (124 bytes)
│
├── sdcard/         Operações no microSD
│   ├── detector.py     Detecção de SD montado via /proc/mounts
│   ├── installer.py    Instalação de pacote CFW
│   ├── updater.py      Atualização de CFW (preserva arquivos)
│   └── preserve.py     Lógica de preserve.txt e copy_files.txt
│
├── firmware/       Cópia de NCAs de firmware
│   └── manager.py      Cópia de arquivos .nca para /firmware/ no SD
│
└── ui/             Interface TUI (Textual)
    ├── app.py          FuseCtlApp — app principal, polling, roteamento
    ├── widgets.py      NavBar, Toolbar, StatusIndicator, InfoPanel, Banner
    └── screens/
        ├── home.py         Aba Home (status geral)
        ├── rcm.py          Aba RCM (injeção de payload)
        ├── install.py      Aba Instalar
        ├── update.py       Aba Atualizar
        ├── firmware.py     Aba Firmware
        ├── confirm.py      Dialog de confirmação
        └── file_picker.py  Seletor de arquivo
```

## Fluxo de polling

```
FuseCtlApp.on_mount()
  └── set_interval(1.5s, _poll_status)

_poll_status()
  ├── _detect_package()     → self._pkg_dir (Path | None)
  ├── _check_rcm()          → rcm_connected (bool)
  ├── _detect_sd()          → self._sd_paths (list[Path])
  ├── _update_global_status(rcm_connected)  → NavBar
  └── propaga para screens:
      ├── HomeScreen.refresh_status(...)
      ├── RCMScreen.update_rcm_status(...)
      ├── RCMScreen.update_payloads(...)
      ├── InstallScreen.set_package_path(...)
      ├── UpdateScreen.set_package_path(...)
      ├── UpdateScreen.show_version_diff(...)
      └── FirmwareScreen.set_firmware_path(...)
```

## Fluxo de instalação

```
InstallScreen (botão "Instalar")
  └── FuseCtlApp._do_install()
      ├── validar package_dir e sd_root
      ├── mostrar ConfirmScreen
      └── @work _install_worker(package_dir, sd_root)
          └── installer.install(package_dir, sd_root, progress_callback)
              ├── is_cfw_package() — valida estrutura
              ├── get_sd_free_space() — valida espaço
              ├── load_preserve_list() — carrega preserve.txt
              ├── _collect_files() — lista arquivos a copiar
              ├── para cada arquivo:
              │   ├── should_preserve() — pular se preservado
              │   ├── redirecionar _READONLY_FILES para .apg
              │   └── shutil.copy2()
              └── execute_copy_files() — copy_files.txt
```

## Dependências externas

| Dependência | Uso | Versão mínima |
|---|---|---|
| `pyusb` | comunicação USB com Switch em RCM | 1.2.0 |
| `textual` | framework TUI | 0.40.0 |
| `rich` | renderização de texto no terminal | 13.0.0 |
| `libusb 1.0` | backend nativo do pyusb (sistema) | qualquer 1.x |

## Modelo de threading

- Polling (`_poll_status`) roda na thread principal do Textual via `set_interval`
- Operações longas (install, update, firmware) rodam em workers via `@work`
  (decorator do Textual que usa threads gerenciadas)
- Não há uso de `asyncio` diretamente no código de produção

## Logging

Todos os módulos usam `get_logger("nome.modulo")` de `fusectl.core.logger`.
O logger escreve em `~/.local/share/fusectl/fusectl.log` com rotação automática.
```

### Passos de implementação

**Passo 1:** Verificar se `docs/` existe:
```bash
ls /home/andrefarias/Desenvolvimento/fusectl/docs/
```

**Passo 2:** Criar `docs/architecture.md` com o conteúdo acima.

**Passo 3:** Adicionar link na seção "Estrutura do projeto" do README:
```markdown
Arquitetura detalhada: [docs/architecture.md](docs/architecture.md)
```

### Critério de aceitação

`docs/architecture.md` existe, descreve a estrutura de módulos, fluxo de polling
e fluxo de instalação de forma que um desenvolvedor novo consiga entender onde
cada funcionalidade está implementada sem ler todo o código.

---

## Resumo dos arquivos criados/modificados

| Arquivo | Ação | Prioridade dentro do sprint |
|---|---|---|
| `README.md` | Atualizar atalhos, expandir testes, adicionar contribuição | Alta |
| `CHANGELOG.md` | Criar com v0.1.0 | Alta |
| `fusectl/rcm/injector.py` | Expandir docstring de `inject()` | Média |
| `docs/architecture.md` | Criar | Média |
| `fusectl/sdcard/installer.py` | Ver Sprint 3 Q3 | Baixa |
| `fusectl/sdcard/updater.py` | Ver Sprint 3 Q3 | Baixa |
| `fusectl/firmware/manager.py` | Expandir docstrings | Baixa |

## Ordem de implementação recomendada

1. CHANGELOG.md — arquivo novo, sem dependências
2. docs/architecture.md — arquivo novo, sem dependências
3. README.md — atualizar seções existentes
4. Docstrings — último, pois depende de ver o código final após outros sprints

## Verificação final

```bash
# Nenhum teste deve quebrar após este sprint (apenas documentação)
cd /home/andrefarias/Desenvolvimento/fusectl
.venv/bin/python -m pytest tests/ -v
```
