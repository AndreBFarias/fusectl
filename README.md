# fusectl

Gerenciador Linux para Custom Firmware Nintendo Switch (Tegra X1 — Erista).

Compatível com qualquer all-in-one pack de CFW (Atmosphere, Hekate, CNX, Kefir, DeepSea, etc.).

![fusectl TUI](assets/screenshot.png)

---

## Funcionalidades

- Injeção de payload RCM via USB (CVE-2018-6242, Tegra X1 Erista)
- Instalação e atualização de pacotes CFW no microSD
- Cópia de firmware (.nca) para o SD
- Detecção automática de dispositivos, SD montado e versões
- Interface TUI com tema Dracula
- CLI completa para automação e scripts

---

## Requisitos de sistema

| Requisito | Versão mínima |
|---|---|
| Python | 3.10+ |
| libusb | 1.0 (não 0.1) |
| Kernel Linux | 5.4+ (exFAT nativo) ou fuse-exfat |
| Conexão USB | Direta (sem hub), porta xHCI (USB 3.0) |

**Hardware suportado:** Nintendo Switch Tegra X1 Erista (HAC-001). Não funciona em Mariko (HAC-001-01) — bootrom corrigida.

---

## Instalação

### Via script (recomendado para usuário final)

```bash
git clone https://github.com/AndreBFarias/fusectl.git
cd fusectl
./install.sh
```

O script instala: libusb, ambiente virtual Python, dependências e regra udev.

### Via .deb (Ubuntu / Pop!_OS / Debian)

```bash
sudo dpkg -i fusectl_*.deb
sudo cp /usr/share/fusectl/udev/50-switch-rcm.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

### Via AppImage (portável, sem instalação)

```bash
chmod +x fusectl-x86_64.AppImage
./fusectl-x86_64.AppImage
```

Instalar regra udev manualmente — ver seção [Solução de problemas](#solução-de-problemas).

### Via Flatpak (sandbox)

```bash
flatpak-builder --install --user build-dir packaging/flatpak/com.github.fusectl.fusectl.yml
```

O Flatpak roda em sandbox. A regra udev precisa ser instalada manualmente no host para acesso USB.

---

## Uso

### Interface TUI

```bash
./run.sh
```

Abre a interface com 5 seções: Home, RCM, Instalar, Atualizar, Firmware.

**Atalhos:**

| Tecla | Ação |
|---|---|
| `F5` | Atualizar status (polling manual) |
| `Delete` | Limpar todos os campos |
| `Ctrl+Q` | Sair |

### CLI

```bash
# Verificar se Switch está em modo RCM
fusectl rcm status

# Injetar payload
fusectl rcm inject /caminho/para/payload.bin

# Listar payloads disponíveis no pacote
fusectl payloads -p /caminho/para/pacote-cfw

# Ver versões detectadas
fusectl version -p /caminho/para/pacote-cfw -s /mnt/sdcard

# Instalar CFW no SD
fusectl install /caminho/para/pacote-cfw /mnt/sdcard

# Atualizar CFW no SD
fusectl update /caminho/para/pacote-cfw /mnt/sdcard

# Forçar atualização (mesma versão)
fusectl update /caminho/para/pacote-cfw /mnt/sdcard --force

# Copiar firmware para SD
fusectl firmware /caminho/para/XX.Y.Z /mnt/sdcard

