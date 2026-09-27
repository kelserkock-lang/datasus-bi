"""
Etapa 3 — Modelo de custo-efetividade (árvore de decisão + Monte Carlo).

Compara "Vacinar" vs. "Não vacinar" por faixa etária (crianças, adultos,
idosos) e por vírus (Influenza, COVID-19, VSR), usando os dados coletados:

  - SIH-RD   -> custo médio da internação (perspectiva SUS)
  - SIVEP-Gripe -> casos graves (SRAG), UTI e óbitos (denominador de efetividade)

Saída (pasta `saida/`):
  - modelo_resultados.csv   (caso-base por faixa x vírus)
  - modelo_psa_resumo.csv   (Monte Carlo: ICER, prob. custo-efetivo)
  - modelo_tornado.csv      (análise de sensibilidade univariada)
  - modelo_sc.xlsx          (todas as abas acima)

Uso (a partir da raiz do projeto):
  python custo_efetividade/modelo.py            # 5.000 iterações
  python custo_efetividade/modelo.py 20000      # N iterações
"""

import argparse
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SAIDA_DIR = os.path.join(PROJECT_DIR, "saida")

# ------------------------------------------------------------------
# PARÂMETROS EDITÁVEIS (placeholders de literatura — ajuste conforme evidência)
# ------------------------------------------------------------------
POPULACAO_SC = {
    "Criancas (0-14)": 1_370_000,   # IBGE 2022 (aproximado)
    "Adultos (15-59)": 4_720_000,
    "Idosos (60+)":    1_520_000,
}

# Cobertura vacinal (proporção da população vacinada)
COBERTURA = {
    "Criancas (0-14)": 0.80,
    "Adultos (15-59)": 0.60,
    "Idosos (60+)":    0.80,
}

# Custo por pessoa vacinada (dose + administração), em R$
CUSTO_VACINA = {
    "Criancas (0-14)": 80.0,
    "Adultos (15-59)": 80.0,
    "Idosos (60+)":    80.0,
}

# Custo REAL (econômico) da internação por SRAG, por faixa etária (R$).
# Placeholder — substituir por estudo de custo local. Inclui UTI e perda de
# produtividade, ao contrário do reembolso AIH (VAL_TOT do SIH).
CUSTO_HOSP_REAL = {
    "Criancas (0-14)": 8_000.0,
    "Adultos (15-59)": 14_000.0,
    "Idosos (60+)":    18_000.0,
}

# Eficácia contra HOSPITALIZAÇÃO por SRAG, por vírus (literatura).
# Influenza: 40–60% (Belongia 2016; Cochrane), menor em idosos.
# COVID-19: ~70% contra hospitalização grave (mRNA, pós-reforço).
# VSR infantil (nirsevimab): ~78% (MELODY/HARMONIE). VSR idoso (RSVpreF): ~80% (RENOIR).
VE_HOSP = {
    "Influenza": {"Criancas (0-14)": 0.55, "Adultos (15-59)": 0.45, "Idosos (60+)": 0.40},
    "COVID-19":  {"Criancas (0-14)": 0.60, "Adultos (15-59)": 0.70, "Idosos (60+)": 0.70},
    "VSR":       {"Criancas (0-14)": 0.78, "Adultos (15-59)": 0.00, "Idosos (60+)": 0.80},
    "Todos":     {"Criancas (0-14)": 0.60, "Adultos (15-59)": 0.60, "Idosos (60+)": 0.60},
}

# Eficácia adicional contra ÓBITO entre os ainda hospitalizados (conservador: 0)
VE_MORTE = 0.0

# Expectativa de vida restante (anos) para conversão em QALYs (aproximado)
EXPECTATIVA_VIDA = {"Criancas (0-14)": 75.0, "Adultos (15-59)": 35.0, "Idosos (60+)": 10.0}

# Limiar de disposição a pagar (R$ por QALY) — ~1 PIB per capita (CONITEC)
WTP_QALY = 120_000.0
PIB_PER_CAPITA = 55_000.0   # PIB per capita Brasil (aprox.; calibrar)
DISCOUNT_RATE = 0.03        # taxa de desconto anual dos QALYs futuros

VIRUS_ALVO = ["Influenza", "COVID-19", "VSR"]

# Incertezas para a PSA
SD_VE = 0.10          # desvio-padrão da eficácia (Beta)
SD_CUSTO = 0.20       # desvio-padrão relativo de custos (Gamma)


