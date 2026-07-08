"""
Catálogo CID-10 e utilitários de filtragem por morbidade.

Permite filtrar os dados do DataSUS por:
- Capítulos CID-10 (grandes grupos de doenças, ex: "IX — Aparelho circulatório")
- Morbidades comuns pré-mapeadas (ex: "Diabetes mellitus" -> E10..E14)
- Códigos CID específicos digitados pelo usuário (ex: "I21", "J45", "A90")

A filtragem é aplicada nos campos de diagnóstico de cada sistema DataSUS.
"""

import csv
import os
from functools import lru_cache

# ================================================================
# Capítulos oficiais da CID-10 (com faixas de códigos)
# ================================================================
CID10_CHAPTERS = [
    {"cap": "I",     "titulo": "Algumas doenças infecciosas e parasitárias",            "range": ("A00", "B99")},
    {"cap": "II",    "titulo": "Neoplasias (tumores)",                                   "range": ("C00", "D48")},
    {"cap": "III",   "titulo": "Doenças do sangue e transtornos imunitários",           "range": ("D50", "D89")},
    {"cap": "IV",    "titulo": "Doenças endócrinas, nutricionais e metabólicas",         "range": ("E00", "E90")},
    {"cap": "V",     "titulo": "Transtornos mentais e comportamentais",                  "range": ("F00", "F99")},
    {"cap": "VI",    "titulo": "Doenças do sistema nervoso",                             "range": ("G00", "G99")},
    {"cap": "VII",   "titulo": "Doenças do olho e anexos",                               "range": ("H00", "H59")},
    {"cap": "VIII",  "titulo": "Doenças do ouvido e da apófise mastoide",                "range": ("H60", "H95")},
    {"cap": "IX",    "titulo": "Doenças do aparelho circulatório",                       "range": ("I00", "I99")},
    {"cap": "X",     "titulo": "Doenças do aparelho respiratório",                       "range": ("J00", "J99")},
    {"cap": "XI",    "titulo": "Doenças do aparelho digestivo",                          "range": ("K00", "K93")},
    {"cap": "XII",   "titulo": "Doenças da pele e do tecido subcutâneo",                 "range": ("L00", "L99")},
    {"cap": "XIII",  "titulo": "Doenças osteomusculares e do tecido conjuntivo",         "range": ("M00", "M99")},
    {"cap": "XIV",   "titulo": "Doenças do aparelho geniturinário",                      "range": ("N00", "N99")},
    {"cap": "XV",    "titulo": "Gravidez, parto e puerpério",                            "range": ("O00", "O99")},
    {"cap": "XVI",   "titulo": "Afecções originadas no período perinatal",               "range": ("P00", "P96")},
    {"cap": "XVII",  "titulo": "Malformações congênitas e anomalias cromossômicas",      "range": ("Q00", "Q99")},
    {"cap": "XVIII", "titulo": "Sintomas, sinais e achados anormais",                    "range": ("R00", "R99")},
    {"cap": "XIX",   "titulo": "Lesões, envenenamentos e causas externas",               "range": ("S00", "T98")},
    {"cap": "XX",    "titulo": "Causas externas de morbidade e mortalidade",             "range": ("V01", "Y98")},
    {"cap": "XXI",   "titulo": "Fatores que influenciam o estado de saúde",              "range": ("Z00", "Z99")},
    {"cap": "XXII",  "titulo": "Códigos para propósitos especiais",                      "range": ("U00", "U99")},
]

