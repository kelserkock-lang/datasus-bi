# Custo-Efetividade — Doenças Respiratórias Sazonais em SC

Subprojeto de análise de custo-efetividade de intervenções contra Influenza,
COVID-19 e VSR em Santa Catarina, usando bases do DataSUS.

## Etapa 1 — Coleta de dados

| Base | O que fornece | Fonte | Script |
|---|---|---|---|
| `SIH-RD` | Custo total (`VAL_TOT`), custo de UTI (`VAL_UTI`), internações, permanência (`DIAS_PERM`), uso de UTI (`MARCA_UTI`), óbito hospitalar (`MORTE`) | FTP DataSUS | `coleta.py` |
| `SIM-DO` | Óbitos por causa básica (`CAUSABAS`) | FTP DataSUS | `coleta.py` |
| `SIVEP-Gripe` | Casos graves (SRAG) por vírus, faixa etária, UTI e desfecho (óbito) | OpenDataSUS (Parquet) | `sivep_gripe.py` |

### CIDs-alvo (SIH/SIM)

- Influenza: `J09`–`J11`
- Pneumonias: `J12`–`J18`
- COVID-19: `U07.1`

### Vírus (SIVEP-Gripe)

Classificação por PCR/antígeno com fallback na classificação final
(`CLASSI_FIN`): SARS-CoV-2/COVID-19, Influenza, VSR, outros vírus
respiratórios, não especificado.

### Como rodar

```powershell
# da raiz do projeto
python custo_efetividade/coleta.py                 # SIH + SIM, janela 2020..2024
python custo_efetividade/sivep_gripe.py            # SRAG (SIVEP-Gripe), 2020..2024
python custo_efetividade/modelo.py                 # modelo de custo-efetividade (8.000 iterações)
python custo_efetividade/relatorio.py              # gráficos + relatório Word
python custo_efetividade/coleta.py 2019 2025       # janela customizada
python custo_efetividade/sivep_gripe.py 2019 2025  # janela customizada

# Ajuste de memória (bases grandes / PC com pouca RAM)
python custo_efetividade/coleta.py 2019 2025 --memoria 512MB --lote 10000
```

**Memória:** a coleta usa o motor DuckDB do projeto, que lê os `.dbc` em **lotes**
e grava Parquet em `custo_efetividade/data/staging/` (nenhuma base inteira fica na
RAM). `--memoria` define o teto de RAM do motor (padrão `1GB`; ao atingir, ele
derrama em disco) e `--lote` define quantos registros são processados por vez
(padrão `50000`) — **esse é o parâmetro que controla o pico de memória**. Em PCs
com pouca RAM, use `--lote 10000` ou `--lote 5000`.

### Saídas (`saida/`)

- `custo_efetividade_sc.xlsx` — abas `SIH_internacoes`, `SIM_obitos`,
  `Probabilidades`, `Resumo_faixa_etaria`, `Metadados`.
- `sivep_gripe_sc.xlsx` — abas `Agregado`, `Resumo_faixa_virus`, `Metadados`.
- `modelo_sc.xlsx` — abas `Resultados`, `PSA_resumo`, `Tornado`, `CEAC`.
- `relatorio_custo_efetividade_srag_sc.docx` — relatório completo (texto + tabelas + gráficos).
- `graficos/` — CEAC, plano de custo-efetividade, tornado e ICER por QALY.
- CSVs equivalentes (com `utf-8-sig`, abrem direto no Excel).

### Notas técnicas

- **Idade**:
  - SIH-RD: `IDADE` em anos direto.
  - SIM-DO: `IDADE` codificado (1º dígito = unidade: 4=anos).
  - SIVEP-Gripe: `NU_IDADE_N` = valor; `TP_IDADE` = unidade (3=anos).
- **Desfecho**: SIH `MORTE` (óbito intra-hospitalar) ≠ SIM `CAUSABAS`
  (causa básica populacional) ≠ SIVEP `EVOLUCAO=2` (óbito por SRAG).
  Use cada um na sua dimensão (custo/gravidade vs. mortalidade vs. efetividade).
- Parâmetros de eficácia vacinal e custo da dose vêm da literatura/tabelas do MS
  e são entradas do modelo (etapa 3).

## Etapa 3 — Modelo de custo-efetividade (`modelo.py`)

Árvore de decisão "Vacinar vs. Não vacinar" por faixa etária e por vírus,
com Monte Carlo (análise de sensibilidade probabilística).

- **Custos** (SIH): custo médio da internação por faixa etária.
- **Efetividade** (SIVEP-Gripe): casos de SRAG evitados, óbitos evitados, QALYs
  (óbitos × expectativa de vida restante).
- **Parâmetros editáveis** (no topo do `modelo.py`): população, cobertura,
  custo da dose, eficácia (VE) contra hospitalização, expectativa de vida e
  limiar de disposição a pagar (R$ por QALY).

**Caveats importantes**: o `VAL_TOT` do SIH é reembolso AIH (não o custo
socioeconômico total da internação) e os valores de VE/custo de dose são
placeholders de literatura. Ajuste-os para refinar as conclusões.
