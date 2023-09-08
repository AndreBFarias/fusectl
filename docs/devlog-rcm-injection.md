# Dev Log: Injeção RCM no Linux

Data início: 2026-03-08
Última atualização: 2026-03-09
Status: **resolvido** -- injeção funciona, Hekate carrega corretamente

---

## Ambiente

- **SO**: Pop!_OS, kernel 6.17.9-76061709-generic
- **Hardware**: Acer Nitro 5, controlador USB AMD xHCI
- **Console**: Nintendo Switch (Tegra X1 - Erista), modo RCM
- **Porta USB**: bus 3 (xHCI confirmado via sysfs)
- **Python**: 3.12.1, pyusb, libusb1
- **Textual**: 8.0.2 (TUI)

---

## O problema

Ao tentar injetar um payload no Switch via USB (protocolo fusee-launcher, CVE-2018-6242), a leitura do device ID de 16 bytes no bulk endpoint IN (0x81) retorna `actual_length=0` e expira com timeout (errno 110). O dispositivo nunca envia dados.

Isso ocorre mesmo em conexão limpa (Switch recém-conectado, nenhum processo abriu o dispositivo antes).

### Evidências coletadas

1. **lsusb** detecta o dispositivo: `Bus 003 Device XXX: ID 0955:7321 NVIDIA Corp. Switch [Tegra Erista] recovery mode`
2. **sysfs** mostra produto "APX", fabricante "NVIDIA Corp.", `bConfigurationValue=1`
3. **Nenhum kernel driver** vinculado a interface (`/sys/bus/usb/devices/3-1/3-1:1.0/driver` não existe)
4. **Permissões OK**: ACL `user:andrefarias:rw-` no device node, grupo plugdev
5. **LIBUSB_DEBUG=4** mostra: bulk URB submetido, `actual_length=0` após timeout de 5s
6. **ioctl USBDEVFS_BULK direto** (bypassing pyusb): mesmo resultado, timeout com 0 bytes
7. **Todas as control transfers falham**: GET_STATUS em endpoints e device retornam I/O Error
8. **USB reset** via pyusb falha com errno 2 (Entity not found), e o kernel entra em loop de re-enumeração que também falha (device descriptor read error -110, -71)

### O que NÃO é o problema

- **Permissões USB**: verificadas, ACL correto, MODE=0666 na regra udev
- **pyusb/libusb**: ioctl direto ao kernel dá mesmo resultado
- **Kernel driver ocupando interface**: nenhum driver vinculado

---

## Cronologia das ações

### Sessão 1 (2026-03-08)

#### 1. Correção dos testes E2E da TUI

- **Problema**: `AttributeError: module 'fusectl.rcm' has no attribute 'injector'` nos testes `test_inject_sucesso_via_mock` e `test_inject_erro_mostra_mensagem`
- **Causa**: `patch("fusectl.rcm.injector.inject")` importava `usb.core` (não instalado no ambiente de teste)
- **Tentativa 1**: fake module em `sys.modules` -- resolveu import mas causou deadlocks nos workers
- **Causa do deadlock**: `call_from_thread()` do Textual bloqueia worker thread esperando o main thread processar callback; `pilot.pause()` não processa esses callbacks de forma confiável
- **Solução final**: reescrever testes para mockar `_run_inject` em vez de `inject`, testando feedback de UI via `set_result()` direto

#### 2. Primeira tentativa de injeção real

- Executado `.venv/bin/python -m fusectl -v rcm inject <pacote>/bootloader/payloads/fusee.bin`
- Resultado: `[Errno 110] Operation timed out` na leitura do device ID

#### 3. Investigação da regra udev

- Regra original: `/etc/udev/rules.d/99-switch-rcm.rules`
- Descoberto via `udevadm test`: `/usr/lib/udev/rules.d/69-libmtp.rules:39` executa `mtp-probe` no dispositivo Tegra
- `mtp-probe` abre o dispositivo USB e envia comandos MTP via bulk endpoints
- A regra `99-switch-rcm.rules` setava `ENV{MTP_NO_PROBE}="1"`, mas rodava DEPOIS da regra 69 (tarde demais)
- **Ação**: renomeada para `50-switch-rcm.rules` (roda ANTES de `69-libmtp.rules`)
- Verificado via `udevadm test`: regra 50 é lida primeiro, `MTP_NO_PROBE=1` é setado antes da regra 69
- A regra 69 verifica `ENV{MTP_NO_PROBE}!="1"` antes de rodar `mtp-probe` -- condição satisfeita

