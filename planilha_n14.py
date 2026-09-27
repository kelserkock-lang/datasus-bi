"""
Planilha DATASUS — CID N14: Nefrite e nefropatia induzidas por drogas e substâncias pesadas.

Gera uma planilha Excel com dados do SIH/SUS (SIH-RD) filtrados pelo CID N10
para uma Unidade da Federação no período especificado.

Saída: planilha_N14_{UF}_{ano_inicio}_{ano_fim}.xlsx
  - Aba "Resumo":           Internações, mortalidade, valor total, dias médios por ano
  - Aba "Por_Faixa_Etaria": Mesmas métricas desagregadas por faixa etária
  - Aba "Por_Sexo":         Mesmas métricas desagregadas por sexo
  - Aba "Dados_Brutos":     Todos os registros N14 filtrados

Uso:
  python planilha_n14.py                          # SC, 2015-2025 (padrão)
  python planilha_n14.py --uf SP                  # São Paulo
  python planilha_n14.py --ano-inicio 2018        # 2018-2025
  python planilha_n14.py --uf SC --ano-inicio 2015 --ano-fim 2025

Memória (bases grandes / PC com pouca RAM):
  python planilha_n14.py --memoria 512MB --lote 10000

  A coleta lê os .dbc em LOTES e grava Parquet em data/staging/ — nenhuma base
  inteira fica na RAM. --memoria é o teto de RAM do motor (padrão 1GB; ao
  atingir, ele derrama em disco) e --lote é quantos registros são processados
  por vez (padrão 50000) — este é o parâmetro que controla o PICO de memória.
"""

import argparse
import os
import sys

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd

from data_ingestion import load_full_datasus
from cid_catalog import build_cid_filter

# ------------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------------
UF_PADRAO = "SC"
ANO_INICIO_PADRAO = 2015
ANO_FIM_PADRAO = 2025

CIDS_ALVO = ["N14"]

SIH_COLS = [
    "UF_ZI", "ANO_CMPT", "MES_CMPT",
    "IDADE", "SEXO", "MORTE",
    "VAL_TOT", "DIAS_PERM", "DIAG_PRINC",
]

FAIXAS_ETARIAS = [
    (0, 4, "0-4"),
    (5, 14, "5-14"),
    (15, 29, "15-29"),
    (30, 44, "30-44"),
    (45, 59, "45-59"),
    (60, 74, "60-74"),
    (75, 199, "75+"),
]

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------

def faixa_etaria(anos):
    """Classifica idade em faixa etária."""
    if pd.isna(anos):
        return "Ignorado"
    for lo, hi, label in FAIXAS_ETARIAS:
        if lo <= int(anos) <= hi:
            return label
    return "Ignorado"


def label_sexo(codigo):
    """Mapeia código SIH de sexo para rótulo legível."""
    try:
        v = int(float(codigo))
    except (TypeError, ValueError):
        return "Ignorado"
    return {1: "Masculino", 3: "Feminino"}.get(v, "Ignorado")


def progresso(pct, msg):
    """Callback de progresso para o Streamlit/CLI."""
    print(f"  [{pct * 100:5.1f}%] {msg}", flush=True)


# ------------------------------------------------------------------
# COLETA
# ------------------------------------------------------------------