# ================================================================
# Morbidades comuns mapeadas para prefixos CID-10
# ================================================================
MORBIDITIES = {
    "Diabetes mellitus":                       ["E10", "E11", "E12", "E13", "E14"],
    "Hipertensão arterial":                    ["I10", "I11", "I12", "I13", "I15"],
    "Infarto agudo do miocárdio":              ["I21", "I22"],
    "Insuficiência cardíaca":                  ["I50"],
    "Doenças cerebrovasculares (AVC)":         ["I60", "I61", "I62", "I63", "I64", "I65", "I66", "I67", "I68", "I69"],
    "DPOC (bronquite/enfisema)":               ["J40", "J41", "J42", "J43", "J44"],
    "Asma":                                    ["J45", "J46"],
    "Pneumonia":                               ["J12", "J13", "J14", "J15", "J16", "J17", "J18"],
    "COVID-19":                                ["U071", "U072", "B342"],
    "Tuberculose":                             ["A15", "A16", "A17", "A18", "A19"],
    "Dengue":                                  ["A90", "A91"],
    "Zika":                                    ["A928"],
    "Chikungunya":                             ["A920"],
    "HIV / AIDS":                              ["B20", "B21", "B22", "B23", "B24"],
    "Sífilis":                                 ["A50", "A51", "A52", "A53"],
    "Sepse":                                   ["A40", "A41"],
    "Neoplasia maligna da mama":               ["C50"],
    "Neoplasia maligna de pulmão/brônquios":   ["C33", "C34"],
    "Neoplasia maligna do colo do útero":      ["C53"],
    "Neoplasia maligna da próstata":           ["C61"],
    "Neoplasia maligna do estômago":           ["C16"],
    "Neoplasia maligna do cólon/reto":         ["C18", "C19", "C20"],
    "Depressão":                               ["F32", "F33"],
    "Transtornos por uso de álcool":           ["F10"],
    "Doença renal crônica":                    ["N18"],
    "Obesidade":                               ["E66"],
    "Desnutrição":                             ["E40", "E41", "E42", "E43", "E44", "E45", "E46"],
    "Malformações congênitas (todas)":         ["Q"],
    "Agressões / homicídios":                  ["X85", "X86", "X87", "X88", "X89", "X90", "X91",
                                                "X92", "X93", "X94", "X95", "X96", "X97", "X98", "X99",
                                                "Y00", "Y01", "Y02", "Y03", "Y04", "Y05", "Y06", "Y07",
                                                "Y08", "Y09"],
    "Lesões autoprovocadas / suicídio":        ["X60", "X61", "X62", "X63", "X64", "X65", "X66", "X67",
                                                "X68", "X69", "X70", "X71", "X72", "X73", "X74", "X75",
                                                "X76", "X77", "X78", "X79", "X80", "X81", "X82", "X83", "X84"],
    "Acidentes de transporte":                 ["V"],
}

# ================================================================
# Catálogo CID-10 completo (código -> nome da doença)
# Fonte: tabela oficial CID10.DBF do DATASUS (14k+ códigos), gerada em cid10.csv
# ================================================================
_CID10_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cid10.csv")


@lru_cache(maxsize=1)
def load_cid10_catalog():
    """
    Carrega o catálogo CID-10 completo do arquivo cid10.csv.

    Returns:
        list[tuple[str, str]]: lista de (código, nome da doença), ordenada por código.
        Retorna [] se o arquivo não existir.
    """
    if not os.path.exists(_CID10_CSV):
        return []
    catalog = []
    with open(_CID10_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("code") or "").strip().upper()
            name = (row.get("name") or "").strip()
            if code and name:
                catalog.append((code, name))
    return catalog


def cid10_label(code, name):
    """Formata um item do catálogo como 'CÓDIGO — Nome da doença'."""
    return f"{code} — {name}"


def search_cid10(query, limit=300):
    """
    Busca códigos CID-10 por código ou por nome da doença.

    Args:
        query: texto de busca (código como 'I21' ou parte do nome como 'infarto').
        limit: número máximo de resultados retornados.

    Returns:
        list[tuple[str, str]]: lista de (código, nome) que casam com a busca.
        Se query for vazio, retorna os primeiros `limit` itens do catálogo.
    """
    catalog = load_cid10_catalog()
    q = _normalize(query) if query else ""
    if not q:
        return catalog[:limit]

    # busca por prefixo de código e por substring no nome (sem acento/caixa)
    q_name = query.strip().lower()
    results = []
    for code, name in catalog:
        if code.startswith(q) or q_name in name.lower():
            results.append((code, name))
            if len(results) >= limit:
                break
    return results


# ================================================================
# Campos que contêm códigos CID-10 em cada sistema
# ================================================================
CID_FIELDS_BY_SYSTEM = {
    "SIM-DO": ["CAUSABAS", "CAUSABAS_O"],
    "SINASC": ["CODANOMAL"],
    "SIH-RD": ["DIAG_PRINC", "DIAG_SECUN"],
    "SIA-PA": ["PA_CIDPRI", "PA_CIDSEC", "PA_CIDCAS"],
    "CIHA":   ["DIAG_PRINC", "DIAG_SECUN"],
}


def get_cid_fields(system_code):
    """Retorna a lista de campos com código CID-10 de um sistema (ou [] se não houver)."""
    if system_code in CID_FIELDS_BY_SYSTEM:
        return CID_FIELDS_BY_SYSTEM[system_code]
    if system_code.startswith("SINAN-"):
        return ["ID_AGRAVO"]
    # SIH-RJ/SP espelham os campos de diagnóstico da AIH; ER pode não ter (ignorado se ausente)
    if system_code.startswith("SIH-"):
        return ["DIAG_PRINC", "DIAG_SECUN", "SP_CIDPRI", "SP_CIDSEC"]
    # Grupos APAC/RAAS do SIA usam AP_CID*; PA usa PA_CID* (candidatos seguros se ausentes)
    if system_code.startswith("SIA-"):
        return ["PA_CIDPRI", "PA_CIDSEC", "PA_CIDCAS", "AP_CIDPRI", "AP_CIDSEC", "AP_CIDCAS"]
    return []


