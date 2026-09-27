"""
Etapa 1 — Coleta e agregação de dados para o modelo de custo-efetividade
de intervenções contra doenças respiratórias sazonais (Influenza, COVID-19
e VSR) em Santa Catarina.

Fontes (reaproveitando o data_ingestion.py do projeto DataSUS BI Pro):
  - SIH/SUS (SIH-RD) -> custos hospitalares, internações, UTI, permanência, óbito
  - SIM (SIM-DO)     -> mortalidade por causa básica (CID-10)

Saídas (pasta `saida/`):
  - custo_efetividade_sc.xlsx  (planilha Excel com 5 abas)
  - sih_internacoes.csv        (agregado mensal do SIH)
  - sim_obitos.csv             (agregado mensal do SIM)
  - probabilidades.csv         (parâmetros p/ árvore de decisão)
  - resumo_faixa_etaria.csv    (resumo por faixa etária)

Uso (a partir da raiz do projeto):
  python custo_efetividade/coleta.py              # janela padrão 2020..2024
  python custo_efetividade/coleta.py 2019 2025    # janela customizada
"""

import argparse
import datetime
import os
import sys

# Permite importar os módulos do projeto pai (data_ingestion, cid_catalog)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Trabalha dentro da própria pasta: cache e saídas ficam isolados nesta subpasta
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

import pandas as pd  # noqa: E402

from data_ingestion import load_full_datasus  # noqa: E402
from cid_catalog import build_cid_filter  # noqa: E402

# ------------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------------
UF = "SC"

ANO_INICIO = 2020
ANO_FIM = 2024

# CIDs-alvo (prefixos CID-10, sem ponto/espaço)
CIDS_ALVO = [
    "J09", "J10", "J11",                                      # Influenza (gripe)
    "J12", "J13", "J14", "J15", "J16", "J17", "J18",          # Pneumonias
    "U071",                                                    # COVID-19 (U07.1)
]

# Colunas mantidas em cada base
SIH_COLS = [
    "N_AIH", "DT_INTER", "DT_SAIDA", "ANO_CMPT", "MES_CMPT",
    "IDADE", "SEXO", "MUNIC_RES", "DIAG_PRINC", "DIAG_SECUN",
    "VAL_TOT", "VAL_UTI", "VAL_SH", "VAL_SP",
    "DIAS_PERM", "MARCA_UTI", "UTI_MES_TO", "MORTE",
]
SIM_COLS = ["DTOBITO", "IDADE", "SEXO", "CODMUNRES", "CAUSABAS"]

NUM_COLS_SIH = ["VAL_TOT", "VAL_UTI", "VAL_SH", "VAL_SP",
                "DIAS_PERM", "MARCA_UTI", "UTI_MES_TO", "MORTE"]

SAIDA_DIR = os.path.join(PROJECT_DIR, "saida")
os.makedirs(SAIDA_DIR, exist_ok=True)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def _normalizar_cid(codigo):
    """Normaliza um CID: maiúsculo, sem ponto/espaço."""
    if codigo is None:
        return ""
    return str(codigo).strip().upper().replace(".", "").replace(" ", "")


def grupo_cid(princ, sec=None):
    """Classifica um registro respiratório em Influenza, Pneumonia ou COVID-19."""
    for c in (princ, sec):
        c = _normalizar_cid(c)
        if c.startswith(("J09", "J10", "J11")):
            return "Influenza (J09-J11)"
        if c.startswith(("J12", "J13", "J14", "J15", "J16", "J17", "J18")):
            return "Pneumonia (J12-J18)"
        if c.startswith("U07"):
            return "COVID-19 (U07.1)"
    return "Outro"


def decodificar_idade_sih(valor):
    """
    SIH-RD: o campo IDADE já vem em anos (0 = menor de 1 ano).
    """
    try:
        v = int(float(valor))
    except (TypeError, ValueError):
        return None
    return v if v >= 0 else None