# ------------------------------------------------------------------
# HELPERS ESTATÍSTICOS
# ------------------------------------------------------------------
def beta_ab(mean, sd):
    """Método dos momentos para Beta(mean, sd), com proteção nas bordas 0/1."""
    mean = min(max(mean, 0.001), 0.999)
    sd = min(sd, np.sqrt(mean * (1 - mean)) / 2) if mean > 0 and mean < 1 else sd
    if sd <= 0:
        sd = 0.001
    k = mean * (1 - mean) / (sd ** 2) - 1
    k = max(k, 0.5)
    return mean * k, (1 - mean) * k


def gamma_par(mean, cv):
    """Parâmetros (shape, scale) de uma Gamma com média e coeficiente de variação."""
    sd = mean * cv
    shape = (mean / sd) ** 2
    scale = (sd ** 2) / mean
    return shape, scale


def _fator_anuidade(anos, taxa):
    """Soma descontada de 1 QALY por ano, por `anos` anos, à taxa `taxa`."""
    if anos <= 0:
        return 0.0
    if taxa <= 0:
        return float(anos)
    return (1 - (1 + taxa) ** (-anos)) / taxa


def _veredicto(neto, death_evit, icer_qaly, limiar):
    if neto < 0 and death_evit >= 0:
        return "Dominante (poupador)"
    if death_evit <= 0:
        return "Sem benefício"
    return "Custo-efetivo" if icer_qaly < limiar else "Não custo-efetivo"


# ------------------------------------------------------------------
# LEITURA E PREPARO DOS DADOS
# ------------------------------------------------------------------
def _ler_csv(nome):
    path = os.path.join(SAIDA_DIR, nome)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} não encontrado. Rode antes coleta.py e sivep_gripe.py."
        )
    return pd.read_csv(path, encoding="utf-8-sig")


def carregar_parametros():
    sivep = _ler_csv("sivep_gripe_agregado.csv")
    sih_res = _ler_csv("resumo_faixa_etaria.csv")

    sivep = sivep.copy()
    sivep["ano_limpo"] = sivep["ano"].astype(str).str.replace(r"\.0$", "", regex=True)
    contagem_anos = sivep.loc[sivep["ano_limpo"].str.len() == 4].groupby("ano_limpo")["casos"].sum()
    # descarta anos residuais (ex.: sintomas iniciados em dezembro do ano anterior)
    anos_validos = contagem_anos[contagem_anos >= max(100, contagem_anos.max() * 0.01)]
    n_anos = max(len(anos_validos), 1)

    # Custo médio de internação por faixa (SIH)
    custo_hosp = {}
    for _, row in sih_res.iterrows():
        custo_hosp[row["faixa_etaria"]] = float(row["custo_medio_internacao"])

    # Eventos por faixa x vírus (SIVEP)
    params = {}
    for faixa, grp in sivep.groupby("faixa_etaria", dropna=False):
        for virus, v in grp.groupby("virus", dropna=False):
            hosp = int(v["hospitalizados"].sum())
            uti = int(v["uti"].sum())
            obitos = int(v["obitos"].sum())
            casos = int(v["casos"].sum())
            params[(faixa, virus)] = {
                "hosp_anual": hosp / n_anos,
                "hosp_total": hosp,
                "p_uti": uti / hosp if hosp else 0.0,
                "p_death": obitos / hosp if hosp else 0.0,
                "casos_total": casos,
                "obitos_total": obitos,
            }
    return params, custo_hosp, n_anos


# ------------------------------------------------------------------
# ÁRVORE DE DECISÃO (determinística)
# ------------------------------------------------------------------
def arvore(n, h0, ve_hosp, cobertura, p_uti, p_death, custo_hosp, custo_vacina):
    """Retorna um dict com os desfechos esperados dos dois braços."""
    hosp0 = n * h0
    uti0 = hosp0 * p_uti
    death0 = hosp0 * p_death
    custo0 = hosp0 * custo_hosp

    hosp_v = n * h0 * (1 - ve_hosp * cobertura)
    uti_v = hosp_v * p_uti
    death_v = hosp_v * p_death
    custo_v = n * cobertura * custo_vacina + hosp_v * custo_hosp

    hosp_evit = hosp0 - hosp_v
    uti_evit = uti0 - uti_v
    death_evit = death0 - death_v
    custo_evit = custo0 - custo_v
    neto = custo_v - custo0
    return {
        "hosp0": hosp0, "hosp_v": hosp_v, "hosp_evit": hosp_evit,
        "uti_evit": uti_evit, "death0": death0, "death_v": death_v,
        "death_evit": death_evit, "custo0": custo0, "custo_v": custo_v,
        "custo_evit": custo_evit, "neto": neto,
    }


