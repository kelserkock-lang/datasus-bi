"""
Ligação (linkage) de registros por paciente entre bases DataSUS.

Duas estratégias:

1. EXATA (determinística) — quando existe uma chave única compartilhada:
   - SIH-RD ↔ SIH-SP pelo número da AIH (N_AIH / SP_NAIH) → mesma internação.
   - Registros APAC do SIA pelo CNS do paciente criptografado (AP_CNSPCN).
   Essas chaves são tratadas pelo join normal (chave única) da aplicação.

2. APROXIMADA (probabilística) — quando NÃO há identificador único de paciente
   compartilhado (o caso de cruzar SIA com SIH). Faz o pareamento por uma
   combinação de quase-identificadores harmonizados:
   município de residência + sexo + data de nascimento/idade + CEP.

   ⚠️ O resultado é "provável mesmo paciente", NÃO uma identificação garantida.
   Pode gerar correspondências múltiplas (um-para-muitos). Use com cautela em
   análises epidemiológicas e sempre reporte a metodologia como pareamento
   probabilístico por quase-identificadores.
"""

import re

# ================================================================
# Quase-identificadores de paciente por sistema (nomes REAIS dos campos DBF)
# canonical -> nome do campo no sistema
# ================================================================
PATIENT_QUASI_IDENTIFIERS = {
    "SIM-DO":   {"municipio": "CODMUNRES", "sexo": "SEXO", "nascimento": "DTNASC", "idade": "IDADE"},
    "SINASC":   {"municipio": "CODMUNRES", "sexo": "SEXO", "nascimento": "DTNASC"},
    "SIH-RD":   {"municipio": "MUNIC_RES", "sexo": "SEXO", "nascimento": "NASC", "idade": "IDADE", "cep": "CEP"},
    "SIA-PA":   {"municipio": "PA_MUNPCN", "sexo": "PA_SEXO", "idade": "PA_IDADE"},
    "SIA-APAC": {"municipio": "AP_MUNPCN", "sexo": "AP_SEXO", "idade": "AP_NUIDADE",
                 "cep": "AP_CEPPCN", "cns": "AP_CNSPCN"},
    "CIHA":     {"municipio": "MUNIC_RES", "sexo": "SEXO", "nascimento": "NASC"},
}

CANONICAL_LABELS = {
    "municipio":  "Município de residência",
    "sexo":       "Sexo",
    "nascimento": "Data de nascimento",
    "idade":      "Idade",
    "cep":        "CEP",
    "cns":        "CNS do paciente (criptografado)",
}

# ordem de prioridade (mais discriminante primeiro)
_CANONICAL_ORDER = ["cns", "nascimento", "cep", "municipio", "idade", "sexo"]


def get_patient_quasi_identifiers(system_code):
    """Retorna o dict {canonical: campo} de quase-identificadores de um sistema."""
    if system_code in PATIENT_QUASI_IDENTIFIERS:
        return PATIENT_QUASI_IDENTIFIERS[system_code]
    if system_code in ("SIA-PA", "SIA-BI"):
        return PATIENT_QUASI_IDENTIFIERS["SIA-PA"]
    if system_code.startswith("SIA-"):
        return PATIENT_QUASI_IDENTIFIERS["SIA-APAC"]
    if system_code == "SIH-SP":
        # SIH-SP não possui identificadores próprios de paciente; liga ao SIH-RD via AIH
        return {}
    if system_code.startswith("SIH-"):
        return PATIENT_QUASI_IDENTIFIERS["SIH-RD"]
    if system_code.startswith("SINAN-"):
        return {"municipio": "ID_MN_RESI", "sexo": "CS_SEXO", "nascimento": "DT_NASC"}
    return {}


def link_field_names(system_code):
    """Nomes dos campos DBF necessários para a ligação por paciente (para incluir no download)."""
    return list(get_patient_quasi_identifiers(system_code).values())


def supports_patient_linkage(system_code):
    """Indica se o sistema tem quase-identificadores de paciente."""
    return len(get_patient_quasi_identifiers(system_code)) > 0


def available_patient_keys(sys1, sys2):
    """Quase-identificadores em comum entre dois sistemas (ordenados por poder discriminante)."""
    a = set(get_patient_quasi_identifiers(sys1).keys())
    b = set(get_patient_quasi_identifiers(sys2).keys())
    return [k for k in _CANONICAL_ORDER if k in a and k in b]


# ================================================================
# Normalizadores por atributo canônico
# ================================================================
def _norm_muni(v):
    s = re.sub(r"\D", "", str(v))
    return s[:6] if s else ""


def _norm_sexo(v):
    s = str(v).strip().upper()
    if not s:
        return ""
    c = s[0]
    if c == "M":
        return "M"
    if c == "F":
        return "F"
    if c == "1":
        return "M"
    if c in ("2", "3"):
        return "F"
    return ""


def _norm_nasc(v):
    s = re.sub(r"\D", "", str(v))
    return s if len(s) == 8 else ""


def _norm_cep(v):
    s = re.sub(r"\D", "", str(v))
    return s.zfill(8) if s else ""


def _norm_idade(v):
    try:
        n = int(float(str(v).strip()))
        return str(n) if n >= 0 else ""
    except (ValueError, TypeError):
        return ""


