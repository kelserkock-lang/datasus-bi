"""
Gera o relatório completo (Word) + gráficos do modelo de custo-efetividade.

Reusa o `modelo.py` (árvore de decisão + Monte Carlo) e produz:
  - gráficos em `saida/graficos/` (CEAC, plano de custo-efetividade, tornado, ICER)
  - relatório em `saida/relatorio_custo_efetividade_srag_sc.docx`

Uso (a partir da raiz do projeto):
  python custo_efetividade/relatorio.py            # 8.000 iterações
  python custo_efetividade/relatorio.py 20000      # N iterações
"""

import argparse
import datetime
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from docx import Document  # noqa: E402
from docx.shared import Pt, Inches, RGBColor  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402

from modelo import (  # noqa: E402
    carregar_parametros, cenarios_base, psa_amostras, resumo_psa, ceac, tornado,
    CUSTO_HOSP_REAL, POPULACAO_SC, COBERTURA, CUSTO_VACINA, VE_HOSP,
    EXPECTATIVA_VIDA, WTP_QALY, PIB_PER_CAPITA, DISCOUNT_RATE, VIRUS_ALVO,
)

SAIDA = os.path.join(PROJECT_DIR, "saida")
GRAF = os.path.join(SAIDA, "graficos")
os.makedirs(GRAF, exist_ok=True)

plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3})

AZUL = "#1565c0"
NOMES_PARAM = {
    "h0": "Taxa de SRAG (h0)", "ve": "Eficácia (VE)", "cov": "Cobertura",
    "p_uti": "P(UTI | internação)", "p_death": "P(óbito | internação)",
    "custo_hosp": "Custo da internação", "custo_vac": "Custo da dose",
}