# Detectar SD de Switch montado
fusectl sd-detect
```

### Fluxo típico

```
1. Switch: segurar Volume+ e pressionar Power → modo RCM
2. Conectar Switch ao PC via USB-C → USB-A (direto, sem hub)
3. ./run.sh → TUI detecta Switch em RCM e SD montado
4. Aba RCM → selecionar payload (fusee.bin) → Injetar → Switch inicia Hekate
5. No Hekate: Tools → USB Tools → SD Card → Mount (monta SD via USB)
6. TUI detecta SD montado e exibe espaço livre
7. Aba Instalar (primeira vez) ou Atualizar → confirmar → aguardar cópia
```

---

## Arquitetura

```
fusectl/                     Pacote principal Python
├── core/
│   ├── config.py            Constantes, detecção de pacote CFW, list_payloads
│   ├── logger.py            Logger rotacionado centralizado (get_logger)
│   └── version.py           Detecção de versão instalada e do pacote
│
├── rcm/
│   ├── detector.py          Detecção do Switch em modo RCM via libusb
│   ├── injector.py          Injeção de payload — protocolo fusee-launcher
│   └── intermezzo.py        Payload intermediário hardcoded (124 bytes, CTCaer)
│
├── sdcard/
│   ├── detector.py          Detecção de SD montado via /proc/mounts
│   ├── installer.py         Instalação de pacote CFW (install)
│   ├── updater.py           Atualização de CFW (update, _remove_old_hekate)
│   └── preserve.py          Lógica de preserve.txt, copy_files.txt, path traversal
│
├── firmware/
│   └── manager.py           Cópia de arquivos .nca para /firmware/ no SD
│
└── ui/
    ├── app.py               FuseCtlApp — app principal, polling, roteamento de eventos
    ├── widgets.py           NavBar, Toolbar, StatusIndicator, InfoPanel, Banner
    └── screens/
        ├── home.py          Aba Home (status geral, espaço livre SD)
        ├── rcm.py           Aba RCM (lista de payloads, injeção)
        ├── install.py       Aba Instalar
        ├── update.py        Aba Atualizar (diff de versão)
        ├── firmware.py      Aba Firmware
        ├── confirm.py       Dialog de confirmação antes de operações destrutivas
        └── file_picker.py   Seletor de arquivo (browser de diretório)

tests/                       Pytest — 139 testes
packaging/
├── debian/                  Empacotamento .deb (dpkg-buildpackage)
├── flatpak/                 Manifesto Flatpak (.yml)
└── appimage/                AppRun.sh + metadados AppImage
docs/
└── devlog-rcm-injection.md  Detalhes técnicos do protocolo RCM
scripts/
├── diag_rcm.sh              Diagnóstico completo do ambiente USB
├── hotplug_inject.py        Injeção automática ao conectar Switch
└── install_udev.sh          Instalação manual da regra udev
udev/
└── 50-switch-rcm.rules      Regra udev para acesso USB sem root
```

### Fluxo de polling (a cada 1,5 s)

```
FuseCtlApp.on_mount()
  └── set_interval(1.5s, _poll_status)

_poll_status()
  ├── _detect_package()   → self._pkg_dir (Path | None)
  ├── _check_rcm()        → rcm_connected (bool)
  ├── _detect_sd()        → self._sd_paths (list[Path])
  ├── _update_global_status(rcm_connected)  → NavBar status text
  └── propaga para screens:
      ├── HomeScreen.refresh_status(...)
      ├── RCMScreen.update_rcm_status(...)
      ├── RCMScreen.update_payloads(...)
      ├── InstallScreen.set_package_path(...)   # apenas se vazio
      ├── UpdateScreen.set_package_path(...)    # apenas se vazio
      ├── UpdateScreen.show_version_diff(...)
      └── FirmwareScreen.set_firmware_path(...) # apenas se vazio
```

### Fluxo de instalação

```
Botão "Instalar" → FuseCtlApp._do_install()
  ├── validar package_dir e sd_root
  ├── push_screen(ConfirmScreen) → aguardar confirmação
  └── @work _install_worker(package_dir, sd_root)
      └── installer.install(package_dir, sd_root, progress_callback)
          ├── is_cfw_package()           → valida estrutura atmosphere/
          ├── load_preserve_list()       → carrega preserve.txt
          ├── _collect_files()           → lista arquivos a copiar
          ├── para cada arquivo:
          │   ├── should_preserve()      → pular se em preserve_list
          │   ├── _READONLY_FILES        → redirecionar para .apg
          │   ├── remover stale sem .apg → se existir versão sem extensão
          │   └── shutil.copy2()
          └── execute_copy_files()       → copy_files.txt (cópias adicionais)
