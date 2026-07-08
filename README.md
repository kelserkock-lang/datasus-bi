# DataSUS BI Pro

Dashboard interativo em **Streamlit** para explorar, filtrar, cruzar e baixar bases públicas do **DataSUS** (SIM, SINASC, SIH, SIA, CNES, SINAN, CIHA, PNI) diretamente do FTP oficial, sem precisar baixar tudo manualmente.

## Principais recursos

- **63 bases** organizadas por família (SIM, SINASC, SIH, SIA, CNES, SINAN, CIHA, PNI), com seleção prática em dois passos: escolha a família e depois a base específica.
- **Filtros inteligentes**: UF, município, período (mensal/anual) e intervalo de anos (a partir de 2010).
- **Classificação por CID-10**: por capítulo, grandes grupos ou **CID específico** (busca por código ou nome da doença no catálogo oficial com ~14 mil códigos).
- **Junção entre bases** (record linkage):
  - **Exata** — por chaves comuns (ex.: nº da AIH entre SIH-RD e SIH-SP, CNS do paciente em APAC).
  - **Aproximada (probabilística)** — pareamento por quase-identificadores (município, sexo, nascimento, idade, CEP) com indicadores de qualidade do pareamento.
- **Modo econômico de memória**: leitura em streaming com filtros aplicados durante a ingestão, para bases grandes.
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

## Estrutura do projeto

| Arquivo | Descrição |
|---|---|
| `app.py` | Interface Streamlit (filtros, abas, visualizações). |
| `data_ingestion.py` | Catálogo de sistemas, download do FTP e conversão `.dbc` → `.dbf`. |
| `metadata_catalog.py` | Metadados dos campos e catálogo de chaves de junção. |
| `cid_catalog.py` | Catálogo CID-10, capítulos, morbididades e filtros por CID. |
| `patient_linkage.py` | Pareamento de registros do mesmo paciente (exato e probabilístico). |
| `cid10.csv` | Tabela oficial CID-10 (código + descrição). |

## Observações

- Os dados baixados (`data/`, arquivos `.dbc`/`.dbf`/`.parquet`) **não** são versionados — são grandes e regeneráveis a partir do FTP.
- Downloads de estados inteiros por períodos longos podem ser pesados; use os filtros (município, período, CID) e o modo econômico de memória.
- Dados de pacientes no DataSUS são anonimizados/criptografados; o pareamento probabilístico é **aproximado** e deve ser interpretado com cautela.

## Fonte dos dados

[DataSUS — Ministério da Saúde](https://datasus.saude.gov.br/) · FTP: `ftp.datasus.gov.br`
