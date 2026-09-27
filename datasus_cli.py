"""
datasus_cli.py — Assistente interativo de linha de comando do DataSUS BI
=======================================================================

Uma alternativa ao Streamlit para quem prefere o terminal. Guia o usuário por
etapas amigáveis (bases, período, regiões, CID e variáveis) e gera o arquivo
com os dados já filtrados.

Interface
---------
Usa `questionary` (menus com setas, checkboxes e busca) quando disponível e cai
automaticamente para menus numerados via `input()` em terminais que não suportam
navegação. Assim funciona tanto no Windows Terminal/PowerShell quanto em SSH.

Motor de dados
--------------
Toda a coleta é feita pelo `datasus_engine` (staging em Parquet + DuckDB com
memória controlada). A CLI é apenas uma camada de conversa: nenhuma base inteira
fica na RAM.

Uso
---
    python datasus_cli.py                          # assistente interativo
    python datasus_cli.py --base SIH-RD --uf SC --ano-inicio 2020 --ano-fim 2024
    python datasus_cli.py --base SIM-DO,SINASC --uf SC,PR --ano-inicio 2021 \
                          --ano-fim 2023 --morbidades "Diabetes mellitus" \
                          --formato parquet --saida D:/dados

Dicas de teclado (modo questionary)
-----------------------------------
  ↑ ↓ ou j k   navegar
  ESPAÇO       marcar/desmarcar (checkbox)
  a            marcar/desmarcar todos (checkbox)
  /            buscar (listas com busca)
  ENTER        confirmar
  Ctrl+C       cancelar e sair
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from dataclasses import dataclass, field

# --- Encoding do console no Windows -----------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd  # noqa: E402

from data_ingestion import (  # noqa: E402
    SYSTEMS_CATALOG,
    SYSTEM_FAMILIES,
    get_systems_by_family,
    REGIOES_BR,
)
from metadata_catalog import get_metadata_for_system  # noqa: E402
from cid_catalog import (  # noqa: E402
    CID10_CHAPTERS,
    MORBIDITIES,
    build_cid_filter,
    search_cid10,
    system_supports_cid,
)

# ============================================================================
# Constantes
# ============================================================================

UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
]

MESES = [f"{m:02d}" for m in range(1, 13)]

FORMATOS = {
    "csv": "CSV (.csv) — abre no Excel, arquivo maior",
    "parquet": "Parquet (.parquet) — comprimido e rápido, ideal para reabrir em Python",
    "xlsx": "Excel (.xlsx) — atenção: limite de ~1 milhão de linhas",
}

LOTE_OPCOES = [5_000, 10_000, 25_000, 50_000, 100_000, 200_000]
MEM_OPCOES = ["512 MB", "1 GB", "2 GB", "4 GB", "8 GB"]

SAIDA_PADRAO = os.path.join(ROOT, "saidas_cli")

# ============================================================================
# Camada de UI (questionary com fallback para input())
# ============================================================================

try:
    import questionary

    HAS_Q = True
except Exception:  # pragma: no cover
    HAS_Q = False


class Cancelado(Exception):
    """Usuário cancelou (Ctrl+C / ESC)."""


def _checar(resposta):
    """questionary devolve None quando o usuário cancela."""
    if resposta is None:
        raise Cancelado()
    return resposta


def _num_fallback(titulo, opcoes, multi=False, default_idx=0):
    """Menu numerado via input(), para terminais sem suporte a navegação."""
    print(f"\n{titulo}")
    for i, (rotulo, _valor) in enumerate(opcoes, start=1):
        print(f"  {i:>2}) {rotulo}")
    if multi:
        print("  Digite os números separados por vírgula (ex.: 1,3,4), ou 't' para todos.")
    else:
        print(f"  Digite o número [ENTER = {default_idx + 1}].")

    while True:
        try:
            bruto = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            raise Cancelado()
        if not bruto and not multi:
            return [opcoes[default_idx][1]]
        if bruto.lower() == "t" and multi:
            return [v for _r, v in opcoes]
        partes = [p.strip() for p in bruto.split(",") if p.strip()]
        try:
            idxs = [int(p) for p in partes]
        except ValueError:
            print("  ⚠️  Digite apenas números.")
            continue
        if any(i < 1 or i > len(opcoes) for i in idxs):
            print(f"  ⚠️  Use números entre 1 e {len(opcoes)}.")
            continue
        if not multi:
            return [opcoes[idxs[0] - 1][1]]
        return [opcoes[i - 1][1] for i in idxs]


def perguntar_select(titulo, opcoes, default_idx=0, busca=False):
    """Seleção única. `opcoes` = [(rotulo, valor), ...]."""
    if not opcoes:
        raise Cancelado()
    if HAS_Q:
        escolhas = [questionary.Choice(title=r, value=v) for r, v in opcoes]
        resp = questionary.select(
            titulo, choices=escolhas, default=opcoes[default_idx][1],
            use_search_filter=busca, use_jk_keys=True, instruction="(↑↓ · ENTER)",
        ).ask()
        return _checar(resp)
    return _num_fallback(titulo, opcoes, multi=False, default_idx=default_idx)[0]


def perguntar_checkbox(titulo, opcoes, default_valores=None):
    """Seleção múltipla. Retorna lista de valores marcados."""
    if not opcoes:
        raise Cancelado()
    default_valores = default_valores or []
    if HAS_Q:
        escolhas = [
            questionary.Choice(title=r, value=v, checked=(v in default_valores))
            for r, v in opcoes
        ]
        resp = questionary.checkbox(
            titulo, choices=escolhas,
            instruction="(↑↓ · ESPAÇO marca · 'a' todos · ENTER confirma)",
        ).ask()
        return _checar(resp)
    return _num_fallback(titulo, opcoes, multi=True)


def perguntar_texto(titulo, default="", validar=None):
    """Entrada de texto livre, com validação opcional."""
    if not HAS_Q:
        try:
            bruto = input(f"\n{titulo}\n  [{default}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            raise Cancelado()
        valor = bruto or default
        if validar:
            erro = validar(valor)
            if erro:
                print(f"  ⚠️  {erro}")
                return perguntar_texto(titulo, default, validar)
        return valor

    resp = questionary.text(titulo, default=default, validate=validar or (lambda _t: True)).ask()
    return _checar(resp)


def perguntar_confirmacao(titulo, default=True):
    if HAS_Q:
        return bool(_checar(questionary.confirm(titulo, default=default).ask()))
    try:
        r = input(f"\n{titulo} [{'S/n' if default else 's/N'}] > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise Cancelado()
    return default if not r else r.startswith("s")


# ============================================================================
# Aparência
# ============================================================================

LARGURA = 74


def titulo_passo(n, total, texto):
    print()
    print("─" * LARGURA)
    print(f"  PASSO {n}/{total} — {texto}")
    print("─" * LARGURA)


def caixa(linhas):
    print()
    print("┌" + "─" * (LARGURA - 2) + "┐")
    for ln in linhas:
        for parte in textwrap.wrap(ln, LARGURA - 4) or [""]:
            print("│ " + parte.ljust(LARGURA - 4) + " │")
    print("└" + "─" * (LARGURA - 2) + "┘")


def banner():
    caixa([
        "DataSUS BI — Assistente de linha de comando",
        "",
        "Vou guiar você por algumas perguntas rápidas para montar sua base:",
        "bases → período → regiões → CID → variáveis → formato.",
        "",
        "Ctrl+C a qualquer momento cancela.",
    ])


def barra_progresso(pct, msg):
    largura = 32
    pct = max(0.0, min(1.0, float(pct)))
    cheio = int(largura * pct)
    barra = "█" * cheio + "░" * (largura - cheio)
    texto = (msg or "")[:44]
    sys.stdout.write(f"\r  [{barra}] {pct*100:5.1f}%  {texto:<44}")
    sys.stdout.flush()
    if pct >= 1.0:
        sys.stdout.write("\n")


# ============================================================================
# Configuração coletada
# ============================================================================

@dataclass
class Config:
    bases: list = field(default_factory=list)
    ufs: list = field(default_factory=list)
    municipio: list = field(default_factory=list)
    municipio_nome: str = ""
    ano_inicio: int = 2020
    ano_fim: int = 2024
    mes: str = "Todos"
    capitulos: list = field(default_factory=list)
    morbidades: list = field(default_factory=list)
    cids: list = field(default_factory=list)
    colunas: dict = field(default_factory=dict)   # {base: [colunas] | None}
    formato: str = "csv"
    saida: str = SAIDA_PADRAO
    memoria: str = "1 GB"
    lote: int = 50_000


# ============================================================================
# Etapas do assistente
# ============================================================================

def passo_bases(cfg, total):
    """Família -> bases. É o primeiro passo porque define todo o resto."""
    titulo_passo(1, total, "Quais bancos de dados você quer?")
    por_familia = get_systems_by_family()

    opcoes_fam = []
    for fam, itens in por_familia.items():
        nome = SYSTEM_FAMILIES.get(fam, {}).get("nome", fam)
        opcoes_fam.append((f"{nome}  ({len(itens)} bases)", fam))

    # Re-pergunta em vez de abortar: é comum apertar ENTER sem ter marcado nada.
    while True:
        familias = perguntar_checkbox("Família de dados:", opcoes_fam)
        if familias:
            break
        print("\n  ⚠️  Nada selecionado. Use ESPAÇO para marcar e ENTER para confirmar.")

    opcoes_base = []
    for fam in familias:
        for code, label in por_familia.get(fam, []):
            tipo = "mensal" if SYSTEMS_CATALOG[code]["type"] == "monthly" else "anual"
            opcoes_base.append((f"{label}  ·  {tipo}", code))

    while True:
        cfg.bases = perguntar_checkbox("\nQuais bases dentro dessas famílias?", opcoes_base)
        if cfg.bases:
            break
        print("\n  ⚠️  Nada selecionado. Use ESPAÇO para marcar e ENTER para confirmar.")


def passo_regioes(cfg, total):
    titulo_passo(2, total, "Onde? (regiões e estados)")

    opcoes_regiao = [(f"{r}  ({', '.join(ufs)})", r) for r, ufs in REGIOES_BR.items()]
    regioes_sel = perguntar_checkbox(
        "Região(ões) inteira(s) — opcional, pré-marca as UFs dela(s) "
        "(ESPAÇO marca, ENTER confirma mesmo sem marcar nada):",
        opcoes_regiao,
    )
    default_ufs = sorted({u for r in regioes_sel for u in REGIOES_BR[r]}) or ["SC"]

    opcoes_uf = [(uf, uf) for uf in UFS]
    while True:
        cfg.ufs = perguntar_checkbox(
            "Unidades da Federação (marque quantas quiser):", opcoes_uf,
            default_valores=default_ufs,
        )
        if cfg.ufs:
            break
        print("\n  ⚠️  Marque ao menos uma UF (ESPAÇO marca, ENTER confirma).")

    municipios_codigos, municipios_nomes = [], []
    if perguntar_confirmacao(
        f"Filtrar por município(s) dentro de {', '.join(cfg.ufs)}?", default=False
    ):
        opcoes_totais = []
        for uf in cfg.ufs:
            for cod, nome in _buscar_municipios(uf):
                opcoes_totais.append((f"{uf} - {nome}", cod))
        if not opcoes_totais:
            caixa(["⚠️  Não foi possível consultar os municípios do IBGE (offline?).",
                   "    Seguindo com o(s) estado(s) inteiro(s)."])
        else:
            while True:
                cod, nome = _escolher_municipio(opcoes_totais)
                if cod in municipios_codigos:
                    print(f"\n  ⚠️  {nome} já foi adicionado.")
                else:
                    municipios_codigos.append(cod)
                    municipios_nomes.append(nome)
                    print(f"\n  ✅ Adicionado: {nome}")
                if not perguntar_confirmacao("Adicionar outro município?", default=False):
                    break
    cfg.municipio = municipios_codigos
    cfg.municipio_nome = ", ".join(municipios_nomes)


def _buscar_municipios(uf):
    """Consulta a API do IBGE. Retorna [(codigo6, nome), ...] ou []."""
    try:
        import requests
        url = ("https://servicodados.ibge.gov.br/api/v1/localidades/"
               f"estados/{uf}/municipios")
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return [(str(m["id"])[:6], m["nome"]) for m in r.json()]
    except Exception:
        pass
    return []


def _escolher_municipio(opcoes):
    """Com muitos itens, prioriza a busca por texto."""
    opcoes_ordenadas = sorted(opcoes, key=lambda x: x[0])
    if HAS_Q:
        resp = perguntar_select(
            "\nDigite para buscar o município (barra '/' também busca):",
            opcoes_ordenadas, busca=True,
        )
        return resp, dict((c, n) for c, n in opcoes_ordenadas)[resp]
    lista = [(f"{n}  ({c})", c) for c, n in opcoes_ordenadas]
    cod = _num_fallback("\nMunicípio:", lista, multi=False)[0]
    return cod, dict((c, n) for c, n in opcoes_ordenadas)[cod]


def passo_periodo(cfg, total):
    titulo_passo(3, total, "Qual período?")

    def valida_ano(txt):
        t = (txt or "").strip()
        if not t.isdigit() or len(t) != 4:
            return "Digite um ano com 4 dígitos (ex.: 2020)."
        n = int(t)
        if n < 1996 or n > 2100:
            return "O DataSUS online começa em 1996."
        return True

    ini = int(perguntar_texto("Ano inicial:", "2020", valida_ano))
    fim_txt = perguntar_texto("Ano final:", str(ini), valida_ano)
    fim = int(fim_txt)
    if fim < ini:
        caixa([f"⚠️  Ano final ({fim}) menor que o inicial ({ini}). Usando {ini}."])
        fim = ini
    cfg.ano_inicio, cfg.ano_fim = ini, fim

    mensais = [b for b in cfg.bases if SYSTEMS_CATALOG[b]["type"] == "monthly"]
    if mensais:
        opcoes = [("Todos os meses", "Todos")] + [(f"Mês {m}", m) for m in MESES]
        cfg.mes = perguntar_select(
            f"\nMês (a(s) base(s) {', '.join(mensais)} são mensais):", opcoes,
        )
    else:
        cfg.mes = "Todos"


def passo_cid(cfg, total):
    titulo_passo(4, total, "Filtrar por CID-10 / morbidade?")
    com_cid = [b for b in cfg.bases if system_supports_cid(b)]

    if not com_cid:
        caixa(["ℹ️  Nenhuma das bases escolhidas tem campo de diagnóstico CID.",
               "    Pulando este passo (ex.: CNES, PNI)."])
        return

    if not perguntar_confirmacao(
        f"Aplicar filtro por CID? (vale para {', '.join(com_cid)})", default=False
    ):
        return

    caixa([
        "Escolha como filtrar. Você pode combinar as três formas:",
        "  • capítulos  — grandes grupos (ex.: IX Doenças do aparelho circulatório)",
        "  • morbidades — atalhos prontos (ex.: Diabetes, COVID-19, Dengue)",
        "  • códigos    — CID específico, com busca por nome",
    ])

    if perguntar_confirmacao("Selecionar por CAPÍTULOS da CID-10?", default=True):
        opcoes = [
            (f"{c['cap']:>4} — {c['titulo']}  [{c['range'][0]}..{c['range'][1]}]", c["cap"])
            for c in CID10_CHAPTERS
        ]
        cfg.capitulos = perguntar_checkbox("\nCapítulos:", opcoes)

    if perguntar_confirmacao("Selecionar por MORBIDADES prontas?", default=True):
        opcoes = [
            (f"{nome}  ({', '.join(codigos[:3])}{'...' if len(codigos) > 3 else ''})", nome)
            for nome, codigos in MORBIDITIES.items()
        ]
        cfg.morbidades = perguntar_checkbox("\nMorbidades:", opcoes)

    if perguntar_confirmacao("Informar CÓDIGOS específicos?", default=False):
        cfg.cids = _coletar_codigos()

    if not (cfg.capitulos or cfg.morbidades or cfg.cids):
        caixa(["⚠️  Nada foi selecionado — seguindo SEM filtro de CID."])


def _coletar_codigos():
    """Coleta códigos digitados e/ou escolhidos via busca por nome."""
    codigos = []
    modo = perguntar_select(
        "\nComo quer informar os CIDs?",
        [
            ("Digitar os códigos (ex.: I21, J45)", "digitar"),
            ("Buscar pelo nome da doença (catálogo oficial)", "buscar"),
        ],
    )

    if modo == "digitar":
        txt = perguntar_texto(
            "Códigos separados por vírgula:", "I21, I50",
            validar=lambda t: True if t.strip() else "Informe ao menos um código.",
        )
        codigos += [c.strip().upper() for c in txt.split(",") if c.strip()]
    else:
        while True:
            termo = perguntar_texto(
                "Buscar doença (ex.: infarto, dengue, asma):", "",
                validar=lambda t: True if len(t.strip()) >= 3 else "Digite ao menos 3 letras.",
            )
            achados = search_cid10(termo, limit=40)
            if not achados:
                print("  Nenhum CID encontrado. Tente outro termo.")
                if not perguntar_confirmacao("Buscar de novo?", default=True):
                    break
                continue
            opcoes = [(f"{cod} — {nome[:52]}", cod) for cod, nome in achados]
            escolhidos = perguntar_checkbox(f"\nResultados para '{termo}':", opcoes)
            codigos += escolhidos
            if not perguntar_confirmacao("Buscar mais CIDs?", default=False):
                break

    return sorted(set(codigos))


def passo_variaveis(cfg, total):
    titulo_passo(5, total, "Quais variáveis (colunas)?")
    for base in cfg.bases:
        meta = get_metadata_for_system(base)
        if not meta:
            cfg.colunas[base] = None
            continue

        rotulo = SYSTEMS_CATALOG[base]["label"]
        escolha = perguntar_select(
            f"\n{rotulo} — {len(meta)} variáveis disponíveis:",
            [
                ("Todas as variáveis (recomendado)", "todas"),
                ("Escolher uma a uma", "manual"),
            ],
        )
        if escolha == "todas":
            cfg.colunas[base] = None
            continue

        opcoes = [
            (f"{nome}  —  {info.get('desc', '')[:60]}  [{info.get('type', '')}]", nome)
            for nome, info in meta.items()
        ]
        sel = perguntar_checkbox(f"\nVariáveis de {base}:", opcoes)
        cfg.colunas[base] = sel or None


def passo_saida(cfg, total):
    titulo_passo(6, total, "Formato e destino")
    opcoes = [(texto, chave) for chave, texto in FORMATOS.items()]
    cfg.formato = perguntar_select("Formato do arquivo:", opcoes)

    if cfg.formato == "xlsx":
        caixa(["ℹ️  O Excel aceita ~1.048.576 linhas por aba.",
               "    Se a base for maior, vou avisar e sugerir CSV/Parquet."])

    cfg.saida = perguntar_texto("Pasta de saída:", cfg.saida)


def passo_memoria(cfg, total):
    titulo_passo(7, total, "Memória (bases grandes)")
    caixa([
        "A leitura é sempre feita em lotes e gravada em Parquet, então nenhuma base",
        "inteira fica na RAM. Ajuste abaixo só se o PC tiver pouca memória.",
    ])
    cfg.memoria = perguntar_select(
        "Teto de RAM do motor:",
        [(m + ("   (recomendado)" if m == "1 GB" else ""), m) for m in MEM_OPCOES],
        default_idx=MEM_OPCOES.index("1 GB"),
    )
    cfg.lote = perguntar_select(
        "Lote da ingestão (controla o pico de memória):",
        [(f"{v:,}".replace(",", ".") + " registros", v) for v in LOTE_OPCOES],
        default_idx=LOTE_OPCOES.index(50_000),
    )


def passo_resumo(cfg):
    total_ufs = len(cfg.ufs)
    linhas = [
        f"Bases        : {', '.join(cfg.bases)}",
        f"Regiões      : {', '.join(cfg.ufs)}" + (f"  ·  {cfg.municipio_nome}" if cfg.municipio_nome else ""),
        f"Período      : {cfg.ano_inicio}–{cfg.ano_fim}" + (f"  ·  mês {cfg.mes}" if cfg.mes != "Todos" else "  ·  todos os meses"),
        f"CID          : {_resumo_cid(cfg)}",
        f"Variáveis    : {_resumo_variaveis(cfg)}",
        f"Formato      : {cfg.formato}",
        f"Destino      : {cfg.saida}",
        f"Memória      : teto {cfg.memoria} · lote {cfg.lote:,}".replace(",", "."),
    ]
    caixa(["Resumo do que vou baixar:", ""] + linhas)
    return perguntar_confirmacao("Confirma e inicia o download?", default=True)


def _resumo_cid(cfg):
    partes = []
    if cfg.capitulos:
        partes.append(f"{len(cfg.capitulos)} capítulo(s)")
    if cfg.morbidades:
        partes.append(f"{len(cfg.morbidades)} morbidade(s)")
    if cfg.cids:
        partes.append(f"{len(cfg.cids)} código(s): {', '.join(cfg.cids[:6])}"
                      + ("..." if len(cfg.cids) > 6 else ""))
    return " + ".join(partes) if partes else "sem filtro"


def _resumo_variaveis(cfg):
    manuais = [b for b, v in cfg.colunas.items() if v]
    if not manuais:
        return "todas"
    return f"{len(manuais)} base(s) com seleção manual"


# ============================================================================
# Execução
# ============================================================================

def _nome_arquivo(cfg, base):
    partes = [base, "+".join(cfg.ufs)]
    if cfg.municipio_nome:
        partes.append(cfg.municipio_nome)
    periodo = f"{cfg.ano_inicio}" if cfg.ano_inicio == cfg.ano_fim else f"{cfg.ano_inicio}-{cfg.ano_fim}"
    partes.append(periodo)
    if cfg.mes != "Todos":
        partes.append(cfg.mes)
    if cfg.capitulos or cfg.morbidades or cfg.cids:
        partes.append("cid")
    nome = "_".join(str(p) for p in partes)
    nome = "".join(c for c in nome if c.isalnum() or c in "_-.+")
    return nome


def _exportar(df, caminho_base, formato):
    """Grava o DataFrame no formato pedido. Retorna (caminho, aviso|None)."""
    os.makedirs(os.path.dirname(caminho_base) or ".", exist_ok=True)
    if formato == "parquet":
        caminho = caminho_base + ".parquet"
        df.to_parquet(caminho, index=False)
        return caminho, None
    if formato == "xlsx":
        caminho = caminho_base + ".xlsx"
        limite = 1_048_576
        if len(df) >= limite:
            caminho = caminho_base + ".csv"
            df.to_csv(caminho, index=False, encoding="utf-8-sig")
            return caminho, (f"⚠️  {len(df):,} linhas excedem o limite do Excel — "
                             f"salvo como CSV.".replace(",", "."))
        df.to_excel(caminho, index=False)
        return caminho, None
    caminho = caminho_base + ".csv"
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho, None


def executar(cfg):
    from datasus_engine import load_full_datasus

    os.makedirs(cfg.saida, exist_ok=True)

    cid_filter = None
    if cfg.capitulos or cfg.morbidades or cfg.cids:
        cid_filter = build_cid_filter(
            selected_chapters=cfg.capitulos,
            selected_morbidities=cfg.morbidades,
            custom_codes=cfg.cids,
        )

    gerados, falhas = [], []

    for i, base in enumerate(cfg.bases, start=1):
        rotulo = SYSTEMS_CATALOG[base]["label"]
        print()
        print("═" * LARGURA)
        print(f"  [{i}/{len(cfg.bases)}] {rotulo}")
        print("═" * LARGURA)

        try:
            df = load_full_datasus(
                system_code=base,
                uf=cfg.ufs,
                year_start=cfg.ano_inicio,
                year_end=cfg.ano_fim,
                month=cfg.mes,
                city_code=cfg.municipio,
                columns_to_keep=cfg.colunas.get(base),
                cid_filter=cid_filter,
                progress_callback=barra_progresso,
                memory_limit=cfg.memoria,
                batch_size=cfg.lote,
            )
        except Exception as e:
            falhas.append((base, str(e)))
            print(f"\n  ❌ Falha em {base}: {e}")
            continue

        if df is None or df.empty:
            print(f"\n  ⚠️  {base}: nenhum registro para os filtros escolhidos.")
            continue

        caminho, aviso = _exportar(df, os.path.join(cfg.saida, _nome_arquivo(cfg, base)), cfg.formato)
        gerados.append((base, caminho, len(df), len(df.columns)))
        print(f"\n  ✅ {len(df):,} linhas × {len(df.columns)} colunas".replace(",", "."))
        if aviso:
            print(f"  {aviso}")
        print(f"  📁 {caminho}")

    return gerados, falhas


# ============================================================================
# Modo não-interativo
# ============================================================================

def config_de_args(args):
    """Monta a Config a partir das flags. Retorna None se faltar o essencial."""
    faltando = []
    if not args.base:
        faltando.append("--base")
    if not args.uf and not args.regiao:
        faltando.append("--uf ou --regiao")
    if args.ano_inicio is None:
        faltando.append("--ano-inicio")
    if faltando:
        print(f"❌ Para o modo não-interativo informe também: {', '.join(faltando)}")
        return None

    bases = [b.strip() for b in args.base.split(",") if b.strip()]
    invalidas = [b for b in bases if b not in SYSTEMS_CATALOG]
    if invalidas:
        print(f"❌ Base(s) desconhecida(s): {', '.join(invalidas)}")
        print(f"   Disponíveis: {', '.join(sorted(SYSTEMS_CATALOG)[:12])} ...")
        return None

    regioes_invalidas = [
        r.strip() for r in (args.regiao or "").split(",")
        if r.strip() and r.strip() not in REGIOES_BR
    ]
    if regioes_invalidas:
        print(f"❌ Região(ões) desconhecida(s): {', '.join(regioes_invalidas)}")
        print(f"   Disponíveis: {', '.join(REGIOES_BR)}")
        return None

    cfg = Config()
    cfg.bases = bases
    ufs_de_regiao = {u for r in (args.regiao or "").split(",") if r.strip() in REGIOES_BR
                     for u in REGIOES_BR[r.strip()]}
    ufs_diretas = {u.strip().upper() for u in (args.uf or "").split(",") if u.strip()}
    cfg.ufs = sorted(ufs_diretas | ufs_de_regiao)
    cfg.ano_inicio = args.ano_inicio
    cfg.ano_fim = args.ano_fim if args.ano_fim is not None else args.ano_inicio
    if cfg.ano_fim < cfg.ano_inicio:
        cfg.ano_fim = cfg.ano_inicio
    cfg.mes = args.mes or "Todos"
    cfg.capitulos = [c.strip() for c in (args.capitulos or "").split(",") if c.strip()]
    cfg.morbidades = [m.strip() for m in (args.morbidades or "").split(",") if m.strip()]
    cfg.cids = [c.strip().upper() for c in (args.cids or "").split(",") if c.strip()]
    cfg.formato = args.formato
    cfg.memoria = args.memoria or "1 GB"
    cfg.lote = args.lote or 50_000

    cfg.saida = args.saida or SAIDA_PADRAO
    if not os.path.isabs(cfg.saida):
        cfg.saida = os.path.abspath(cfg.saida)

    if args.municipio:
        cfg.municipio = [c.strip() for c in args.municipio.split(",") if c.strip()]
        cfg.municipio_nome = ", ".join(cfg.municipio)

    # Colunas: por padrão todas; --colunas aplica a todas as bases informadas.
    for b in cfg.bases:
        cfg.colunas[b] = None
    if args.colunas:
        cols = [c.strip() for c in args.colunas.split(",") if c.strip()]
        for b in cfg.bases:
            cfg.colunas[b] = cols

    return cfg


def validar_morbidades(nomes):
    """Confere nomes de morbidade (evita erro silencioso de digitação)."""
    desconhecidas = [m for m in nomes if m not in MORBIDITIES]
    if desconhecidas:
        print(f"⚠️  Morbidade(s) não reconhecida(s): {', '.join(desconhecidas)}")
        print(f"   Use --listar para ver os nomes válidos.")
        return False
    return True


def listar_opcoes():
    print("\n=== FAMÍLIAS E BASES ===")
    for fam, itens in get_systems_by_family().items():
        print(f"\n{fam}:")
        for code, label in itens:
            print(f"  {code:<12} {label}")
    print("\n=== MORBIDADES (use o nome exato em --morbidades) ===")
    for nome in MORBIDITIES:
        print(f"  {nome}")
    print("\n=== CAPÍTULOS CID-10 (use o código romano em --capitulos) ===")
    for c in CID10_CHAPTERS:
        print(f"  {c['cap']:<6} {c['titulo']}")
    print("\n=== UFs ===")
    print("  " + ", ".join(UFS))
    print("\n=== REGIÕES (use em --regiao) ===")
    for regiao, ufs in REGIOES_BR.items():
        print(f"  {regiao:<14} {', '.join(ufs)}")
    print()


# ============================================================================
# main
# ============================================================================

def montar_parser():
    ap = argparse.ArgumentParser(
        prog="datasus_cli.py",
        description="Assistente DataSUS BI — selecione bases, período, regiões e CID.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Exemplos:
              python datasus_cli.py                       # assistente interativo
              python datasus_cli.py --listar              # ver bases, morbidades e capítulos
              python datasus_cli.py --base SIH-RD --uf SC --ano-inicio 2020 --ano-fim 2024
              python datasus_cli.py --base SIM-DO,SINASC --uf SC,PR --ano-inicio 2021 \\
                    --ano-fim 2023 --morbidades "Diabetes mellitus" --formato parquet
              python datasus_cli.py --base SIH-RD --uf SC --ano-inicio 2022 \\
                    --capitulos IX --cids I21 --colunas N_AIH,DIAG_PRINC,VAL_TOT
              python datasus_cli.py --base SIH-RD --regiao Sul --ano-inicio 2022  # estado(s) de uma região inteira
        """),
    )
    ap.add_argument("--listar", action="store_true",
                    help="Lista bases, morbidades, capítulos e UFs e sai")
    ap.add_argument("--base", help="Base(s) separadas por vírgula (ex.: SIH-RD,SIM-DO)")
    ap.add_argument("--uf", help="UF(s) separadas por vírgula (ex.: SC,PR)")
    ap.add_argument("--regiao", help="Região(ões) separadas por vírgula "
                    f"({', '.join(REGIOES_BR)}) — soma as UFs dela(s) às de --uf")
    ap.add_argument("--municipio", help="Código(s) IBGE de 6 dígitos, separados por vírgula")
    ap.add_argument("--ano-inicio", type=int)
    ap.add_argument("--ano-fim", type=int)
    ap.add_argument("--mes", help="01..12 (só para bases mensais; padrão: todos)")
    ap.add_argument("--capitulos", help="Capítulos CID-10 separados por vírgula (ex.: IX,X)")
    ap.add_argument("--morbidades", help='Nomes de morbidade (ex.: "Diabetes mellitus,Dengue")')
    ap.add_argument("--cids", help="Códigos CID separados por vírgula (ex.: I21,J45)")
    ap.add_argument("--colunas", help="Variáveis separadas por vírgula (padrão: todas)")
    ap.add_argument("--formato", choices=list(FORMATOS), default="csv")
    ap.add_argument("--saida", help=f"Pasta de saída (padrão: {SAIDA_PADRAO})")
    ap.add_argument("--memoria", help="Teto de RAM do motor (ex.: 512MB, 1GB, 2GB)")
    ap.add_argument("--lote", type=int, help="Registros por lote (padrão: 50000)")
    return ap