def decodificar_idade_sim(valor):
    """
    SIM-DO: o campo IDADE é codificado — o 1º dígito é a unidade:
      1 = horas, 2 = dias, 3 = meses, 4 = anos, 5 = 100+ anos.
    Retorna a idade em anos (menores de 1 ano -> 0) ou None.
    """
    try:
        v = int(float(valor))
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    s = str(v)
    unidade = int(s[0])
    restante = int(s[1:]) if len(s) > 1 else 0
    if unidade in (1, 2, 3):   # horas, dias ou meses -> menor de 1 ano
        return 0
    if unidade == 4:            # anos
        return restante
    if unidade == 5:            # 100+ anos
        return 100 + restante
    return None


def faixa_etaria(anos):
    if anos is None:
        return "Ignorado"
    if anos < 15:
        return "Criancas (0-14)"
    if anos < 60:
        return "Adultos (15-59)"
    return "Idosos (60+)"


def _dt_parts(v):
    """Extrai (ano, mês) de uma data string aaaammdd."""
    s = str(v).strip()
    if len(s) >= 8:
        return s[:4], s[4:6]
    return "", ""


def _progresso():
    def cb(frac, msg):
        print(f"    [{frac * 100:5.1f}%] {msg}", flush=True)
    return cb


# ------------------------------------------------------------------
# COLETA E PREPARO
# ------------------------------------------------------------------
def coletar_sih(ano_inicio, ano_fim, cid_filter, memory_limit=None, batch_size=None):
    print(f"\n=== Coleta SIH-RD {UF} {ano_inicio}..{ano_fim} ===", flush=True)
    df = load_full_datasus(
        "SIH-RD", UF, ano_inicio, ano_fim,
        month="Todos", city_code="",
        columns_to_keep=SIH_COLS, cid_filter=cid_filter,
        memory_efficient=True, progress_callback=_progresso(),
        memory_limit=memory_limit, batch_size=batch_size,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()

    # Idade e faixa etária (SIH: idade em anos direto)
    if "IDADE" in df.columns:
        df["idade_anos"] = df["IDADE"].apply(decodificar_idade_sih)
    else:
        df["idade_anos"] = None
    df["faixa_etaria"] = df["idade_anos"].apply(faixa_etaria)

    # Ano/mês (preferência: data de internação; fallback: competência)
    if "DT_INTER" in df.columns:
        partes = df["DT_INTER"].astype(str).apply(lambda v: pd.Series(_dt_parts(v)))
        df["ano"] = partes[0]
        df["mes"] = partes[1]
    else:
        df["ano"] = ""
        df["mes"] = ""
    vazio_ano = df["ano"].eq("")
    if "ANO_CMPT" in df.columns and vazio_ano.any():
        df.loc[vazio_ano, "ano"] = df.loc[vazio_ano, "ANO_CMPT"].astype(str).str.zfill(4)
    vazio_mes = df["mes"].eq("")
    if "MES_CMPT" in df.columns and vazio_mes.any():
        df.loc[vazio_mes, "mes"] = df.loc[vazio_mes, "MES_CMPT"].astype(str).str.zfill(2)

    # Grupo CID (diagnóstico principal e secundário)
    df["grupo_cid"] = df.apply(
        lambda r: grupo_cid(r.get("DIAG_PRINC"), r.get("DIAG_SECUN")), axis=1
    )

    # Coerção numérica
    for c in NUM_COLS_SIH:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def coletar_sim(ano_inicio, ano_fim, cid_filter, memory_limit=None, batch_size=None):
    print(f"\n=== Coleta SIM-DO {UF} {ano_inicio}..{ano_fim} ===", flush=True)
    df = load_full_datasus(
        "SIM-DO", UF, ano_inicio, ano_fim,
        columns_to_keep=SIM_COLS, cid_filter=cid_filter,
        memory_efficient=True, progress_callback=_progresso(),
        memory_limit=memory_limit, batch_size=batch_size,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()

    # Idade e faixa etária (SIM: idade codificada com unidade no 1º dígito)
    if "IDADE" in df.columns:
        df["idade_anos"] = df["IDADE"].apply(decodificar_idade_sim)
    else:
        df["idade_anos"] = None
    df["faixa_etaria"] = df["idade_anos"].apply(faixa_etaria)

    if "DTOBITO" in df.columns:
        partes = df["DTOBITO"].astype(str).apply(lambda v: pd.Series(_dt_parts(v)))
        df["ano"] = partes[0]
        df["mes"] = partes[1]
    else:
        df["ano"] = ""
        df["mes"] = ""

    df["grupo_cid"] = df["CAUSABAS"].apply(lambda c: grupo_cid(c))
    return df


# ------------------------------------------------------------------
# AGREGAÇÃO
# ------------------------------------------------------------------
def agregar_sih(df):
    cols = ["ano", "mes", "faixa_etaria", "grupo_cid", "internacoes",
            "custo_total", "custo_uti", "permanencia_media",
            "internacoes_uti", "obitos_hospitalares", "custo_medio"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = df.groupby(["ano", "mes", "faixa_etaria", "grupo_cid"], dropna=False).agg(
        internacoes=("N_AIH", "count"),
        custo_total=("VAL_TOT", "sum"),
        custo_uti=("VAL_UTI", "sum"),
        permanencia_media=("DIAS_PERM", "mean"),
        internacoes_uti=("MARCA_UTI", lambda s: (s.eq(1)).sum()),
        obitos_hospitalares=("MORTE", lambda s: (s.eq(1)).sum()),
    ).reset_index()
    g["custo_medio"] = g["custo_total"] / g["internacoes"].replace(0, pd.NA)
    return g[cols]


def agregar_sim(df):
    cols = ["ano", "mes", "faixa_etaria", "grupo_cid", "obitos"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = df.groupby(["ano", "mes", "faixa_etaria", "grupo_cid"], dropna=False).agg(
        obitos=("CAUSABAS", "count")
    ).reset_index()
    return g[cols]


def resumos(sih_g, sim_g):
    if sih_g.empty:
        resumo = pd.DataFrame(columns=["faixa_etaria"])
        prob = pd.DataFrame(columns=["faixa_etaria", "grupo_cid"])
    else:
        resumo = sih_g.groupby("faixa_etaria", dropna=False).agg(
            internacoes=("internacoes", "sum"),
            custo_total=("custo_total", "sum"),
            custo_uti=("custo_uti", "sum"),
            permanencia_media=("permanencia_media", "mean"),
            internacoes_uti=("internacoes_uti", "sum"),
            obitos_hospitalares=("obitos_hospitalares", "sum"),
        ).reset_index()
        resumo["custo_medio_internacao"] = resumo["custo_total"] / resumo["internacoes"].replace(0, pd.NA)

        prob = sih_g.groupby(["faixa_etaria", "grupo_cid"], dropna=False).agg(
            internacoes=("internacoes", "sum"),
            internacoes_uti=("internacoes_uti", "sum"),
            obitos_hospitalares=("obitos_hospitalares", "sum"),
            custo_total=("custo_total", "sum"),
            permanencia_media=("permanencia_media", "mean"),
        ).reset_index()
        prob["p_uti"] = prob["internacoes_uti"] / prob["internacoes"].replace(0, pd.NA)
        prob["p_obito_hospitalar"] = prob["obitos_hospitalares"] / prob["internacoes"].replace(0, pd.NA)
        prob["custo_medio_internacao"] = prob["custo_total"] / prob["internacoes"].replace(0, pd.NA)

    if not sim_g.empty:
        sim_por_faixa = sim_g.groupby("faixa_etaria", dropna=False)["obitos"].sum().reset_index()
        if "obitos_sim" not in resumo.columns:
            resumo = resumo.merge(sim_por_faixa.rename(columns={"obitos": "obitos_sim"}),
                                  on="faixa_etaria", how="left")
        sim_por_grupo = sim_g.groupby(["faixa_etaria", "grupo_cid"], dropna=False)["obitos"].sum().reset_index()
        prob = prob.merge(sim_por_grupo.rename(columns={"obitos": "obitos_sim"}),
                          on=["faixa_etaria", "grupo_cid"], how="left")

    return resumo, prob


# ------------------------------------------------------------------
# EXPORTAÇÃO
# ------------------------------------------------------------------
def exportar(sih_g, sim_g, prob, resumo, ano_inicio, ano_fim):
    metadados = pd.DataFrame({
        "Campo": [
            "Data de geração", "UF", "Janela de coleta", "CIDs-alvo",
            "Fontes", "Decodificação de idade",
            "Observação (lacuna conhecida)",
        ],
        "Valor": [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            UF, f"{ano_inicio}..{ano_fim}", "; ".join(CIDS_ALVO),
            "SIH/SUS (SIH-RD) e SIM (SIM-DO) via FTP DataSUS",
            "SIH: IDADE em anos direto; SIM: 1º dígito do IDADE = unidade (4=anos, 5=100+ anos)",
            "SIVEP-Gripe (SRAG) coletado em separado por sivep_gripe.py (OpenDataSUS).",
        ],
    })

    tabelas = {
        "sih_internacoes": sih_g,
        "sim_obitos": sim_g,
        "probabilidades": prob,
        "resumo_faixa_etaria": resumo,
    }
    for nome, df in tabelas.items():
        df.to_csv(os.path.join(SAIDA_DIR, f"{nome}.csv"), index=False, encoding="utf-8-sig")

    xlsx_path = os.path.join(SAIDA_DIR, "custo_efetividade_sc.xlsx")
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            sih_g.to_excel(writer, sheet_name="SIH_internacoes", index=False)
            sim_g.to_excel(writer, sheet_name="SIM_obitos", index=False)
            prob.to_excel(writer, sheet_name="Probabilidades", index=False)
            resumo.to_excel(writer, sheet_name="Resumo_faixa_etaria", index=False)
            metadados.to_excel(writer, sheet_name="Metadados", index=False)
        print(f"\nPlanilha Excel gerada: {xlsx_path}", flush=True)
    except ImportError:
        print("\n(Aviso) openpyxl não instalado — foram gerados apenas os CSVs.", flush=True)
        print("Instale com: pip install openpyxl", flush=True)

    print("\nArquivos gerados em:", SAIDA_DIR, flush=True)
    for nome in sorted(os.listdir(SAIDA_DIR)):
        print("  -", nome, flush=True)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Coleta dados respiratórios SIH+SIM de SC.")
    ap.add_argument("ano_inicio", nargs="?", type=int, default=ANO_INICIO)
    ap.add_argument("ano_fim", nargs="?", type=int, default=ANO_FIM)
    ap.add_argument("--memoria", default=None,
                    help="Teto de RAM do motor, ex.: 512MB, 1GB, 2GB (padrão: 1GB)")
    ap.add_argument("--lote", type=int, default=None,
                    help="Registros por lote na conversão .dbc->Parquet. "
                         "Controla o pico de memória (padrão: 50000)")
    args = ap.parse_args()
    ano_inicio, ano_fim = args.ano_inicio, args.ano_fim
    if ano_fim < ano_inicio:
        raise SystemExit("ano_fim deve ser >= ano_inicio")

    cid_filter = build_cid_filter(custom_codes=CIDS_ALVO)
    print(f"CIDs-alvo normalizados: {cid_filter.get('prefixes')}", flush=True)

    sih = coletar_sih(ano_inicio, ano_fim, cid_filter,
                      memory_limit=args.memoria, batch_size=args.lote)
    print(f"Registros SIH filtrados: {len(sih)}", flush=True)

    sim = coletar_sim(ano_inicio, ano_fim, cid_filter,
                      memory_limit=args.memoria, batch_size=args.lote)
    print(f"Registros SIM filtrados: {len(sim)}", flush=True)

    sih_g = agregar_sih(sih)
    sim_g = agregar_sim(sim)
    resumo, prob = resumos(sih_g, sim_g)

    exportar(sih_g, sim_g, prob, resumo, ano_inicio, ano_fim)

    print("\n=== Resumo por faixa etária ===", flush=True)
    print(resumo.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
