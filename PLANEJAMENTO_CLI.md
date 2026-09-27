# Planejamento: Interface CLI Interativa — DataSUS BI

> **STATUS: IMPLEMENTADO** ✅
>
> Veja `datasus_cli.py` (assistente) e `CLI.bat` (atalho Windows).
>
> Duas correções foram feitas em relação a este documento original:
>
> 1. **Etapa 1 estava incorreta** — as "famílias" listadas (Epidemiológico,
>    Hospitalar/Ambulatorial, Assistencial, Outros) não correspondem ao código.
>    O agrupamento real é `SYSTEM_FAMILIES`: SIM, SINASC, SIH, SIA, CNES,
>    SINAN, CIHA e PNI.
> 2. **A mitigação de memória não procedia** — o documento afirmava que o
>    "modo streaming já implementado" resolvia bases grandes, mas aquele modo
>    terminava em `pd.concat()` e continuava estourando a RAM. O problema só foi
>    resolvido com o `datasus_engine.py` (staging em Parquet + DuckDB), que agora
>    é a base da CLI.
>
> Além disso, a CLI ficou em um arquivo único na raiz (`datasus_cli.py`) em vez
> do diretório `datasus_cli/`, porque o projeto é plano e o assistente importa os
> módulos da raiz — um subdiretório exigiria manipulação de `sys.path` sem ganho.
> Também foi adicionado suporte a **múltiplas UFs** (`--uf SC,PR`) e um
> **modo não-interativo** por flags, que não estavam previstos aqui.

## Visão Geral

Criar uma interface de linha de comando (CLI) interativa para o DataSUS BI, utilizing checkboxes e menus para guiar o usuário na seleção de parâmetros, variáveis e geração do banco de dados.

**Objetivo:** Oferecer uma alternativa ao Streamlit para usuários que preferem trabalhar no terminal, com interface amigável via prompts interativos.

---

## Viabilidade

**Classificação: ALTA** ✅

A arquitetura atual já separa lógica de dados da interface Streamlit:
- `data_ingestion.py` → Funções de download e processamento
- `metadata_catalog.py` → Metadados e chaves de join
- `cid_catalog.py` → Catálogo CID-10 e filtros
- `patient_linkage.py` → Ligação de registros

Todas essas funções podem ser reutilizadas na nova CLI sem modificações.

---

## Estrutura de Diretórios

```
datasus_bi/
├── app.py                    ← Streamlit (INALTERADO)
├── data_ingestion.py         ← INALTERADO
├── metadata_catalog.py       ← INALTERADO
├── cid_catalog.py            ← INALTERADO
├── patient_linkage.py        ← INALTERADO
│
└── datasus_cli/              ← NOVO DIRETÓRIO (separado)
    ├── cli.py                ← Entry point principal (~500 linhas)
    ├── requirements_cli.txt  ← Dependências específicas da CLI
    └── CLI.bat               ← Atalho Windows para inicialização
```

**Princípio:** O diretório `datasus_cli/` é autocontido e não modifica nenhum arquivo existente.

---

## Tecnologias

| Componente | Tecnologia | Justificativa |
|------------|------------|---------------|
| Interface | `questionary` | Checkboxes e menus interativos no terminal |
| Dados | Módulos existentes | Reutilização total da lógica atual |
| Exportação | pandas + openpyxl | CSV, Parquet, Excel (já disponível) |

### Dependência Nova

```txt
questionary>=2.0.0
```

---

## Fluxo de Trabalho (10 Etapas)

### Etapa 1: Família de Dados
- **Tipo:** Checkbox (múltipla escolha)
- **Opções:** SIM (Mortalidade), SINASC (Nascidos Vivos), SIH (Internações),
  SIA (Produção Ambulatorial), CNES (Estabelecimentos), SINAN (Agravos),
  CIHA (Internação/Alta), PNI (Imunizações)
- **Função reutilizada:** `get_systems_by_family()` + `SYSTEM_FAMILIES`
- **CORRIGIDO:** a versão original deste documento listava "Epidemiológico,
  Hospitalar/Ambulatorial, Assistencial, Outros", que não existe no código.

### Etapa 2: Sistemas Específicos
- **Tipo:** Checkbox (múltipla escolha)
- **Opções:** Filtradas pela família selecionada (ex: SIM-DO, SINASC, SIH-RD)
- **Função reutilizada:** `SYSTEMS_CATALOG`

### Etapa 3: Unidade Federativa (UF)
- **Tipo:** Checkbox (múltipla escolha)
- **Opções:** 27 UFs do Brasil (AC, AL, AP, ..., TO)
- **Constante:** Lista fixa de UFs

### Etapa 4: Município (Opcional)
- **Tipo:** Texto com busca
- **Comportamento:** Usuário digita nome ou código IBGE; lista filtrada em tempo real
- **API:** IBGE (já utilizada no Streamlit)
- **Pode ser pulado** para baixar estado inteiro

### Etapa 5: Período
- **Tipo:** Texto
- **Formato:** "2020-2024" ou "2022" (ano único)
- **Validação:** Ano inicial ≤ ano final; ano ≤ ano atual

### Etapa 6: Meses (se sistema mensal)
- **Tipo:** Checkbox
- **Opções:** Todos, Jan, Fev, Mar, ..., Dez
- **Condicional:** Apenas aparece para sistemas com `type: "monthly"` (SIH, SIA, CNES)

