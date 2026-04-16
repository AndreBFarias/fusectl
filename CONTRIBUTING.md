# Como Contribuir

Obrigado pelo interesse em contribuir com o fusectl!

## Código de Conduta

Este projeto adota o [Contributor Covenant v2.1](CODE_OF_CONDUCT.md). Ao participar, você concorda em respeitá-lo.

## Configurando o Ambiente

### Requisitos

- Python 3.10+
- Linux (acesso USB requer udev rules)
- Nintendo Switch Erista (opcional, para testes com hardware real)

### Instalação

```bash
git clone https://github.com/AndreBFarias/fusectl.git
cd fusectl
./install.sh
```

### Testes

```bash
pytest tests/ -v
pytest tests/ -v --cov=fusectl
```

## Padrões de Código

### Lint

O projeto usa `ruff` para lint e formatação. Verifique antes de commitar:

```bash
ruff check fusectl/ tests/
ruff format fusectl/ tests/
```

### Commits

Mensagens em português, formato convencional:

```
tipo: descrição imperativa em PT-BR

# Tipos: feat, fix, refactor, docs, test, perf, chore
```

## Regras do Projeto

- **Zero emojis** em código, commits e documentação
- **Acentuação correta** obrigatória em todo texto PT-BR
- **Type hints** em todas as funções novas
- **Sem polling USB em testes** -- mockar dispositivos para CI
- **Regras udev** testadas antes de submeter mudanças

## Submetendo Mudanças

### Antes de Abrir o PR

- [ ] `pytest tests/ -v` passando (139+ testes)
- [ ] `ruff check` e `ruff format --check` passando
- [ ] Zero emojis no código e commits
- [ ] Acentuação correta em textos PT-BR
- [ ] Documentação atualizada (se aplicável)

### Processo de Review

1. Um mantenedor vai revisar seu PR
2. Pode haver solicitações de mudanças
3. Após aprovação, o PR será mergeado