#### 4. Configuração do run.sh

- Adicionada verificação/instalação automática da regra udev
- Adicionada remoção da regra antiga (99-)
- Adicionada verificação de libusb
- Adicionada verificação/adição do grupo plugdev
- Uso de `sg plugdev` para aplicar grupo sem logout

#### 5. Tentativas subsequentes de injeção

Mesmo após instalar a regra 50 e reconectar o Switch:
- `_read_device_id` continua retornando 0 bytes e expirando
- Adicionado `detach_kernel_driver()` -- kernel driver não estava ativo
- Adicionado `ENV{ID_MM_DEVICE_IGNORE}="1"` na regra udev -- sem efeito
- Tentativa com `set_configuration(0)` + `set_configuration(1)` -- errno 2 (Entity not found)
- Tentativa com ioctl direto ao kernel -- mesmo timeout
- Tentativa com USB reset -- falha e corrompe device (kernel entra em loop de re-enumeração)

### Sessão 2 (2026-03-09)

#### 6. Análise do fusee-launcher original (Kate Temkin / CTCaer)

Comparação com o código de referência revelou diferenças significativas na nossa implementação:

| Aspecto | fusee-launcher original | Nossa implementação (antes) |
|---------|------------------------|-----------------------------|
| `set_configuration()` | NÃO chama | Chamava |
| `claim_interface()` | NÃO chama | Chamava |
| `detach_kernel_driver()` | NÃO chama | Chamava |
| Trigger vulnerability | ioctl `USBDEVFS_SUBMITURB` direto | `ctrl_transfer()` via libusb |
| Tamanho do trigger | `STACK_END - buffer_addr` (~0xB000) | 0x7000 fixo |
| RCM command length | 0x30298 | MAX_PAYLOAD_LENGTH (0x30000) |
| Timeout | 1000ms | 5000ms |
| Buffer tracking | Alterna lowbuf/highbuf a cada write | Não rastreava |

**Problema crítico do trigger**: libusb no Linux limita control transfers ao tamanho de uma página (~4096 bytes). O exploit precisa de ~0xB000 bytes. Nosso `ctrl_transfer(data_or_wLength=0x7000)` era silenciosamente truncado pelo libusb, e a vulnerabilidade nunca era acionada corretamente. O original usa `fcntl.ioctl()` com `USBDEVFS_SUBMITURB` para contornar essa limitação.

#### 7. Reescrita do injector

Arquivo: `fusectl/rcm/injector.py`

Mudanças:
- Removido `_acquire_device()` (sem `set_configuration`, `claim_interface`, `detach_kernel_driver`)
- Trigger via ioctl `USBDEVFS_SUBMITURB` direto ao kernel
- Estrutura `_SubmitURB` (ctypes) para o ioctl
- Validação de controlador xHCI via sysfs
- Buffer tracking (alterna entre `COPY_BUFFER_ADDRESSES[0]` e `[1]` a cada write)
- RCM command length corrigido para 0x30298
- Timeout reduzido para 1000ms

#### 8. Correção dos testes para Textual 8.x

- `Label.renderable` não existe no Textual 8.x -- substituído por `Label.content` em todos os testes E2E
- `pytest-asyncio` precisou ser reinstalado (removido do venv)
- Testes com `_wait_workers` deadlockavam (Textual 8.x mudou comportamento de `call_from_thread` em modo headless) -- reescritos para mockar workers e testar UI diretamente
- `test_inject_claim_interface_error` removido (não usamos mais `claim_interface`)
- Adicionado `test_inject_xhci_validation_runs`

**Resultado**: 94 testes passando, 0 falhas, ~7s

#### 9. Tentativa de injeção com código reescrito

- Não foi possível testar: o Switch desconectou após tentativas anteriores de USB reset
- O kernel ficou em loop de re-enumeração (device descriptor read error -110, -71)
- Switch precisa ser fisicamente desconectado e reconectado

### Sessão 3 (2026-03-09)

#### 10. Análise detalhada do layout de payload vs fusee-launcher original

Comparação byte a byte revelou que `_build_payload` montava o payload com estrutura completamente diferente do original. Três bugs críticos identificados:

**Bug 1a: Intermezzo no offset errado**

| Aspecto | Original (CTCaer) | fusectl (antes) |
|---------|-------------------|-----------------|
| Offset do intermezzo | 680 (0x2A8) | 0xE40 |
| Posição no layout | Dentro do NOP sled ARM | Depois do NOP sled |