def main():
    args = montar_parser().parse_args()

    if args.listar:
        listar_opcoes()
        return 0

    # Trabalha a partir da raiz do projeto: assim o staging em `data/staging`
    # é o mesmo usado pelo app Streamlit e pelos outros scripts.
    os.chdir(ROOT)

    try:
        if args.base:
            cfg = config_de_args(args)
            if cfg is None:
                return 2
            if cfg.morbidades and not validar_morbidades(cfg.morbidades):
                return 2
            caixa(["Modo não-interativo"] + [
                f"Bases     : {', '.join(cfg.bases)}",
                f"Regiões   : {', '.join(cfg.ufs)}",
                f"Período   : {cfg.ano_inicio}–{cfg.ano_fim}",
                f"Formato   : {cfg.formato}",
                f"Destino   : {cfg.saida}",
            ])
        else:
            banner()
            cfg = Config()
            TOTAL = 7
            passo_bases(cfg, TOTAL)
            passo_regioes(cfg, TOTAL)
            passo_periodo(cfg, TOTAL)
            passo_cid(cfg, TOTAL)
            passo_variaveis(cfg, TOTAL)
            passo_saida(cfg, TOTAL)
            passo_memoria(cfg, TOTAL)
            if not passo_resumo(cfg):
                print("\n  Cancelado pelo usuário.")
                return 1

        gerados, falhas = executar(cfg)

    except Cancelado:
        print("\n\n  Cancelado pelo usuário.")
        return 1
    except KeyboardInterrupt:
        print("\n\n  Interrompido (Ctrl+C).")
        return 1

    print()
    print("═" * LARGURA)
    if gerados:
        print(f"  ✅ Concluído — {len(gerados)} arquivo(s) gerado(s):")
        for base, caminho, n, c in gerados:
            print(f"     • {base}: {n:,} linhas × {c} colunas".replace(",", "."))
            print(f"       {caminho}")
    if falhas:
        print(f"\n  ⚠️  {len(falhas)} base(s) com falha:")
        for base, erro in falhas:
            print(f"     • {base}: {erro}")
    if not gerados and not falhas:
        print("  ⚠️  Nenhum dado retornado para os filtros escolhidos.")
    print("═" * LARGURA)

    try:
        from datasus_engine import clear_temp, close_connections
        close_connections()
        clear_temp()
    except Exception:
        pass

    return 0 if gerados else 3


if __name__ == "__main__":
    sys.exit(main())