def _f(x, casas=2):
    """Formata número para texto, tratando inf/nan."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not np.isfinite(v):
        return "—"
    return f"{v:,.{casas}f}"


# ------------------------------------------------------------------
# GRÁFICOS
# ------------------------------------------------------------------
def grafico_ceac(ceac_df):
    fig, ax = plt.subplots(figsize=(8, 5))
    cores = {"Criancas (0-14)": "#e53935", "Adultos (15-59)": "#43a047", "Idosos (60+)": "#1e88e5"}
    sub = ceac_df[ceac_df["virus"] == "Todos"]
    for faixa in POPULACAO_SC:
        for persp, ls in [("Real", "-"), ("SUS", "--")]:
            d = sub[(sub["faixa_etaria"] == faixa) & (sub["perspectiva"] == persp)]
            if d.empty:
                continue
            ax.plot(d["WTP"] / 1000, d["p_efetivo"], ls=ls, color=cores[faixa],
                    label=f"{faixa} — {persp}")
    for x, rotulo in [(PIB_PER_CAPITA / 1000, "1× PIB"),
                      (WTP_QALY / 1000, "WTP 120 mil"),
                      (3 * PIB_PER_CAPITA / 1000, "3× PIB")]:
        ax.axvline(x, color="gray", linestyle=":", linewidth=1.1)
        ax.text(x + 2, 0.02, rotulo, color="gray", fontsize=8)
    ax.set_xlabel("Limiar de disposição a pagar (R$ mil por QALY)")
    ax.set_ylabel("Probabilidade de ser custo-efetivo")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title("Curva de aceitabilidade custo-efetividade (CEAC) — todos os vírus")
    fig.tight_layout()
    path = os.path.join(GRAF, "ceac.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def grafico_plano(amostras):
    sub = amostras[(amostras["virus"] == "Todos") & (amostras["perspectiva"] == "Real")]
    cores = {"Criancas (0-14)": "#e53935", "Adultos (15-59)": "#43a047", "Idosos (60+)": "#1e88e5"}
    fig, ax = plt.subplots(figsize=(8, 5))
    for faixa in POPULACAO_SC:
        d = sub[sub["faixa_etaria"] == faixa]
        d = d.sample(min(2000, len(d)), random_state=1)
        ax.scatter(d["qaly"], d["custo_liquido"], s=6, alpha=0.35,
                   color=cores[faixa], label=faixa)
    xmax = max(sub["qaly"].quantile(0.99), 1)
    ax.plot([0, xmax], [0, WTP_QALY * xmax], color="gray", linestyle="--",
            label=f"Limiar {WTP_QALY/1000:.0f} mil/QALY")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("QALYs ganhos (incrementais)")
    ax.set_ylabel("Custo incremental (R$)")
    ax.legend(fontsize=8)
    ax.set_title("Plano de custo-efetividade — cenário 'Todos' (perspectiva Real)")
    fig.tight_layout()
    path = os.path.join(GRAF, "plano_custo_efetividade.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def grafico_tornado(torn):
    sub = torn[(torn["faixa_etaria"] == "Idosos (60+)") & (torn["perspectiva"] == "Real")]
    sub = sub.sort_values("swing", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(sub))
    for i, (_, r) in enumerate(sub.iterrows()):
        lo, hi = r["custo_liquido_baixo"], r["custo_liquido_alto"]
        ax.hlines(i, lo, hi, color=AZUL, linewidth=9, alpha=0.8)
        ax.scatter([lo, hi], [i, i], s=12, color="#0d47a1", zorder=3)
    base_neto = sub["custo_liquido_baixo"].mean()
    ax.axvline(base_neto, color="gray", linestyle=":", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels([NOMES_PARAM.get(p, p) for p in sub["parametro"]])
    ax.set_xlabel("Custo líquido incremental (R$)")
    ax.set_title("Tornado — Idosos (60+), perspectiva Real (±20%)")
    fig.tight_layout()
    path = os.path.join(GRAF, "tornado.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def grafico_icer(base):
    sub = base[(base["perspectiva"] == "Real") & (base["virus"] != "Todos")].copy()
    sub = sub.replace([np.inf, -np.inf], np.nan)
    sub["rotulo"] = sub["faixa_etaria"].str.replace(" (", "\n(", regex=False)
    piv = sub.pivot_table(index="rotulo", columns="virus", values="ICER_R_por_QALY")
    piv = piv.reindex(index=sub["rotulo"].unique(), columns=VIRUS_ALVO)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    piv.plot(kind="bar", ax=ax, color=["#e53935", "#43a047", "#1e88e5"])
    ax.axhline(WTP_QALY, color="gray", linestyle="--", linewidth=1.2)
    ax.text(0.02, WTP_QALY * 1.05, f"WTP = R$ {WTP_QALY/1000:.0f} mil", color="gray")
    ax.set_yscale("log")
    ax.set_ylabel("ICER (R$ por QALY, escala log)")
    ax.set_xlabel("")
    ax.legend(title="Vírus")
    ax.set_title("ICER por QALY — perspectiva Real")
    fig.tight_layout()
    path = os.path.join(GRAF, "icer_por_qaly.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ------------------------------------------------------------------
# WORD
# ------------------------------------------------------------------
def tabela_cenarios(params, custo_hosp_sus, n_anos):
    linhas = []
    for persp, ch in [("SUS", custo_hosp_sus), ("Real", CUSTO_HOSP_REAL)]:
        for taxa in [0.0, 0.03, 0.05]:
            b = cenarios_base(params, ch, n_anos, persp, taxa_desconto=taxa)
            for _, r in b[b["virus"] == "Todos"].iterrows():
                linhas.append({
                    "perspectiva": persp,
                    "faixa_etaria": r["faixa_etaria"],
                    "desconto": f"{taxa*100:.0f}%",
                    "ICER_R_por_QALY": r["ICER_R_por_QALY"],
                    "veredicto_1x_PIB": r["veredicto_1x_PIB"],
                    "veredicto_3x_PIB": r["veredicto_3x_PIB"],
                })
    return pd.DataFrame(linhas)


def _adicionar_tabela(doc, df, colunas=None, fonte=8):
    df = df.copy()
    if colunas:
        df = df[colunas]
    for c in df.columns:
        df[c] = df[c].map(lambda v: _f(v) if not isinstance(v, str) else v)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for j, c in enumerate(df.columns):
        hdr[j].text = str(c)
    for _, row in df.iterrows():
        cells = table.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = str(v)
    for r in table.rows:
        for cell in r.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(fonte)
    return table


def _titulo(doc, texto, nivel=1):
    doc.add_heading(texto, level=nivel)


def _par(doc, texto, negrito=False, tamanho=11):
    p = doc.add_paragraph()
    run = p.add_run(texto)
    run.bold = negrito
    run.font.size = Pt(tamanho)
    return p


def gerar_word(base, resumo, torn, n_anos, custo_hosp_sus, params):
    doc = Document()

    # Cabeçalho
    h = doc.add_heading("Relatório de Custo-Efetividade", level=0)
    p = doc.add_paragraph()
    p.add_run("Intervenções contra doenças respiratórias sazonais em Santa Catarina "
              "(Influenza, COVID-19 e VSR)").bold = True
    doc.add_paragraph(f"Gerado em {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} — "
                      f"janela 2020–2024 ({n_anos} anos de SRAG)")

    # 1. Contexto
    _titulo(doc, "1. Contexto e objetivo", 1)
    _par(doc, "O inverno rigoroso de Santa Catarina gera sazonalidade marcante das doenças "
              "respiratórias, com pico de internações por SRAG (Síndrome Respiratória Aguda Grave) "
              "entre maio e agosto e reflexo imediato na ocupação de leitos de UTI. Este relatório "
              "avalia a custo-efetividade de vacinar versus não vacinar três faixas etárias "
              "(crianças 0–14, adultos 15–59 e idosos 60+) contra Influenza, COVID-19 e VSR.")
    _par(doc, "A medida de resultado é o ICER (razão de custo-efetividade incremental) expresso "
              "em R$ por óbito evitado e em R$ por QALY ganho. Um ICER negativo indica intervenção "
              "dominante (poupadora de recursos).")

    # 2. Métodos e fontes
    _titulo(doc, "2. Métodos e fontes de dados", 1)
    _par(doc, "Modelo: árvore de decisão determinística seguida de análise de sensibilidade "
              "probabilística (Monte Carlo).", negrito=True)
    for item in [
        "Custos hospitalares (SIH/SUS): custo médio da internação por faixa etária a partir do "
        "VAL_TOT das AIH de SC (2020–2024), filtradas por CID respiratório (J09–J18, U07.1).",
        "Efetividade (SIVEP-Gripe): casos de SRAG por vírus, UTI e óbitos, via OpenDataSUS.",
        "Custo da vacinação: custo por pessoa vacinada (dose + administração).",
        "Duas perspectivas de custo hospitalar: SUS (reembolso AIH) e Real (custo econômico estimado, "
        "incluindo UTI).",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    # 3. Parâmetros
    _titulo(doc, "3. Parâmetros do modelo", 1)
    _par(doc, "Parâmetros editáveis no topo do arquivo modelo.py. Valores de eficácia (VE) "
              "calibrados a partir da literatura (ver comentários no código).", tamanho=10)
    _adicionar_tabela(doc, pd.DataFrame({
        "Faixa": list(POPULACAO_SC),
        "População": [f"{v:,.0f}".replace(",", ".") for v in POPULACAO_SC.values()],
        "Cobertura": [f"{v*100:.0f}%" for v in COBERTURA.values()],
        "Custo dose (R$)": [f"{v:.0f}" for v in CUSTO_VACINA.values()],
        "Custo hosp. SUS (R$)": [f"{custo_hosp_sus[f]:.0f}" for f in POPULACAO_SC],
        "Custo hosp. Real (R$)": [f"{CUSTO_HOSP_REAL[f]:,.0f}".replace(",", ".") for f in POPULACAO_SC],
        "Expect. vida (anos)": [f"{v:.0f}" for v in EXPECTATIVA_VIDA.values()],
    }))
    doc.add_paragraph("")
    _adicionar_tabela(doc, pd.DataFrame({
        "Vírus": VIRUS_ALVO + ["Todos"],
        **{f"VE {f}": [f"{VE_HOSP[v][f]*100:.0f}%" for v in VIRUS_ALVO + ["Todos"]]
           for f in POPULACAO_SC},
    }))

    # 4. Resultados caso-base
    _titulo(doc, "4. Resultados — caso-base", 1)
    _par(doc, "Perspectiva SUS (reembolso AIH):", negrito=True)
    cols = ["faixa_etaria", "virus", "obitos_evitados_ano", "custo_liquido",
            "ICER_R_por_obito", "ICER_R_por_QALY", "veredicto"]
    _adicionar_tabela(doc, base[base["perspectiva"] == "SUS"], cols)
    doc.add_paragraph("")
    _par(doc, "Perspectiva Real (custo econômico):", negrito=True)
    _adicionar_tabela(doc, base[base["perspectiva"] == "Real"], cols)

    # 5. PSA
    _titulo(doc, "5. Análise de sensibilidade probabilística", 1)
    _par(doc, "Monte Carlo com distribuições Beta (probabilidades e VE) e Gamma (custos). "
              "A tabela resume a probabilidade de a intervenção ser custo-efetiva no limiar de "
              f"R$ {WTP_QALY/1000:.0f} mil por QALY.", tamanho=10)
    _adicionar_tabela(doc, resumo, ["faixa_etaria", "virus", "perspectiva",
                                    "p_custo_poupador", "media_obitos_evitados",
                                    "ICER_medio_R_por_obito", "p_efetivo_WTP"])
    doc.add_picture(os.path.join(GRAF, "ceac.png"), width=Inches(6.3))

    # 6. Plano de custo-efetividade
    _titulo(doc, "6. Plano de custo-efetividade", 1)
    _par(doc, "Cada ponto é uma iteração da simulação (perspectiva Real, cenário 'Todos'). "
              "Pontos abaixo da reta do limiar são custo-efetivos.", tamanho=10)
    doc.add_picture(os.path.join(GRAF, "plano_custo_efetividade.png"), width=Inches(6.3))
    doc.add_picture(os.path.join(GRAF, "icer_por_qaly.png"), width=Inches(6.3))

    # 7. Tornado
    _titulo(doc, "7. Sensibilidade univariada (tornado)", 1)
    _par(doc, "Variação de ±20% em cada parâmetro, para idosos (grupo de maior impacto). "
              "O custo líquido é mais sensível à cobertura e ao custo da dose.", tamanho=10)
    doc.add_picture(os.path.join(GRAF, "tornado.png"), width=Inches(6.3))
    _adicionar_tabela(doc, torn[torn["faixa_etaria"] == "Idosos (60+)"],
                      ["perspectiva", "parametro", "valor_base", "custo_liquido_baixo",
                       "custo_liquido_alto", "swing"])

    # 8. Análise de cenário
    _titulo(doc, "8. Análise de cenário (desconto temporal e limiar)", 1)
    _par(doc, f"QALYs descontados a {DISCOUNT_RATE*100:.0f}% a.a. na análise principal. A tabela "
              f"compara taxas de desconto de 0%, 3% e 5% e os limiares de 1× PIB per capita "
              f"(R$ {PIB_PER_CAPITA/1000:.0f} mil) e 3× PIB (R$ {3*PIB_PER_CAPITA/1000:.0f} mil), "
              "para o cenário agregado 'Todos'.", tamanho=10)
    _adicionar_tabela(doc, tabela_cenarios(params, custo_hosp_sus, n_anos),
                      ["perspectiva", "faixa_etaria", "desconto", "ICER_R_por_QALY",
                       "veredicto_1x_PIB", "veredicto_3x_PIB"])

    # 9. Conclusões
    _titulo(doc, "9. Conclusões e limitações", 1)
    real_covid_idosos = base[(base["perspectiva"] == "Real") & (base["virus"] == "COVID-19")
                             & (base["faixa_etaria"] == "Idosos (60+)")]
    if not real_covid_idosos.empty:
        icer = _f(real_covid_idosos.iloc[0]["ICER_R_por_QALY"])
        _par(doc, f"Na perspectiva Real (desconto de 3% a.a.), a vacinação contra COVID-19 em "
              f"idosos apresentou ICER de R$ {icer} por QALY — abaixo de qualquer limiar usual, "
              "sendo custo-efetiva.")
    _par(doc, "O desconto temporal reduz o valor dos QALYs futuros e, portanto, eleva o ICER; "
              "ainda assim, as conclusões qualitativas se mantêm. Com o limiar mais rigoroso de "
              "1× PIB per capita (R$ 55 mil), apenas a COVID-19 em adultos e idosos permanece "
              "custo-efetiva; com 3× PIB (R$ 165 mil), os cenários agregados por faixa também "
              "passam a ser custo-efetivos.")
    _par(doc, "Limitações: (i) o VAL_TOT do SIH é reembolso AIH, não o custo total — por isso "
              "apresentamos também a perspectiva Real, cujos valores são placeholders a calibrar "
              "com estudo de custo local; (ii) COVID-19 no SIH está subnotificada (codificada como "
              "pneumonia J12–J18); (iii) VE e custo da dose são valores de literatura ajustáveis; "
              "(iv) não foram incluídos custos de produtividade nem perda de qualidade de vida dos "
              "sobreviventes.")

    path = os.path.join(SAIDA, "relatorio_custo_efetividade_srag_sc.docx")
    doc.save(path)
    return path


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n_iter", nargs="?", type=int, default=8000)
    args = ap.parse_args()

    params, custo_hosp_sus, n_anos = carregar_parametros()

    base = pd.concat([
        cenarios_base(params, custo_hosp_sus, n_anos, "SUS"),
        cenarios_base(params, CUSTO_HOSP_REAL, n_anos, "Real"),
    ], ignore_index=True)

    amostras = pd.concat([
        psa_amostras(params, custo_hosp_sus, n_anos, args.n_iter, "SUS"),
        psa_amostras(params, CUSTO_HOSP_REAL, n_anos, args.n_iter, "Real"),
    ], ignore_index=True)
    resumo = resumo_psa(amostras)
    ceac_df = ceac(amostras, np.linspace(0, 300_000, 61))
    torn = pd.concat([
        tornado(params, custo_hosp_sus, "SUS"),
        tornado(params, CUSTO_HOSP_REAL, "Real"),
    ], ignore_index=True)

    p1 = grafico_ceac(ceac_df)
    p2 = grafico_plano(amostras)
    p3 = grafico_tornado(torn)
    p4 = grafico_icer(base)
    print("Gráficos:", p1, p2, p3, p4, sep="\n  ")

    docx = gerar_word(base, resumo, torn, n_anos, custo_hosp_sus, params)
    print("Relatório Word:", docx)


if __name__ == "__main__":
    main()
