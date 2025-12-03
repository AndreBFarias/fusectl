# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão: [SemVer](https://semver.org/lang/pt-BR/).

---

## [Não lançado]

---

## [0.1.1] — 2026-03-16

### Corrigido
- `_update_global_status()` implementado: NavBar exibe status real de RCM e SD
  após cada ciclo de polling (`fusectl/ui/app.py`)
- `_trigger_vulnerability()`: OSError tratada por errno — ENODEV silencioso
  (comportamento esperado do smash), demais erros relançados como `RCMError`
  com mensagem descritiva (`fusectl/rcm/injector.py`)
- `_remove_old_hekate()`: iteração sobre diretório materializada com `list()`
  antes de remover arquivos, evitando comportamento indefinido em FAT32
  (`fusectl/sdcard/updater.py`)
- `update_payloads()`: guarda `0 <= prev_idx` adicionada para prevenir acesso
  com índice negativo (`fusectl/ui/screens/rcm.py`)
- `install()` e `update()`: arquivo stale sem extensão `.apg` removido antes de
  criar a versão `.apg` para `_READONLY_FILES`, evitando coexistência de
  `package3` e `package3.apg` no SD (`fusectl/sdcard/installer.py`,
  `fusectl/sdcard/updater.py`)
- Bordas circulares internas removidas dos botões de conteúdo (`fusectl/ui/app.py`)

### Testes
- 11 testes de regressão adicionados cobrindo os bugs acima (total: 139 testes)

### Documentação
- README reescrito com golden path completo: arquitetura, fluxos, setup dev, CI/CD

---

## [0.1.0] — 2025-10-01

### Adicionado
- Injeção de payload RCM via USB (CVE-2018-6242, Tegra X1 Erista)
- Interface TUI com tema Dracula: tela Home + tela de Operações (RCM, Instalar, Atualizar, Firmware em rolagem)
- CLI completa: `fusectl rcm inject`, `fusectl install`, `fusectl update`,
  `fusectl firmware`, `fusectl sd-detect`, `fusectl version`, `fusectl payloads`
- Detecção automática de SD montado (FAT32/exFAT em /media, /mnt, /run/media)
- Detecção automática de pacote CFW por estrutura (atmosphere/, bootloader/)
- Detecção de versão instalada via hekate_ipl.ini
- Preservação de arquivos via preserve.txt do pacote
- Suporte a copy_files.txt para cópias adicionais pós-instalação
- Arquivos `_READONLY_FILES` (package3, stratosphere.romfs) redirecionados para .apg
- Cópia de firmware NCA para /firmware/ no SD
- Empacotamento: .deb, Flatpak, AppImage
- 128 testes automatizados cobrindo todos os módulos principais
- Regra udev para acesso USB sem root
- Scripts de diagnóstico e hotplug
- Devlog de engenharia em docs/devlog-rcm-injection.md
