# DataSUS BI Pro

Dashboard interativo em **Streamlit** para explorar, filtrar, cruzar e baixar bases públicas do **DataSUS** (SIM, SINASC, SIH, SIA, CNES, SINAN, CIHA, PNI) diretamente do FTP oficial, sem precisar baixar tudo manualmente.

## Principais recursos

- **64 bases** organizadas por família (SIM, SINASC, SIH, SIA, CNES, SINAN, CIHA, PNI), com seleção prática em dois passos: escolha a família e depois a base específica.
- **Filtros inteligentes**: UF, município, período (mensal/anual) e intervalo de anos (a partir de 2010).
- **Classificação por CID-10**: por capítulo, grandes grupos ou **CID específico** (busca por código ou nome da doença no catálogo oficial com ~14 mil códigos).
- **Junção entre bases** (record linkage):
  - **Exata** — por chaves comuns (ex.: nº da AIH entre SIH-RD e SIH-SP, CNS do paciente em APAC).
  - **Aproximada (probabilística)** — pareamento por quase-identificadores (município, sexo, nascimento, idade, CEP) com indicadores de qualidade do pareamento.
- **Memória sob controle (DuckDB)**: a ingestão converte cada base para **Parquet em lotes**, com pico de memória proporcional ao lote — não ao tamanho da base. As consultas rodam no **DuckDB** com teto de memória e *spill* em disco, sem `pd.concat` de bases inteiras. É o que evita o *Out-Of-Memory* em bases grandes como o SIA.
- **Cache local** em Parquet para acelerar consultas repetidas.

## Requisitos

- Python 3.10+
- Dependências em [`requirements.txt`](requirements.txt)

## Como executar localmente

```powershell
# 1. Clonar o repositório
git clone https://github.com/kelserkock-lang/datasus-bi.git
cd datasus-bi

# 2. (Opcional, recomendado) criar um ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Rodar o app
streamlit run app.py
```

O navegador abre automaticamente em `http://localhost:8501`.

No Windows também é possível iniciar pelo atalho [`DataSUS_BI.bat`](DataSUS_BI.bat).

## Assistente de linha de comando (terminal)

Se você prefere o terminal, use o assistente — ele guia a seleção de **bases,
período, regiões e CID** com menus de setas e busca:

```powershell
python datasus_cli.py          # assistente interativo
```

No Windows, o atalho [`CLI.bat`](CLI.bat) faz o mesmo (e usa a `.venv` se existir).

Cada etapa é uma pergunta simples:

| Passo | Pergunta | Como responder |
|---|---|---|
| 1 | Quais bancos? | família (SIM, SIH, SIA...) → bases específicas |
| 2 | Onde? | uma ou várias UFs; município opcional (busca do IBGE) |
| 3 | Qual período? | ano inicial/final; mês (só para bases mensais) |
| 4 | Filtrar por CID? | capítulos, morbidades prontas e/ou busca por nome da doença |
| 5 | Quais variáveis? | todas, ou escolha uma a uma (com descrição) |
| 6 | Formato e destino | CSV, Parquet ou Excel |
| 7 | Memória | teto de RAM e tamanho do lote |

### Modo não-interativo (automação/scripts)

```powershell
python datasus_cli.py --listar                  # ver bases, morbidades, capítulos e UFs

python datasus_cli.py --base SIH-RD --uf SC --ano-inicio 2020 --ano-fim 2024

python datasus_cli.py --base SIM-DO,SINASC --uf SC,PR --ano-inicio 2021 \
                      --ano-fim 2023 --morbidades "Diabetes mellitus" --formato parquet

python datasus_cli.py --base SIH-RD --uf SC --ano-inicio 2022 --capitulos IX \
                      --cids I21 --colunas N_AIH,DIAG_PRINC,VAL_TOT
```

Arquivos são gravados em `saidas_cli/` por padrão (use `--saida` para mudar).