def system_supports_cid(system_code):
    """Indica se o sistema possui algum campo de diagnóstico CID-10."""
    return len(get_cid_fields(system_code)) > 0


def _normalize(code):
    """Normaliza um código CID: maiúsculo, sem pontos/espaços."""
    if code is None:
        return ""
    return str(code).strip().upper().replace(".", "").replace(" ", "")


def _cid_to_int(code):
    """
    Converte os 3 primeiros caracteres de um código CID (letra + 2 dígitos)
    em um inteiro comparável para checagem de faixa.
    Ex: 'A00' -> 0, 'B99' -> 199, 'I21' -> 821.
    Retorna None se o código não começar com letra.
    """
    code = _normalize(code)
    if not code or not code[0].isalpha():
        return None
    letter = code[0]
    digits = ""
    for ch in code[1:3]:
        if ch.isdigit():
            digits += ch
        else:
            break
    num = int(digits) if digits else 0
    return (ord(letter) - ord("A")) * 100 + num


def build_cid_filter(selected_chapters=None, selected_morbidities=None, custom_codes=None):
    """
    Constrói a estrutura de filtro a partir das seleções da interface.

    Args:
        selected_chapters: lista de códigos de capítulo (ex: ["IX", "X"])
        selected_morbidities: lista de nomes de morbidade (chaves de MORBIDITIES)
        custom_codes: lista de códigos CID digitados (ex: ["I21", "J45"])

    Returns:
        dict: {"ranges": [(lo, hi), ...], "prefixes": [str, ...], "active": bool}
    """
    ranges = []
    prefixes = []

    for cap in (selected_chapters or []):
        chap = next((c for c in CID10_CHAPTERS if c["cap"] == cap), None)
        if chap:
            lo = _cid_to_int(chap["range"][0])
            hi = _cid_to_int(chap["range"][1])
            if lo is not None and hi is not None:
                ranges.append((lo, hi))

    for morb in (selected_morbidities or []):
        for code in MORBIDITIES.get(morb, []):
            norm = _normalize(code)
            if norm:
                prefixes.append(norm)

    for code in (custom_codes or []):
        norm = _normalize(code)
        if norm:
            prefixes.append(norm)

    prefixes = sorted(set(prefixes))
    return {"ranges": ranges, "prefixes": prefixes, "active": bool(ranges or prefixes)}


def _code_matches(code, ranges, prefixes):
    """Verifica se um código CID casa com algum prefixo ou faixa selecionada."""
    if not code or code in ("NAN", "NONE"):
        return False
    if prefixes and code.startswith(prefixes):
        return True
    if ranges:
        ci = _cid_to_int(code)
        if ci is not None:
            for lo, hi in ranges:
                if lo <= ci <= hi:
                    return True
    return False


def filter_dataframe_by_cid(df, system_code, cid_filter):
    """
    Filtra um DataFrame mantendo apenas as linhas cujo CID (em qualquer campo
    de diagnóstico do sistema) casa com o filtro.

    - Se o filtro estiver inativo ou o sistema não tiver campos CID, retorna df inalterado.
    - Aplica match em CID principal E secundário (basta um casar).
    """
    if df is None or df.empty:
        return df
    if not cid_filter or not cid_filter.get("active"):
        return df

    fields = [f for f in get_cid_fields(system_code) if f in df.columns]
    if not fields:
        return df

    import pandas as pd

    ranges = cid_filter.get("ranges", [])
    prefixes = tuple(cid_filter.get("prefixes", []))

    mask = pd.Series(False, index=df.index)
    for field in fields:
        col = (
            df[field].astype(str)
            .str.upper()
            .str.replace(".", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.strip()
        )
        # Calcula o match sobre os valores únicos (muito mais rápido em bases grandes)
        matched_vals = {v for v in col.unique() if _code_matches(v, ranges, prefixes)}
        if matched_vals:
            mask = mask | col.isin(matched_vals)

    return df[mask]


def make_cid_record_matcher(system_code, cid_filter):
    """
    Cria um matcher por registro (dict) para filtragem em streaming, sem carregar
    o DataFrame inteiro na memória.

    Retorna (fields, matcher):
      - fields: lista de campos CID do sistema (para referência)
      - matcher: função(record_dict) -> bool, ou None se o filtro estiver inativo
                 ou o sistema não tiver campos CID.
    """
    if not cid_filter or not cid_filter.get("active"):
        return [], None
    fields = get_cid_fields(system_code)
    if not fields:
        return [], None

    ranges = cid_filter.get("ranges", [])
    prefixes = tuple(cid_filter.get("prefixes", []))

    def matcher(record):
        for f in fields:
            if f in record:
                if _code_matches(_normalize(record[f]), ranges, prefixes):
                    return True
        return False

    return fields, matcher