O NOP sled (676 bytes de zeros = instruções ARM `ANDEQ` condicionais) precede o intermezzo. O intermezzo relocator roda primeiro e copia o payload real para 0x40010000. No fusectl, o intermezzo estava no offset errado (0xE40 em vez de 680).

**Bug 1b: Stack spray ausente (causa principal)**

O stack spray preenche a região 0x40014E40-0x40017000 com 2160 repetições do endereço 0x40010000 (entry point). Quando o `memcpy` overflow corrompe a stack, os return addresses precisam apontar para 0x40010000. Sem stack spray, o return address é lixo e a execução vai para lugar nenhum.

Layout corrigido:
```
Offset 0x0000: RCM_CMD_LENGTH (4 bytes LE = 0x30298)
Offset 0x0004: NOP sled (676 bytes de zeros)
Offset 0x02A8: INTERMEZZO (96 bytes)
Offset 0x0308: Padding zeros
Offset 0x0E40: User payload parte 1 (até 0x4000 bytes)
Offset 0x4E40: Stack spray (0x40010000 x 2160)
Offset 0x7000: User payload parte 2 (restante)
Final:   Alinhado a 0x1000
```

**Bug 2: Ausência de `switch_to_highbuf`**

O original chama `switch_to_highbuf()` antes do trigger para garantir que o buffer ativo seja 0x40009000 (índice 1). Isso garante trigger length = 0x7000 (STACK_END - 0x40009000). Sem isso, o trigger length depende da paridade do número de chunks enviados.

#### 11. Correções aplicadas

Arquivo `fusectl/rcm/injector.py`:
- `_build_payload` reescrito com layout idêntico ao fusee-launcher original
- Constante `INTERMEZZO_ADDR` removida (não existe no original)
- Adicionadas constantes `STACK_SPRAY_START` e `STACK_SPRAY_END`
- Adicionada função `_switch_to_highbuf` para garantir high buffer antes do trigger
- Fluxo `inject()` atualizado: write -> switch_to_highbuf -> trigger

Arquivo `tests/test_rcm.py`:
- Testes de layout: intermezzo offset 680, NOP sled, stack spray
- Testes de `_switch_to_highbuf`: buffer já alto, transição de low para high
- Testes de payload pequeno (< 0x4000) e grande (> 0x4000 com segunda parte)

**Resultado**: 102 testes passando, 0 falhas, ~7s

### Sessão 4 (2026-03-09)

#### 12. Diagnóstico de ambiente

Script `scripts/diag_rcm.sh` revelou:
- `autosuspend_delay_ms=2000` (kernel suspende device em 2s)
- ModemManager ativo (potencial interferência)
- Regra udev sem proteção de autosuspend

#### 13. Correção de autosuspend

- Regra udev atualizada: `ATTR{power/autosuspend_delay_ms}="-1"`, `ATTR{power/control}="on"`
- Função `_disable_autosuspend()` adicionada ao injector (belt-and-suspenders)
- Resultado: device não trava mais, mas bulk transfers ainda timeout

#### 14. Baseline com fusee-launcher original

- **Original também falha**: mesma `USBTimeoutError` no device ID read
- Testado com sudo e sem ModemManager: mesmo resultado
- Control transfers (`GET_STATUS`, `GET_DESCRIPTOR`) retornam I/O Error
- **Conclusão**: problema é ambiental, não do código

#### 15. Descoberta: USB hub causa falha

Device em `8-1.3` (via hub USB): bulk transfers timeout.
Device em `3-1` (conexão direta): **funciona** -- device ID lido, payload enviado.

O bootrom Tegra RCM tem stack USB minimalista que não funciona bem com hubs.

#### 16. Bug crítico no layout do payload

**Causa raiz da falha de execução**: o header RCM de 680 bytes é consumido pelo
protocolo e NÃO entra no IRAM. O offset no buffer USB é `IRAM_offset + 680`.

| Aspecto | Original (correto) | fusectl (antes) |
|---------|-------------------|-----------------|
| User payload buffer offset | 4328 (0x10E8) | 3648 (0x0E40) |
| User payload IRAM addr | 0x40010E40 | 0x40010B98 |
| Intermezzo entry point | 0x40010E40 | 0x40010E40 |
| Match? | Sim | Não (680 bytes de diferença) |

O intermezzo saltava para 0x40010E40 e encontrava zeros em vez do payload.