```

### Dependências

| Pacote | Uso | Versão mínima |
|---|---|---|
| `pyusb` | Comunicação USB com Switch em RCM | 1.2.0 |
| `textual` | Framework TUI | 0.40.0 |
| `rich` | Renderização de texto no terminal | 13.0.0 |
| `libusb 1.0` | Backend nativo do pyusb (sistema) | 1.x |

---

## Desenvolvimento

### Configurar ambiente

```bash
git clone https://github.com/AndreBFarias/fusectl.git
cd fusectl
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Rodar a TUI em desenvolvimento

```bash
./run.sh
# ou
python -m fusectl
# ou com verbose
python -m fusectl -v
```

### Estrutura de testes

```
tests/
├── conftest.py          Fixtures: cnx_package, sd_card, mock_usb_device
├── test_installer.py    Instalação de pacotes CFW
├── test_updater.py      Atualização de CFW, remoção de arquivos obsoletos
├── test_preserve.py     preserve.txt, copy_files.txt, path traversal
├── test_version.py      Detecção de versão instalada e do pacote
├── test_firmware.py     Cópia de NCAs
├── test_sd_detector.py  Detecção de SD montado
├── test_rcm.py          Protocolo RCM, build_payload, inject (mocks USB)
├── test_tui_e2e.py      Testes end-to-end da TUI (Textual headless pilot)
├── test_config.py       Configuração, detecção de pacotes
└── test_stress.py       Testes de stress e volume
```

### Comandos de teste

```bash
# Suite completa
python -m pytest tests/ -v

# Módulo específico
python -m pytest tests/test_installer.py -v

# Com cobertura
python -m pytest tests/ --cov=fusectl --cov-report=term-missing

# Apenas E2E
python -m pytest tests/test_tui_e2e.py -v

# Diagnóstico de falha com output completo
python -m pytest tests/ -v --tb=long -s
```

### Convenções de código

- **Linguagem:** Python 3.10+, type hints obrigatórios
- **Logger:** sempre `get_logger("modulo.submodulo")` — nunca `print()`
- **Paths:** sempre `pathlib.Path` — nunca strings hardcoded
- **Commits:** PT-BR, imperativo, formato `tipo: descrição`
  - Tipos: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`
- **Limite de arquivo:** 800 linhas (exceção: testes, configurações)
- **Error handling:** explícito — nunca `except: pass` sem logging

### Adicionar um novo módulo

1. Criar `fusectl/<subpacote>/<modulo>.py`
2. Adicionar `get_logger("subpacote.modulo")` no topo
3. Criar `tests/test_<modulo>.py` com pelo menos um teste por função pública
4. Importar no `__init__.py` do subpacote se for API pública
5. Documentar no fluxo de arquitetura acima

---

## CI/CD

### Pipeline de release (`.github/workflows/release.yml`)

Acionado por push de tag `v*` (ex: `git tag v0.2.0 && git push --tags`).

```
push tag v* →
  ├── test          Roda pytest no Ubuntu com Python 3.12
  ├── build-deb     dpkg-buildpackage → fusectl_*.deb
  ├── build-flatpak flatpak-builder → fusectl.flatpak
  ├── build-appimage appimagetool → fusectl-x86_64.AppImage
  └── release       softprops/action-gh-release → publica artefatos
```

### Criar um release

```bash
# Atualizar versão em pyproject.toml
# Atualizar CHANGELOG.md (seção [Não lançado] → [X.Y.Z] com data)
git add pyproject.toml CHANGELOG.md
git commit -m "chore: preparar release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

### Monitorar o workflow

```bash
# Listar runs recentes
gh run list --workflow=release.yml

# Acompanhar run em tempo real
gh run watch <run-id>

# Ver logs de um job específico
gh run view <run-id> --log
```

---

## Empacotamento local

### .deb

```bash
sudo apt-get install build-essential debhelper dh-python python3-all python3-venv
ln -s packaging/debian debian
dpkg-buildpackage -us -uc -b
```