def _norm_cns(v):
    s = str(v).strip()
    return s if s and s.upper() not in ("NAN", "NONE", "0", "") else ""


_NORMALIZERS = {
    "municipio":  _norm_muni,
    "sexo":       _norm_sexo,
    "nascimento": _norm_nasc,
    "cep":        _norm_cep,
    "idade":      _norm_idade,
    "cns":        _norm_cns,
}


def harmonize_patient_keys(df, system_code, attributes=None):
    """
    Retorna {canonical: Series normalizada} para os quase-identificadores presentes no df.

    attributes: lista opcional de canônicos a considerar (ex: ["municipio","sexo"]).
    """
    qi = get_patient_quasi_identifiers(system_code)
    out = {}
    for canon, field in qi.items():
        if attributes and canon not in attributes:
            continue
        if field in df.columns:
            out[canon] = df[field].map(_NORMALIZERS[canon])
    return out


def approximate_patient_merge(df1, sys1, df2, sys2, how="inner", keys=None,
                              suffixes=("_b1", "_b2"), max_pairs=5_000_000):
    """
    Pareamento probabilístico de registros do mesmo paciente entre duas bases.

    Args:
        df1, df2: DataFrames das duas bases.
        sys1, sys2: códigos dos sistemas.
        how: tipo de merge ('inner', 'left', 'right', 'outer').
        keys: lista opcional de canônicos a usar (default = todos em comum).
        suffixes: sufixos para colunas homônimas.
        max_pairs: limite de segurança de combinações estimadas. Acima disso,
                   levanta erro (evita explosão combinatória que trava a aplicação).

    Returns:
        (df_merged, keys_usados, colunas_de_chave, stats)

    Raises:
        ValueError se não houver quase-identificadores utilizáveis, ou se o
        pareamento estimado exceder max_pairs.
    """
    common = available_patient_keys(sys1, sys2)
    if keys:
        common = [k for k in common if k in keys]
    if not common:
        raise ValueError("Não há quase-identificadores em comum entre as duas bases selecionadas.")

    h1 = harmonize_patient_keys(df1, sys1, common)
    h2 = harmonize_patient_keys(df2, sys2, common)
    # manter apenas os que existem de fato nos dados baixados
    common = [k for k in common if k in h1 and k in h2]
    if not common:
        raise ValueError(
            "Os campos de ligação por paciente não estão presentes nos dados baixados. "
            "Verifique se as colunas de município/sexo/nascimento foram incluídas."
        )

    left = df1.copy()
    right = df2.copy()
    keycols = []
    for k in common:
        col = f"_pl_{k}"
        left[col] = h1[k].values
        right[col] = h2[k].values
        keycols.append(col)

    # descartar linhas com chave vazia para evitar casamentos falsos em brancos
    for col in keycols:
        left = left[left[col] != ""]
        right = right[right[col] != ""]

    stats = _match_quality(left, right, keycols)

    # Guarda de segurança: impede explosão combinatória que travaria a aplicação
    est = stats.get("est_pairs", 0)
    if est > max_pairs:
        raise ValueError(
            f"O pareamento geraria ~{est:,} combinações".replace(",", ".") +
            f" (limite: {max_pairs:,})".replace(",", ".") +
            ". Os campos escolhidos são pouco discriminantes e casariam muitos "
            "registros entre si (explosão combinatória). Adicione mais "
            "quase-identificadores (ex.: data de nascimento e/ou CEP), reduza o "
            "período/município, ou filtre por CID antes de parear."
        )

    merged = left.merge(right, on=keycols, how=how, suffixes=suffixes)
    return merged, common, keycols, stats


def _match_quality(left, right, keycols):
    """
    Calcula métricas de qualidade do pareamento probabilístico.

    Retorna dict com:
      - left_total / right_total: registros com chave válida em cada base
      - matched: registros da base 1 com ao menos 1 correspondência na base 2
      - unique: registros da base 1 com correspondência ÚNICA (1-para-1)
      - multi: registros da base 1 com múltiplas correspondências (1-para-muitos)
      - unmatched: registros da base 1 sem correspondência
      - match_rate / unique_rate: proporções sobre o total da base 1
    """
    left_total = len(left)
    right_total = len(right)
    result = {
        "left_total": left_total, "right_total": right_total,
        "matched": 0, "unique": 0, "multi": 0, "unmatched": left_total,
        "match_rate": 0.0, "unique_rate": 0.0, "est_pairs": 0,
    }
    if left_total == 0 or right_total == 0:
        return result

    right_counts = right.groupby(keycols, dropna=False).size().rename("_rc").reset_index()
    lk = left[keycols].merge(right_counts, on=keycols, how="left")
    rc = lk["_rc"].fillna(0)

    matched = int((rc >= 1).sum())
    unique = int((rc == 1).sum())
    multi = int((rc > 1).sum())
    result.update({
        "matched": matched,
        "unique": unique,
        "multi": multi,
        "unmatched": left_total - matched,
        "match_rate": matched / left_total,
        "unique_rate": unique / left_total,
        "est_pairs": int(rc.sum()),
    })
    return result
