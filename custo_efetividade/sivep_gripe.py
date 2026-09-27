"""
Coleta SIVEP-Gripe (SRAG — Síndrome Respiratória Aguda Grave) de Santa Catarina
via OpenDataSUS (arquivos Parquet no S3 do Ministério da Saúde).

Complementa a coleta de SIH/SIM do `coleta.py`, fornecendo o denominador de
gravidade por vírus (Influenza, VSR, SARS-CoV-2/COVID-19), faixa etária e desfecho.

Fonte: dataset "Banco de dados da Síndrome Respiratória Aguda Grave (SRAG) - 2019 a 2026"
  https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026
Arquivos: https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/{ano}/INFLUD{aa}-{data}.parquet

Saídas (pasta `saida/`):
  - sivep_gripe_sc.xlsx        (planilha Excel)
  - sivep_gripe_casos.csv      (registros de SC normalizados)
  - sivep_gripe_agregado.csv   (agregado por ano/mês/faixa/vírus)
  - sivep_gripe_resumo.csv     (resumo por faixa × vírus)

Uso (a partir da raiz do projeto):
  python custo_efetividade/sivep_gripe.py              # janela padrão 2020..2024
  python custo_efetividade/sivep_gripe.py 2019 2025    # janela customizada
"""

import argparse
import datetime
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

import pandas as pd  # noqa: E402
import requests  # noqa: E402

# ------------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------------
UF = "SC"
ANO_INICIO = 2020
ANO_FIM = 2024

S3_BASE = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG"

# Data do "banco vivo" por ano (descobertas em 17/08/2026).
# Anos 2019-2024 estão CONGELADOS (não mudam). Anos 2025-2026 atualizam semanalmente.
SRAG_DATAS = {
    2019: "23-03-2026",
    2020: "23-03-2026",
    2021: "23-03-2026",
    2022: "23-03-2026",
    2023: "23-03-2026",
    2024: "23-03-2026",
    2025: "17-08-2026",
    2026: "17-08-2026",
}

# Colunas mantidas do banco SRAG (existem em todos os anos 2019+)
COLS = [
    "DT_NOTIFIC", "SEM_NOT", "DT_SIN_PRI", "SEM_PRI",
    "SG_UF_NOT", "ID_MUNICIP", "CO_MUN_NOT",
    "CS_SEXO", "NU_IDADE_N", "TP_IDADE",
    "CLASSI_FIN", "EVOLUCAO", "HOSPITAL", "UTI", "SUPORT_VEN",
    "DT_INTERNA", "DT_ENTUTI", "DT_SAIDUTI", "DT_EVOLUCA", "DT_ENCERRA",
    "POS_PCRFLU", "TP_FLU_PCR", "PCR_FLUASU", "PCR_FLUBLI",
    "POS_PCROUT", "PCR_VSR", "PCR_SARS2", "POS_AN_FLU", "AN_SARS2", "AN_VSR",
    "VACINA", "VACINA_COV", "DOSE_1_COV", "DOSE_2_COV", "DOSE_REF",
]

DATA_DIR = os.path.join(PROJECT_DIR, "data", "srag")
SAIDA_DIR = os.path.join(PROJECT_DIR, "saida")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SAIDA_DIR, exist_ok=True)


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def _url(ano):
    data = SRAG_DATAS.get(ano)
    if not data:
        raise ValueError(f"Sem URL mapeada para o ano {ano}. Atualize SRAG_DATAS.")
    return f"{S3_BASE}/{ano}/INFLUD{str(ano)[-2:]}-{data}.parquet"


def _baixar_parquet(ano):
    """Baixa (com cache local) e retorna o caminho do parquet do ano."""
    path = os.path.join(DATA_DIR, f"INFLUD{str(ano)[-2:]}.parquet")
    if os.path.exists(path):
        print(f"  cache: {os.path.basename(path)}", flush=True)
        return path
    url = _url(ano)
    print(f"  baixando {url}", flush=True)
    r = requests.get(url, timeout=300, stream=True)
    r.raise_for_status()
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    os.replace(tmp, path)
    return path


def _eq1(v):
    """True se o valor equivale a '1' (positivo/sim)."""
    try:
        return int(float(v)) == 1
    except (TypeError, ValueError):
        return str(v).strip() in ("1", "1.0", "POSITIVO", "POSITIVO/REAGENTE")