**Correção**: padding após intermezzo usa fórmula do original:
`(RCM_PAYLOAD_START - RCM_PAYLOAD_ADDR) - len(INTERMEZZO)` (3524 bytes)
em vez de `(RCM_PAYLOAD_START - RCM_PAYLOAD_ADDR) - len(payload_so_far)` (2844 bytes).

Payload gerado agora é **byte-por-byte idêntico** ao fusee-launcher original.

#### 17. Injeção bem-sucedida

```
Detectado: bus 3, device 30
Injeção concluída.
```

Switch bootou Hekate corretamente.

---

## Estado atual dos arquivos

### Modificados

| Arquivo | Mudança |
|---------|---------|
| `fusectl/rcm/injector.py` | Layout corrigido + `_disable_autosuspend()` |
| `tests/test_rcm.py` | Offsets atualizados para layout correto |
| `udev/50-switch-rcm.rules` | Autosuspend disable adicionado |
| `scripts/diag_rcm.sh` | Novo: diagnóstico completo de ambiente USB |
| `scripts/hotplug_inject.py` | Ignora devices stale, espera reconexão |

### Regra udev instalada

```
/etc/udev/rules.d/50-switch-rcm.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="0955", ATTR{idProduct}=="7321", MODE="0666", TAG+="uaccess", ENV{ID_MM_DEVICE_IGNORE}="1", ENV{MTP_NO_PROBE}="1", ATTR{power/autosuspend_delay_ms}="-1", ATTR{power/control}="on"
```

---

## Lições aprendidas

1. **Header RCM não entra no IRAM**: os 680 bytes do comando são consumidos pelo protocolo.
   Todos os offsets de IRAM precisam ser somados a 680 para obter o offset no buffer USB.

2. **USB hubs causam falha com Tegra RCM**: o bootrom tem stack USB minimalista.
   Conexão direta USB-A para USB-C é obrigatória.

3. **Devices RCM ficam stale**: após tentativas falhadas ou tempo ocioso, o bootrom
   para de responder. Reconexão física é necessária.

4. **Autosuspend pode travar transfers**: regra udev com `autosuspend_delay_ms=-1`
   e código defensivo via sysfs previnem o problema.

---

## Referência: protocolo RCM

```
1. Host encontra device (VID=0955, PID=7321)
2. Host lê 16 bytes do bulk IN endpoint (0x81) -- device ID
3. Host envia payload em chunks de 0x1000 via bulk OUT endpoint (0x01):

   Layout no buffer USB (offsets incluem header de 680 bytes):
   - 0x0000: RCM command length (4 bytes LE = 0x30298)
   - 0x0004: NOP sled (676 bytes de zeros)
   - 0x02A8: Intermezzo relocator (124 bytes)
   - 0x0324: Padding zeros (3524 bytes)
   - 0x10E8: User payload parte 1 (até 0x4000 bytes)  [IRAM: 0x40010E40]
   - 0x50E8: Stack spray (0x40010000 x 2160)           [IRAM: 0x40014E40]
   - 0x72A8: User payload parte 2 (restante)            [IRAM: 0x40017000]
   - Final: alinhado a 0x1000

4. Host garante buffer ativo = high (0x40009000) via switch_to_highbuf
5. Host aciona vulnerabilidade: control transfer GET_STATUS com tamanho
   = STACK_END (0x40010000) - 0x40009000 = 0x7000
   (causa memcpy oversized que sobrescreve a stack com stack spray)
6. Device executa o payload e para de responder (control transfer "falha")
```

---

## Comandos úteis para debug

```bash
# Verificar se Switch está conectado
lsusb | grep 0955

# Verificar regra udev
udevadm test --action=add /sys/bus/usb/devices/3-1 2>&1 | grep -E "mtp|MTP|50-switch|69-lib"

# Verificar permissões
ls -la /dev/bus/usb/003/*
getfacl /dev/bus/usb/003/XXX

# Verificar controlador xHCI
ls /sys/bus/pci/drivers/xhci_hcd/*/usb3

# Monitorar eventos USB em tempo real
udevadm monitor --property --subsystem-match=usb

# Injeção com debug completo
LIBUSB_DEBUG=4 .venv/bin/python -m fusectl -v rcm inject <pacote>/bootloader/payloads/fusee.bin 2>&1

# Verificar kernel log durante conexão
journalctl -f | grep -i "usb\|tegra\|0955"

# Verificar processos acessando o device
sudo lsof /dev/bus/usb/003/XXX
sudo fuser -v /dev/bus/usb/003/XXX
```