### AppImage

```bash
cd /tmp && mkdir AppDir
pip install --target=AppDir/usr/lib/python3.$(python3 -c "import sys; print(sys.version_info.minor)")/site-packages .
cp packaging/appimage/AppRun AppDir/ && chmod +x AppDir/AppRun
# ... (ver build-appimage em release.yml para sequência completa)
```

### Flatpak

```bash
flatpak-builder build-dir packaging/flatpak/com.github.fusectl.fusectl.yml --force-clean
```

---

## Pacotes CFW compatíveis

Detecção por estrutura (presença de `atmosphere/`), não por formato proprietário.

**Detecção de versão — fallback chain:**
1. Arquivo de versão na raiz (`cnx.txt`, `version.txt`, `pack.txt`)
2. Tag `{TAG X.Y.Z}` em `bootloader/hekate_ipl.ini`
3. Padrão `X.Y.Z` no nome do diretório (ex: `AIO-19.0.1-3`)

**Arquivos protegidos (`_READONLY_FILES`):**

`atmosphere/package3` e `atmosphere/stratosphere.romfs` são copiados como `.apg`
para que o Hekate os atualize de forma controlada no primeiro boot.

---

## Solução de problemas

### udev / permissão USB

```bash
# Verificar se regra está instalada
ls /etc/udev/rules.d/50-switch-rcm.rules

# Reinstalar
sudo bash scripts/install_udev.sh

# Verificar grupo plugdev
groups $USER   # deve incluir plugdev
# Se não incluir:
sudo usermod -aG plugdev $USER && newgrp plugdev
```

### Pop!_OS / Ubuntu

- **Prioridade udev:** `50-switch-rcm.rules` deve vir antes de `69-libmtp.rules`
- **ModemManager:** a regra já inclui `ENV{ID_MM_DEVICE_IGNORE}="1"`
- **autosuspend:** a regra já inclui `autosuspend_delay_ms=-1`

### Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| Switch não detectado | USB hub, porta USB 2.0 | Usar porta xHCI diretamente |
| `EPERM` na injeção | udev não instalada ou grupo plugdev | `scripts/install_udev.sh` |
| Device stale | Tentativa anterior falhou | Reconectar fisicamente o Switch |
| SD não detectado | exFAT sem suporte | `apt install fuse-exfat` ou kernel 5.4+ |
| `ModuleNotFoundError` (AppImage) | Python version mismatch | Rebuildar AppImage com Python local |

### Diagnóstico

```bash
# Ambiente USB completo
bash scripts/diag_rcm.sh

# Injeção com log verbose
.venv/bin/python -m fusectl -v rcm inject <payload.bin>

# Log persistente
cat ~/.local/share/fusectl/fusectl.log
```

---

## Aviso legal

Esta ferramenta destina-se exclusivamente ao uso pessoal e legítimo em hardware
de propriedade do usuário, para fins de interoperabilidade de software.

**O que este projeto faz:** fornece interface para executar código em hardware
próprio, usando a vulnerabilidade pública CVE-2018-6242 (Tegra X1 RCM),
divulgada responsavelmente por Kate Temkin / ReSwitched em junho de 2018.

**O que este projeto não faz:** não distribui software proprietário, não contorna
proteções em tempo de execução, não facilita pirataria, não coleta dados.

**Base legal:** DMCA sec. 1201(f) (EUA) e Diretiva 2009/24/CE art. 6 (UE)
garantem o direito de engenharia reversa para interoperabilidade.

---

## Créditos

Injeção RCM baseada no protocolo [fusee-launcher](https://github.com/Qyriad/fusee-launcher) (Kate Temkin / ReSwitched, CVE-2018-6242).

## Desinstalação

```bash
./uninstall.sh
```

Remove ambiente virtual, regra udev e logs. Os arquivos do projeto permanecem.

## Licença

GPL-3.0-or-later. Consulte [LICENSE](LICENSE) para detalhes.