def _dt_parts(v):
    """Extrai (ano, mês) de datas dd/mm/aaaa, aaaa-mm-dd ou aaaammdd."""
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "nat", ""):
        return "", ""
    s2 = s.replace("/", "-")
    parts = s2.split("-")
    if len(parts) >= 3:
        if len(parts[2]) == 4:          # dd-mm-aaaa
            return parts[2], parts[1]
        if len(parts[0]) == 4:          # aaaa-mm-dd
            return parts[0], parts[1]
    if len(s) == 8 and s.isdigit():     # aaaammdd
        return s[:4], s[4:6]
    return "", ""


def _idade_srag(nu_idade, tp_idade):
    """
    SRAG: NU_IDADE_N é o VALOR da idade; TP_IDADE é a UNIDADE
    (1=dia, 2=mês, 3=ano — verificado empiricamente nos parquets).
    Retorna idade em anos (menores de 1 ano -> 0) ou None.
    """
    try:
        valor = int(float(nu_idade))
    except (TypeError, ValueError):
        return None
    tp = str(tp_idade).strip()
    if tp in ("3", "4"):   # anos (4 por compatibilidade com o dicionário clássico)
        return valor
    return 0                # dias ou meses -> menor de 1 ano


def faixa_etaria(anos):
    if anos is None:
        return "Ignorado"
    if anos < 15:
        return "Criancas (0-14)"
    if anos < 60:
        return "Adultos (15-59)"
    return "Idosos (60+)"


def _sexo(v):
    s = str(v).strip().upper()
    return {"M": "Masculino", "F": "Feminino"}.get(s, "Ignorado")


def _virus(r):
    """Classifica o vírus do caso com base em PCR/antígeno e na classificação final."""
    if _eq1(r.get("PCR_SARS2")) or _eq1(r.get("AN_SARS2")):
        return "COVID-19"
    if _eq1(r.get("POS_PCRFLU")) or _eq1(r.get("POS_AN_FLU")):
        return "Influenza"
    if _eq1(r.get("PCR_VSR")) or _eq1(r.get("AN_VSR")):
        return "VSR"
    cf = str(r.get("CLASSI_FIN") or "").strip()
    if cf == "5":
        return "COVID-19"
    if cf == "1":
        return "Influenza"
    if cf == "2":
        return "Outro virus respiratorio"
    if cf == "3":
        return "Outro agente"
    if cf == "4":
        return "Nao especificado"
    return "Ignorado"


def _obito(v):
    """EVOLUCAO: 2 = óbito por SRAG."""
    try:
        return int(float(v)) == 2
    except (TypeError, ValueError):
        return str(v).strip() == "2"