def cenarios_base(params, custo_hosp, n_anos, perspectiva="SUS", taxa_desconto=None):
    linhas = []
    virus_list = VIRUS_ALVO + ["Todos"]
    for faixa in POPULACAO_SC:
        n = POPULACAO_SC[faixa]
        for virus in virus_list:
            if virus == "Todos":
                # agregado = soma dos vírus-alvo (Influenza + COVID + VSR)
                h0 = sum(params.get((faixa, v), {}).get("hosp_anual", 0.0) for v in VIRUS_ALVO) / n
                hosp_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) for v in VIRUS_ALVO)
                uti_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) *
                                params.get((faixa, v), {}).get("p_uti", 0.0) for v in VIRUS_ALVO)
                obi_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) *
                                params.get((faixa, v), {}).get("p_death", 0.0) for v in VIRUS_ALVO)
                p_uti = uti_total / hosp_total if hosp_total else 0.0
                p_death = obi_total / hosp_total if hosp_total else 0.0
            else:
                p = params.get((faixa, virus), {"hosp_anual": 0.0, "p_uti": 0.0, "p_death": 0.0})
                h0 = p["hosp_anual"] / n
                p_uti = p["p_uti"]
                p_death = p["p_death"]

            ve = VE_HOSP[virus][faixa]
            r = arvore(n, h0, ve, COBERTURA[faixa], p_uti, p_death,
                       custo_hosp.get(faixa, 0.0), CUSTO_VACINA[faixa])
            taxa = DISCOUNT_RATE if taxa_desconto is None else taxa_desconto
            fator = _fator_anuidade(EXPECTATIVA_VIDA[faixa], taxa)
            qaly = r["death_evit"] * fator
            icer_death = r["neto"] / r["death_evit"] if r["death_evit"] > 0 else np.inf
            icer_qaly = r["neto"] / qaly if qaly > 0 else np.inf

            veredicto = _veredicto(r["neto"], r["death_evit"], icer_qaly, WTP_QALY)
            v_1x = _veredicto(r["neto"], r["death_evit"], icer_qaly, PIB_PER_CAPITA)
            v_3x = _veredicto(r["neto"], r["death_evit"], icer_qaly, 3 * PIB_PER_CAPITA)

            linhas.append({
                "perspectiva": perspectiva, "faixa_etaria": faixa, "virus": virus,
                "populacao": n, "hosp_anuais_sem_vac": r["hosp0"],
                "hosp_evitadas_ano": r["hosp_evit"], "uti_evitadas_ano": r["uti_evit"],
                "obitos_evitados_ano": r["death_evit"],
                "custo_vacinacao": r["custo_v"], "custo_hosp_evitado": r["custo_evit"],
                "custo_liquido": r["neto"],
                "ICER_R_por_obito": icer_death, "ICER_R_por_QALY": icer_qaly,
                "QALYs_ganhos": qaly, "veredicto": veredicto,
                "veredicto_1x_PIB": v_1x, "veredicto_3x_PIB": v_3x,
            })
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------
# MONTE CARLO (PSA)
# ------------------------------------------------------------------
def psa_amostras(params, custo_hosp, n_anos, n_iter, perspectiva="SUS", seed=42):
    """Gera as amostras da PSA (custo líquido, QALYs, óbitos e internações evitadas)."""
    rng = np.random.default_rng(seed)
    virus_list = VIRUS_ALVO + ["Todos"]
    amostras = []
    for faixa in POPULACAO_SC:
        n = POPULACAO_SC[faixa]
        for virus in virus_list:
            if virus == "Todos":
                h0_mean = sum(params.get((faixa, v), {}).get("hosp_anual", 0.0) for v in VIRUS_ALVO) / n
                hosp_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) for v in VIRUS_ALVO)
                uti_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) *
                                params.get((faixa, v), {}).get("p_uti", 0.0) for v in VIRUS_ALVO)
                obi_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) *
                                params.get((faixa, v), {}).get("p_death", 0.0) for v in VIRUS_ALVO)
                p_uti_mean = uti_total / hosp_total if hosp_total else 0.0
                p_death_mean = obi_total / hosp_total if hosp_total else 0.0
                a_uti, b_uti = beta_ab(p_uti_mean, 0.02)
                a_dth, b_dth = beta_ab(p_death_mean, 0.02)
            else:
                p = params.get((faixa, virus), {"hosp_anual": 0.0, "p_uti": 0.0, "p_death": 0.0})
                h0_mean = p["hosp_anual"] / n
                p_uti_mean = p["p_uti"]
                p_death_mean = p["p_death"]
                a_uti, b_uti = beta_ab(p_uti_mean, 0.02)
                a_dth, b_dth = beta_ab(p_death_mean, 0.02)

            events = max(h0_mean * n, 1e-9)
            a_h0, b_h0 = max(events + 1, 1), max(n - events + 1, 1)
            h0_s = rng.beta(a_h0, b_h0, n_iter)
            ve_mean = VE_HOSP[virus][faixa]
            a_ve, b_ve = beta_ab(ve_mean, SD_VE)
            ve_s = rng.beta(a_ve, b_ve, n_iter)
            cov = COBERTURA[faixa]
            p_uti_s = rng.beta(a_uti, b_uti, n_iter)
            p_death_s = rng.beta(a_dth, b_dth, n_iter)
            sh_c, sc_c = gamma_par(custo_hosp.get(faixa, 0.0), SD_CUSTO)
            custo_hosp_s = rng.gamma(sh_c, sc_c, n_iter)
            sh_v, sc_v = gamma_par(CUSTO_VACINA[faixa], SD_CUSTO)
            custo_vac_s = rng.gamma(sh_v, sc_v, n_iter)

            hosp0 = n * h0_s
            death0 = hosp0 * p_death_s
            custo0 = hosp0 * custo_hosp_s
            hosp_v = n * h0_s * (1 - ve_s * cov)
            death_v = hosp_v * p_death_s
            custo_v = n * cov * custo_vac_s + hosp_v * custo_hosp_s

            neto = custo_v - custo0
            fator = _fator_anuidade(EXPECTATIVA_VIDA[faixa], DISCOUNT_RATE)
            qaly = (death0 - death_v) * fator
            hosp_evit = hosp0 - hosp_v
            death_evit = death0 - death_v

            for i in range(n_iter):
                amostras.append((faixa, virus, perspectiva, i,
                                 neto[i], qaly[i], death_evit[i], hosp_evit[i]))
    return pd.DataFrame(amostras, columns=[
        "faixa_etaria", "virus", "perspectiva", "iter",
        "custo_liquido", "qaly", "obitos_evitados", "hosp_evitadas",
    ])