### Etapa 7: Capítulos CID-10
- **Tipo:** Checkbox (múltipla escolha)
- **Opções:** 22 capítulos oficiais da CID-10 (I-XXII)
- **Função reutilizada:** `CID10_CHAPTERS`

### Etapa 8: Morbidades (Refino)
- **Tipo:** Checkbox (múltipla escolha)
- **Opções:** 35+ morbidades pré-mapeadas (Diabetes, COVID-19, AVC, etc.)
- **Condicional:** Apenas morbidades dos capítulos selecionados na Etapa 7
- **Função reutilizada:** `MORBIDITIES`

### Etapa 9: Variáveis/Colunas
- **Tipo:** Checkbox com descrições
- **Opções:** Colunas do metadado com nome, tipo e descrição
- **Exemplo:** `☑ DTOBITO (C8) - Data do óbito (ddmmaaaa)`
- **Função reutilizada:** `get_metadata_for_system()`

### Etapa 10: Exportação
- **Tipo:** Seleção única (select)
- **Opções:** CSV, Parquet, Excel
- **Ação:** Gera arquivo na pasta `data/` com nome descritivo

---

## Interface Visual (Exemplo)

```
╔══════════════════════════════════════════════════════════════╗
║  DATAUS CLI — Gerador de Banco de Dados                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Passo 1/10: Selecione a(s) família(s) de dados             ║
║                                                              ║
║  ┌─ Epidemiológico (SIM, SINASC, SINAN)                     ║
║  │  Hospitalar/Ambulatorial (SIH, SIA, CNES)                ║
║  │  Assistencial (CIHA)                                      ║
║  │  Outros (PNI)                                             ║
║  └─                                                          ║
║                                                              ║
║  [↑↓] navegar  [ESPACO] marcar/desmarcar  [ENTER] confirmar ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Comandos de Execução

```bash
# Navegar até o diretório da CLI
cd datasus_cli

# Instalar dependências (primeira vez)
pip install -r requirements_cli.txt

# Executar interface interativa
python cli.py

# Executar com argumentos (pular etapas)
python cli.py --uf SC --ano-inicio 2020 --ano-fim 2024 --sistema SIM-DO --output csv

# Windows: usar atalho
CLI.bat
```

---

## Argumentos CLI (Opcionais)

| Argumento | Descrição | Exemplo |
|-----------|-----------|---------|
| `--uf` | UF(s) separadas por vírgula | `--uf SC,PR,SP` |
| `--ano-inicio` | Ano inicial | `--ano-inicio 2020` |
| `--ano-fim` | Ano final | `--ano-fim 2024` |
| `--sistema` | Sistema(s) DataSUS | `--sistema SIM-DO,SIH-RD` |
| `--municipio` | Código IBGE do município | `--municipio 4205407` |
| `--cid` | Códigos CID-10 | `--cid I21,I22` |
| `--output` | Formato de saída | `--output csv` |
| `--meses` | Meses (1-12) | `--meses 1,6,12` |

---

## Funções Reutilizadas

| Módulo | Função | Uso na CLI |
|--------|--------|------------|
| `data_ingestion` | `get_systems_by_family()` | Etapa 1 |
| `data_ingestion` | `get_systems_by_category()` | Etapa 2 |
| `data_ingestion` | `load_full_datasus()` | Download final |
| `data_ingestion` | `SYSTEMS_CATALOG` | Listar sistemas |
| `metadata_catalog` | `get_metadata_for_system()` | Etapa 9 |
| `metadata_catalog` | `get_join_suggestions()` | Joins opcionais |
| `cid_catalog` | `CID10_CHAPTERS` | Etapa 7 |
| `cid_catalog` | `MORBIDITIES` | Etapa 8 |
| `cid_catalog` | `build_cid_filter()` | Construir filtro |
| `cid_catalog` | `search_cid10()` | Busca interativa |

---

## Saída Gerada

### Estrutura do Arquivo de Saída

```
data/
└── {SISTEMA}_{UF}_{ANO_INICIO}-{ANO_FIM}_{MESES}_{MUNICIPIO}.ext
```

### Exemplos

```
data/SIM-DO_SC_2020-2024_Todos_Todos.parquet
data/SIH-RD_SC_2020-2024_01_12_Florianopolis.csv
data/SIA-PA_PR_2022_Todos_Todos.xlsx
```

---

## Vantagens da Abordagem

1. **Zero impacto** no Streamlit existente
2. **Reutilização total** da lógica de dados
3. **Independência** — pode ser distribuída separadamente
4. **Flexibilidade** — argumentos CLI para automação
5. **Portabilidade** — funciona em qualquer terminal

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| `questionary` pode não funcionar em todos os terminais | Fallback automático para menus numerados via `input()` (implementado em `_num_fallback`) |
| Downloads grandes podem parecer travados | Barra de progresso na CLI + mensagens por arquivo |
| Memória insuficiente | **RESOLVIDO** por `datasus_engine.py`: leitura em lotes + Parquet + DuckDB com `memory_limit` e spill em disco. A CLI expõe `--memoria` e `--lote`. (A mitigação original citada aqui — "modo streaming já implementado" — era incorreta: aquele caminho terminava em `pd.concat`.) |

---

## Próximos Passos

1. Criar diretório `datasus_cli/`
2. Criar `requirements_cli.txt`
3. Implementar `cli.py` com as 10 etapas
4. Criar `CLI.bat` para Windows
5. Testar fluxo completo