def coletar_sih(uf, ano_inicio, ano_fim, cid_filter, memory_limit=None, batch_size=None):
    """Baixa dados do SIH-RD e filtra pelo CID N14.

    memory_limit: teto de RAM do motor (ex.: "1GB"). None usa o padrão.
    batch_size:   registros por lote na conversão. None usa o padrão.
    """
    print(f"\n{'='*60}")
    print(f"  SIH-RD  |  CID N14  |  {uf}  |  {ano_inicio}-{ano_fim}")
    print(f"{'='*60}", flush=True)

    df = load_full_datasus(
        "SIH-RD", uf, ano_inicio, ano_fim,
        month="Todos", city_code="",
        columns_to_keep=SIH_COLS, cid_filter=cid_filter,
        memory_efficient=True, progress_callback=progresso,
        memory_limit=memory_limit, batch_size=batch_size,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Idade em anos (SIH-RD já vem decodificado)
    df["idade_anos"] = pd.to_numeric(df["IDADE"], errors="coerce")
    df["faixa_etaria"] = df["idade_anos"].apply(faixa_etaria)
    df["sexo_label"] = df["SEXO"].apply(label_sexo)

    # Coerção numérica
    for c in ["VAL_TOT", "DIAS_PERM", "MORTE"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# ------------------------------------------------------------------
# AGREGAÇÃO
# ------------------------------------------------------------------

def agregar(df, uf):
    """Gera as 3 tabelas agregadas: resumo, por faixa etária e por sexo."""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Tabela 1: Resumo por Ano
    resumo = df.groupby("ANO_CMPT", dropna=False).agg(
        internacoes=("DIAG_PRINC", "count"),
        mortalidade=("MORTE", lambda s: (s == 1).sum()),
        valor_total=("VAL_TOT", "sum"),
        dias_perm_media=("DIAS_PERM", "mean"),
    ).reset_index()
    resumo["mortalidade_pct"] = (
        resumo["mortalidade"] / resumo["internacoes"] * 100
    ).round(2)
    resumo["UF"] = uf
    resumo["ANO_CMPT"] = resumo["ANO_CMPT"].astype(str).str.strip()

    # Tabela 2: Por Faixa Etária
    por_faixa = df.groupby(["ANO_CMPT", "faixa_etaria"], dropna=False).agg(
        internacoes=("DIAG_PRINC", "count"),
        mortalidade=("MORTE", lambda s: (s == 1).sum()),
        valor_total=("VAL_TOT", "sum"),
        dias_perm_media=("DIAS_PERM", "mean"),
    ).reset_index()
    por_faixa["mortalidade_pct"] = (
        por_faixa["mortalidade"] / por_faixa["internacoes"] * 100
    ).round(2)
    por_faixa["ANO_CMPT"] = por_faixa["ANO_CMPT"].astype(str).str.strip()

    # Tabela 3: Por Sexo
    por_sexo = df.groupby(["ANO_CMPT", "sexo_label"], dropna=False).agg(
        internacoes=("DIAG_PRINC", "count"),
        mortalidade=("MORTE", lambda s: (s == 1).sum()),
        valor_total=("VAL_TOT", "sum"),
        dias_perm_media=("DIAS_PERM", "mean"),
    ).reset_index()
    por_sexo["mortalidade_pct"] = (
        por_sexo["mortalidade"] / por_sexo["internacoes"] * 100
    ).round(2)
    por_sexo["ANO_CMPT"] = por_sexo["ANO_CMPT"].astype(str).str.strip()

    return resumo, por_faixa, por_sexo


# ------------------------------------------------------------------
# EXPORTAÇÃO
# ------------------------------------------------------------------

def _fmt_brl(valor):
    """Formata valor numérico como moeda brasileira."""
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def exportar_excel(resumo, por_faixa, por_sexo, df_bruto, uf, ano_inicio, ano_fim):
    """Gera a planilha Excel com 4 abas + fallback CSV."""
    # Adicionar linha de TOTAL ao resumo
    total_internacoes = resumo["internacoes"].sum()
    total_mortalidade = resumo["mortalidade"].sum()
    total_valor = resumo["valor_total"].sum()
    media_dias = resumo["dias_perm_media"].mean()
    mortalidade_pct_total = (
        round(total_mortalidade / total_internacoes * 100, 2)
        if total_internacoes > 0 else 0
    )

    total_row = pd.DataFrame([{
        "ANO_CMPT": "TOTAL",
        "internacoes": total_internacoes,
        "mortalidade": total_mortalidade,
        "valor_total": total_valor,
        "dias_perm_media": round(media_dias, 2),
        "mortalidade_pct": mortalidade_pct_total,
        "UF": uf,
    }])
    resumo_com_total = pd.concat([resumo, total_row], ignore_index=True)

    # Adicionar colunas formatadas
    resumo_display = resumo_com_total.copy()
    resumo_display["valor_total_BRL"] = resumo_display["valor_total"].apply(_fmt_brl)
    resumo_display["dias_perm_media"] = resumo_display["dias_perm_media"].round(1)
    resumo_display = resumo_display.rename(columns={
        "ANO_CMPT": "Ano",
        "internacoes": "Internações",
        "mortalidade": "Mortalidade",
        "valor_total": "Valor Total (R$)",
        "valor_total_BRL": "Valor Total (formatado)",
        "dias_perm_media": "Dias Médios Permanência",
        "mortalidade_pct": "Mortalidade %",
    })

    # Formatar por_faixa
    por_faixa_display = por_faixa.copy()
    por_faixa_display["valor_total_BRL"] = por_faixa_display["valor_total"].apply(_fmt_brl)
    por_faixa_display["dias_perm_media"] = por_faixa_display["dias_perm_media"].round(1)
    por_faixa_display = por_faixa_display.rename(columns={
        "ANO_CMPT": "Ano",
        "faixa_etaria": "Faixa Etária",
        "internacoes": "Internações",
        "mortalidade": "Mortalidade",
        "valor_total": "Valor Total (R$)",
        "valor_total_BRL": "Valor Total (formatado)",
        "dias_perm_media": "Dias Médios Permanência",
        "mortalidade_pct": "Mortalidade %",
    })

    # Formatar por_sexo
    por_sexo_display = por_sexo.copy()
    por_sexo_display["valor_total_BRL"] = por_sexo_display["valor_total"].apply(_fmt_brl)
    por_sexo_display["dias_perm_media"] = por_sexo_display["dias_perm_media"].round(1)
    por_sexo_display = por_sexo_display.rename(columns={
        "ANO_CMPT": "Ano",
        "sexo_label": "Sexo",
        "internacoes": "Internações",
        "mortalidade": "Mortalidade",
        "valor_total": "Valor Total (R$)",
        "valor_total_BRL": "Valor Total (formatado)",
        "dias_perm_media": "Dias Médios Permanência",
        "mortalidade_pct": "Mortalidade %",
    })

    filename = os.path.join(ROOT, f"planilha_N14_{uf}_{ano_inicio}_{ano_fim}.xlsx")

    try:
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            resumo_display.to_excel(writer, sheet_name="Resumo", index=False)
            por_faixa_display.to_excel(writer, sheet_name="Por_Faixa_Etaria", index=False)
            por_sexo_display.to_excel(writer, sheet_name="Por_Sexo", index=False)
            df_bruto.to_excel(writer, sheet_name="Dados_Brutos", index=False)

        print(f"\n{'='*60}")
        print(f"  ✅  Planilha gerada com sucesso!")
        print(f"  📁  {filename}")
        print(f"{'='*60}")

    except ImportError:
        print("\n⚠️  openpyxl não instalado. Gerando CSVs como alternativa...")
        print("   Instale com: pip install openpyxl\n")

        for nome, df_zip in [
            ("resumo", resumo_display),
            ("faixa_etaria", por_faixa_display),
            ("sexo", por_sexo_display),
            ("brutos", df_bruto),
        ]:
            csv_path = os.path.join(ROOT, f"{nome}_N14_{uf}_{ano_inicio}_{ano_fim}.csv")
            df_zip.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"  📄 {csv_path}")


# ------------------------------------------------------------------
# RESUMO NO CONSOLE
# ------------------------------------------------------------------

def imprimir_resumo(resumo, total_registros):
    """Imprime resumo formatado no console."""
    print(f"\n{'─'*60}")
    print(f"  RESUMO — CID N14 (Nefrite induzida por drogas)")
    print(f"{'─'*60}")
    print(f"  {'Ano':<8} {'Internações':>12} {'Óbitos':>8} {'Mortalidade':>12} {'Valor Total':>18} {'Dias Méd':>10}")
    print(f"  {'─'*8} {'─'*12} {'─'*8} {'─'*12} {'─'*18} {'─'*10}")

    for _, row in resumo.iterrows():
        ano = str(row["ANO_CMPT"])
        intern = int(row["internacoes"])
        mort = int(row["mortalidade"])
        mort_pct = row["mortalidade_pct"]
        valor = row["valor_total"]
        dias = row["dias_perm_media"]

        valor_fmt = _fmt_brl(valor)
        dias_fmt = f"{dias:.1f}" if not pd.isna(dias) else "-"

        if ano == "TOTAL":
            print(f"  {'─'*8} {'─'*12} {'─'*8} {'─'*12} {'─'*18} {'─'*10}")

        print(f"  {ano:<8} {intern:>12,} {mort:>8} {mort_pct:>11.2f}% {valor_fmt:>18} {dias_fmt:>10}")

    print(f"\n  📊 Total de registros N14: {total_registros:,}")


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Planilha DATASUS — CID N14: Nefrite induzida por drogas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python planilha_n14.py
  python planilha_n14.py --uf SP
  python planilha_n14.py --uf SC --ano-inicio 2018 --ano-fim 2025
  python planilha_n14.py --memoria 512MB --lote 10000   # PC com pouca RAM
        """,
    )
    ap.add_argument("--uf", default=UF_PADRAO, help=f"Unidade da Federação (padrão: {UF_PADRAO})")
    ap.add_argument("--ano-inicio", type=int, default=ANO_INICIO_PADRAO, help=f"Ano inicial (padrão: {ANO_INICIO_PADRAO})")
    ap.add_argument("--ano-fim", type=int, default=ANO_FIM_PADRAO, help=f"Ano final (padrão: {ANO_FIM_PADRAO})")
    ap.add_argument("--memoria", default=None,
                    help="Teto de RAM do motor, ex.: 512MB, 1GB, 2GB (padrão: 1GB)")
    ap.add_argument("--lote", type=int, default=None,
                    help="Registros por lote na conversão .dbc->Parquet. "
                         "Controla o pico de memória (padrão: 50000)")
    args = ap.parse_args()

    if args.ano_fim < args.ano_inicio:
        raise SystemExit("❌ O ano final deve ser >= ano inicial.")

    cid_filter = build_cid_filter(custom_codes=CIDS_ALVO)
    print(f"CID-alvo: {cid_filter['prefixes']}")

    df = coletar_sih(args.uf, args.ano_inicio, args.ano_fim, cid_filter,
                     memory_limit=args.memoria, batch_size=args.lote)

    if df.empty:
        print("\n❌ Nenhum registro encontrado para CID N14 neste período/UF.")
        print("   Possíveis causas:")
        print("   - CID N14 não é registrado como diagnóstico principal nesta região")
        print("   - Período sem dados disponíveis no FTP do DataSUS")
        print("   - Todos os registros foram filtrados por critérios de qualidade")
        return

    print(f"\n📋 Registros N14 filtrados: {len(df):,}")

    resumo, por_faixa, por_sexo = agregar(df, args.uf)

    exportar_excel(resumo, por_faixa, por_sexo, df, args.uf, args.ano_inicio, args.ano_fim)

    imprimir_resumo(resumo, len(df))


if __name__ == "__main__":
    main()