def resumo_psa(amostras):
    """Resume as amostras da PSA por cenário."""
    linhas = []
    for (faixa, virus, persp), g in amostras.groupby(["faixa_etaria", "virus", "perspectiva"]):
        neto = g["custo_liquido"].to_numpy()
        qaly = g["qaly"].to_numpy()
        obit = g["obitos_evitados"].to_numpy()
        linhas.append({
            "faixa_etaria": faixa, "virus": virus, "perspectiva": persp,
            "p_custo_poupador": float(np.mean(neto < 0)),
            "media_custo_liquido": float(np.mean(neto)),
            "media_obitos_evitados": float(np.mean(obit)),
            "media_QALYs": float(np.mean(qaly)),
            "ICER_medio_R_por_obito": float(np.mean(neto) / np.mean(obit)) if np.mean(obit) > 0 else np.inf,
            "p_efetivo_WTP": float(np.mean((neto - WTP_QALY * qaly) < 0)),
            "p_efetivo_1x_PIB": float(np.mean((neto - PIB_PER_CAPITA * qaly) < 0)),
            "p_efetivo_3x_PIB": float(np.mean((neto - 3 * PIB_PER_CAPITA * qaly) < 0)),
        })
    return pd.DataFrame(linhas)


def ceac(amostras, wtp_grid):
    """Probabilidade de ser custo-efetivo em cada limiar WTP, por cenário."""
    linhas = []
    for (faixa, virus, persp), g in amostras.groupby(["faixa_etaria", "virus", "perspectiva"]):
        neto = g["custo_liquido"].to_numpy()
        qaly = g["qaly"].to_numpy()
        for w in wtp_grid:
            linhas.append({
                "faixa_etaria": faixa, "virus": virus, "perspectiva": persp,
                "WTP": w, "p_efetivo": float(np.mean((neto - w * qaly) < 0)),
            })
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------
# SENSIBILIDADE UNIVARIADA (tornado)
# ------------------------------------------------------------------
def tornado(params, custo_hosp, perspectiva="SUS"):
    linhas = []
    delta = 0.20  # +/- 20%
    for faixa in POPULACAO_SC:
        n = POPULACAO_SC[faixa]
        h0 = sum(params.get((faixa, v), {}).get("hosp_anual", 0.0) for v in VIRUS_ALVO) / n
        hosp_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) for v in VIRUS_ALVO)
        uti_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) *
                        params.get((faixa, v), {}).get("p_uti", 0.0) for v in VIRUS_ALVO)
        obi_total = sum(params.get((faixa, v), {}).get("hosp_total", 0) *
                        params.get((faixa, v), {}).get("p_death", 0.0) for v in VIRUS_ALVO)
        base = {
            "n": n, "h0": h0, "ve": VE_HOSP["Todos"][faixa], "cov": COBERTURA[faixa],
            "p_uti": uti_total / hosp_total if hosp_total else 0.0,
            "p_death": obi_total / hosp_total if hosp_total else 0.0,
            "custo_hosp": custo_hosp.get(faixa, 0.0), "custo_vac": CUSTO_VACINA[faixa],
        }

        def neto_de(param, val):
            b = dict(base)
            b[param] = val
            r = arvore(b["n"], b["h0"], b["ve"], b["cov"], b["p_uti"], b["p_death"],
                       b["custo_hosp"], b["custo_vac"])
            return r["neto"]

        for param in ["h0", "ve", "cov", "p_uti", "p_death", "custo_hosp", "custo_vac"]:
            v0 = base[param]
            lo, hi = (v0 * (1 - delta), v0 * (1 + delta)) if v0 else (0.0, 0.0)
            if param == "ve" or param == "cov":
                lo, hi = max(0.0, v0 - delta), min(1.0, v0 + delta)
            n_lo, n_hi = neto_de(param, lo), neto_de(param, hi)
            linhas.append({
                "perspectiva": perspectiva, "faixa_etaria": faixa, "parametro": param,
                "valor_base": v0, "baixo": lo, "alto": hi,
                "custo_liquido_baixo": n_lo, "custo_liquido_alto": n_hi,
                "swing": abs(n_hi - n_lo),
            })
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Modelo de custo-efetividade SRAG/SC.")
    ap.add_argument("n_iter", nargs="?", type=int, default=5000)
    args = ap.parse_args()

    params, custo_hosp_sus, n_anos = carregar_parametros()
    print(f"Anos de SRAG considerados: {n_anos}", flush=True)

    base = pd.concat([
        cenarios_base(params, custo_hosp_sus, n_anos, "SUS"),
        cenarios_base(params, CUSTO_HOSP_REAL, n_anos, "Real"),
    ], ignore_index=True)

    amostras = pd.concat([
        psa_amostras(params, custo_hosp_sus, n_anos, args.n_iter, "SUS"),
        psa_amostras(params, CUSTO_HOSP_REAL, n_anos, args.n_iter, "Real"),
    ], ignore_index=True)
    psa_df = resumo_psa(amostras)
    torn = pd.concat([
        tornado(params, custo_hosp_sus, "SUS"),
        tornado(params, CUSTO_HOSP_REAL, "Real"),
    ], ignore_index=True)
    ceac_df = ceac(amostras, np.linspace(0, 300_000, 61))

    base.to_csv(os.path.join(SAIDA_DIR, "modelo_resultados.csv"), index=False, encoding="utf-8-sig")
    psa_df.to_csv(os.path.join(SAIDA_DIR, "modelo_psa_resumo.csv"), index=False, encoding="utf-8-sig")
    torn.to_csv(os.path.join(SAIDA_DIR, "modelo_tornado.csv"), index=False, encoding="utf-8-sig")
    ceac_df.to_csv(os.path.join(SAIDA_DIR, "modelo_ceac.csv"), index=False, encoding="utf-8-sig")

    try:
        with pd.ExcelWriter(os.path.join(SAIDA_DIR, "modelo_sc.xlsx"), engine="openpyxl") as w:
            base.to_excel(w, sheet_name="Resultados", index=False)
            psa_df.to_excel(w, sheet_name="PSA_resumo", index=False)
            torn.to_excel(w, sheet_name="Tornado", index=False)
            ceac_df.to_excel(w, sheet_name="CEAC", index=False)
        print("Planilha modelo_sc.xlsx gerada.", flush=True)
    except ImportError:
        pass

    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    print("\n=== Resultado base (por faixa x vírus x perspectiva) ===", flush=True)
    cols = ["perspectiva", "faixa_etaria", "virus", "obitos_evitados_ano",
            "custo_liquido", "ICER_R_por_QALY", "veredicto"]
    print(base[cols].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