# ------------------------------------------------------------------
# CARREGAMENTO
# ------------------------------------------------------------------
def carregar_anos(ano_inicio, ano_fim):
    frames = []
    for ano in range(ano_inicio, ano_fim + 1):
        print(f"\n=== SRAG {ano} ===", flush=True)
        try:
            path = _baixar_parquet(ano)
        except requests.HTTPError as e:
            print(f"  [AVISO] Falha no download de {ano}: {e}", flush=True)
            print(f"  Verifique a data em SRAG_DATAS para {ano} (banco vivo pode ter mudado).", flush=True)
            continue
        df = pd.read_parquet(path)
        df = df[[c for c in COLS if c in df.columns]]
        # filtro UF (SC) — coluna de notificação
        uf_col = "SG_UF_NOT" if "SG_UF_NOT" in df.columns else ("SG_UF" if "SG_UF" in df.columns else None)
        if uf_col:
            df = df[df[uf_col].astype(str).str.strip().str.upper() == UF]
        frames.append(df)
        print(f"  {len(df)} casos de {UF}", flush=True)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def normalizar(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()

    if "NU_IDADE_N" in df.columns and "TP_IDADE" in df.columns:
        df["idade_anos"] = df.apply(
            lambda r: _idade_srag(r.get("NU_IDADE_N"), r.get("TP_IDADE")), axis=1
        )
    else:
        df["idade_anos"] = None
    df["faixa_etaria"] = df["idade_anos"].apply(faixa_etaria)
    df["sexo"] = df["CS_SEXO"].apply(_sexo) if "CS_SEXO" in df.columns else "Ignorado"

    dt_col = "DT_SIN_PRI" if "DT_SIN_PRI" in df.columns else "DT_NOTIFIC"
    partes = df[dt_col].astype(str).apply(lambda v: pd.Series(_dt_parts(v)))
    df["ano"] = partes[0]
    df["mes"] = partes[1]

    df["semana_epi"] = pd.to_numeric(df["SEM_PRI"], errors="coerce") if "SEM_PRI" in df.columns else None

    df["virus"] = df.apply(_virus, axis=1)
    df["obito"] = df["EVOLUCAO"].apply(_obito) if "EVOLUCAO" in df.columns else False
    df["hospital"] = df["HOSPITAL"].apply(_eq1) if "HOSPITAL" in df.columns else False
    df["uti"] = df["UTI"].apply(_eq1) if "UTI" in df.columns else False
    df["suport_ven"] = df["SUPORT_VEN"].apply(_eq1) if "SUPORT_VEN" in df.columns else False

    keep = ["ano", "mes", "semana_epi", "faixa_etaria", "sexo", "virus",
            "obito", "hospital", "uti", "suport_ven"]
    return df[keep]


# ------------------------------------------------------------------
# AGREGAÇÃO E EXPORTAÇÃO
# ------------------------------------------------------------------
def agregar(df):
    cols = ["ano", "mes", "faixa_etaria", "virus", "casos", "obitos",
            "hospitalizados", "uti", "suport_ven", "p_obito"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = df.groupby(["ano", "mes", "faixa_etaria", "virus"], dropna=False).agg(
        casos=("obito", "size"),
        obitos=("obito", "sum"),
        hospitalizados=("hospital", "sum"),
        uti=("uti", "sum"),
        suport_ven=("suport_ven", "sum"),
    ).reset_index()
    g["p_obito"] = g["obitos"] / g["casos"].replace(0, pd.NA)
    return g[cols]


def resumo(df):
    if df.empty:
        return pd.DataFrame(columns=["faixa_etaria", "virus", "casos", "obitos", "p_obito"])
    g = df.groupby(["faixa_etaria", "virus"], dropna=False).agg(
        casos=("obito", "size"),
        obitos=("obito", "sum"),
        hospitalizados=("hospital", "sum"),
        uti=("uti", "sum"),
    ).reset_index()
    g["p_obito"] = g["obitos"] / g["casos"].replace(0, pd.NA)
    return g


def exportar(df, agreg, res, ano_inicio, ano_fim):
    metadados = pd.DataFrame({
        "Campo": ["Data de geração", "UF", "Janela de coleta", "Fonte",
                  "Classificação de vírus", "Faixas etárias"],
        "Valor": [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            UF, f"{ano_inicio}..{ano_fim}",
            "SIVEP-Gripe (SRAG) via OpenDataSUS — arquivos Parquet",
            "PCR/antígeno (SARS2, Influenza, VSR) com fallback em CLASSI_FIN",
            "Crianças 0-14, Adultos 15-59, Idosos 60+",
        ],
    })

    df.to_csv(os.path.join(SAIDA_DIR, "sivep_gripe_casos.csv"), index=False, encoding="utf-8-sig")
    agreg.to_csv(os.path.join(SAIDA_DIR, "sivep_gripe_agregado.csv"), index=False, encoding="utf-8-sig")
    res.to_csv(os.path.join(SAIDA_DIR, "sivep_gripe_resumo.csv"), index=False, encoding="utf-8-sig")

    xlsx = os.path.join(SAIDA_DIR, "sivep_gripe_sc.xlsx")
    try:
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            agreg.to_excel(writer, sheet_name="Agregado", index=False)
            res.to_excel(writer, sheet_name="Resumo_faixa_virus", index=False)
            metadados.to_excel(writer, sheet_name="Metadados", index=False)
        print(f"\nPlanilha Excel gerada: {xlsx}", flush=True)
    except ImportError:
        print("\n(Aviso) openpyxl não instalado — apenas CSVs gerados.", flush=True)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Coleta SIVEP-Gripe (SRAG) de SC.")
    ap.add_argument("ano_inicio", nargs="?", type=int, default=ANO_INICIO)
    ap.add_argument("ano_fim", nargs="?", type=int, default=ANO_FIM)
    args = ap.parse_args()
    ai, af = args.ano_inicio, args.ano_fim
    if af < ai:
        raise SystemExit("ano_fim deve ser >= ano_inicio")

    raw = carregar_anos(ai, af)
    df = normalizar(raw)
    print(f"\nCasos normalizados de {UF}: {len(df)}", flush=True)

    agreg = agregar(df)
    res = resumo(df)
    exportar(df, agreg, res, ai, af)

    print("\n=== Resumo por faixa × vírus ===", flush=True)
    print(res.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