| Argumento | Descrição |
|---|---|
| `--base` | Base(s) separadas por vírgula (ex.: `SIH-RD,SIM-DO`) |
| `--uf` | UF(s) separadas por vírgula (ex.: `SC,PR`) |
| `--municipio` | Código IBGE de 6 dígitos (exige uma única `--uf`) |
| `--ano-inicio` / `--ano-fim` | Período |
| `--mes` | `01`..`12` (só bases mensais; padrão: todos) |
| `--capitulos` | Capítulos CID-10 (ex.: `IX,X`) |
| `--morbidades` | Nomes exatos do catálogo (ver `--listar`) |
| `--cids` | Códigos CID (ex.: `I21,J45`) |
| `--colunas` | Variáveis (padrão: todas) |
| `--formato` | `csv`, `parquet` ou `xlsx` |
| `--saida` / `--memoria` / `--lote` | Destino e controle de memória |

## Estrutura do projeto

| Arquivo | Descrição |
|---|---|
| `app.py` | Interface Streamlit (filtros, abas, visualizações). |
| `datasus_cli.py` | **Assistente de linha de comando** (menus interativos) — alternativa ao Streamlit. |
| `data_ingestion.py` | Catálogo de sistemas, download do FTP e conversão `.dbc` → `.dbf`. |
| `datasus_engine.py` | **Motor de memória controlada**: staging Parquet em lotes + consultas DuckDB. |
| `metadata_catalog.py` | Metadados dos campos e catálogo de chaves de junção. |
| `cid_catalog.py` | Catálogo CID-10, capítulos, morbididades e filtros por CID. |
| `patient_linkage.py` | Pareamento de registros do mesmo paciente (exato e probabilístico). |
| `cid10.csv` | Tabela oficial CID-10 (código + descrição). |

## Observações

- Os dados baixados (`data/`, arquivos `.dbc`/`.dbf`/`.parquet`) **não** são versionados — são grandes e regeneráveis a partir do FTP.
- Downloads de estados inteiros por períodos longos podem ser pesados; use os filtros (município, período, CID).
- **Memória:** cada base baixada vira um Parquet em `data/staging/`. O tamanho do lote (padrão 50.000 registros) é o que controla o pico de RAM; o DuckDB recebe teto de memória (padrão 1 GB) e usa `data/_duckdb_tmp/` para *spill* em disco. Se ainda faltar RAM, reduza o lote ou o teto.
- **Ordem das linhas:** sem filtros, a ordem do arquivo original é preservada. Com filtros (município/CID), o DuckDB pode devolver **as mesmas linhas em ordem diferente** — o conjunto de dados é idêntico. Se a ordem importar, ordene o DataFrame resultante.
- O staging é regenerável e pode ser apagado a qualquer momento (`datasus_engine.clear_staging()`).

### Particularidades de algumas bases (verificadas no FTP)

| Base | Particularidade |
|---|---|
| **SINAN** (34 agravos) | Os arquivos são **nacionais** (`DENGBR17.dbc`), não separados por UF. A UF escolhida é aplicada **sobre os dados** (`SG_UF_NOT`), então o resultado sai filtrado corretamente — mas o download é sempre do Brasil inteiro. Cobertura por ano (2 dígitos). |
| **PNI** | São dois conjuntos: `PNI (Doses Aplicadas)` e `PNI (Cobertura Vacinal)`. Arquivos **anuais** já em `.DBF` (sem descompactação), agregados por município/faixa/imunobiológico — **não** são registros individuais de vacinação. Cobertura: 1994–1999 e 2000–2019; o esquema de campos varia conforme o ano. |
| **SIA (grupos APAC)** | A disponibilidade varia muito por UF e período (ex.: Nefrologia tem SC só até 2014; Amputado começa em 2019). Períodos sem dados retornam vazio, sem erro. |
| **SINASC** | O diretório oficial é `1996_/Dados/DNRES/` (o antigo `NOVOS/DNRES/` não existe mais). |

- Dados de pacientes no DataSUS são anonimizados/criptografados; o pareamento probabilístico é **aproximado** e deve ser interpretado com cautela.

## Fonte dos dados

[DataSUS — Ministério da Saúde](https://datasus.saude.gov.br/) · FTP: `ftp.datasus.gov.br`
