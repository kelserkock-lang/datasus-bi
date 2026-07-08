import os
from ftplib import FTP
import pandas as pd
from dbctodbf.dbc_decompress import DBCDecompress
from dbfread import DBF
import time

# ============================================================
# Catálogo completo de sistemas DataSUS disponíveis via FTP
# ============================================================

SYSTEMS_CATALOG = {
    # --- Sistemas Epidemiológicos ---
    "SIM-DO": {
        "label": "SIM-DO (Mortalidade)",
        "ftp_path": "/dissemin/publicos/SIM/CID10/DORES/",
        "file_pattern": "DO{uf}{year}.dbc",  # year = 4 dígitos ou 2
        "type": "annual",
        "category": "Epidemiológico",
    },
    "SINASC": {
        "label": "SINASC (Nascidos Vivos)",
        "ftp_path": "/dissemin/publicos/SINASC/NOVOS/DNRES/",
        "file_pattern": "DN{uf}{year}.dbc",
        "type": "annual",
        "category": "Epidemiológico",
    },
    # --- Sistemas Hospitalares/Ambulatoriais ---
    "SIH-RD": {
        "label": "SIH-RD (Internações)",
        "ftp_path": "/dissemin/publicos/SIHSUS/200801_/Dados/",
        "file_pattern": "RD{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-PA": {
        "label": "SIA-PA (Produção Ambulatorial)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "PA{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    # --- SIH (outros grupos além da AIH Reduzida) ---
    "SIH-SP": {
        "label": "SIH-SP (Serviços Profissionais)",
        "ftp_path": "/dissemin/publicos/SIHSUS/200801_/Dados/",
        "file_pattern": "SP{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIH-RJ": {
        "label": "SIH-RJ (AIH Rejeitadas)",
        "ftp_path": "/dissemin/publicos/SIHSUS/200801_/Dados/",
        "file_pattern": "RJ{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIH-ER": {
        "label": "SIH-ER (AIH Rejeitadas c/ Erro)",
        "ftp_path": "/dissemin/publicos/SIHSUS/200801_/Dados/",
        "file_pattern": "ER{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    # --- SIA (grupos APAC / RAAS / BPA-I além da Produção Ambulatorial) ---
    "SIA-AM": {
        "label": "SIA-AM (APAC Medicamentos)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "AM{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-AQ": {
        "label": "SIA-AQ (APAC Quimioterapia)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "AQ{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-AR": {
        "label": "SIA-AR (APAC Radioterapia)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "AR{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-AN": {
        "label": "SIA-AN (APAC Nefrologia)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "AN{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-ATD": {
        "label": "SIA-ATD (APAC Tratamento Dialítico)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "ATD{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-AD": {
        "label": "SIA-AD (APAC Laudos Diversos)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "AD{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-AB": {
        "label": "SIA-AB (APAC Cirurgia Bariátrica)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "AB{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-ABO": {
        "label": "SIA-ABO (APAC Acomp. Pós-Bariátrica)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "ABO{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-ACF": {
        "label": "SIA-ACF (APAC Confecção de Fístula)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "ACF{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-AMP": {
        "label": "SIA-AMP (APAC Acomp. Amputado)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "AMP{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-PS": {
        "label": "SIA-PS (RAAS Psicossocial)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "PS{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-SAD": {
        "label": "SIA-SAD (RAAS Atenção Domiciliar)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "SAD{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "SIA-BI": {
        "label": "SIA-BI (Boletim Prod. Individualizado)",
        "ftp_path": "/dissemin/publicos/SIASUS/200801_/Dados/",
        "file_pattern": "BI{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    "CIHA": {
        "label": "CIHA (Com. Inf. Hosp. Ambulatorial)",
        "ftp_path": "/dissemin/publicos/CIHA/201101_/Dados/",
        "file_pattern": "CIHA{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Hospitalar/Ambulatorial",
    },
    # --- CNES (subdivisions) ---
    "CNES-LT": {
        "label": "CNES-LT (Leitos)",
        "ftp_path": "/dissemin/publicos/CNES/200508_/Dados/LT/",
        "file_pattern": "LT{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Estabelecimentos (CNES)",
    },
    "CNES-ST": {
        "label": "CNES-ST (Estabelecimentos)",
        "ftp_path": "/dissemin/publicos/CNES/200508_/Dados/ST/",
        "file_pattern": "ST{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Estabelecimentos (CNES)",
    },
    "CNES-PF": {
        "label": "CNES-PF (Profissionais)",
        "ftp_path": "/dissemin/publicos/CNES/200508_/Dados/PF/",
        "file_pattern": "PF{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Estabelecimentos (CNES)",
    },
    "CNES-EP": {
        "label": "CNES-EP (Equipamentos)",
        "ftp_path": "/dissemin/publicos/CNES/200508_/Dados/EP/",
        "file_pattern": "EP{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Estabelecimentos (CNES)",
    },
    "CNES-EE": {
        "label": "CNES-EE (Equipes)",
        "ftp_path": "/dissemin/publicos/CNES/200508_/Dados/EE/",
        "file_pattern": "EE{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Estabelecimentos (CNES)",
    },
    "CNES-HB": {
        "label": "CNES-HB (Habilitações)",
        "ftp_path": "/dissemin/publicos/CNES/200508_/Dados/HB/",
        "file_pattern": "HB{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Estabelecimentos (CNES)",
    },
    "CNES-SR": {
        "label": "CNES-SR (Serviços Especializados)",
        "ftp_path": "/dissemin/publicos/CNES/200508_/Dados/SR/",
        "file_pattern": "SR{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Estabelecimentos (CNES)",
    },
    # --- SINAN (Agravos de Notificação) - Dados Finais ---
    "SINAN-DENG": {
        "label": "SINAN - Dengue",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "DENG{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-CHIK": {
        "label": "SINAN - Chikungunya",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "CHIK{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-ZIKA": {
        "label": "SINAN - Zika",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "ZIKA{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-LEIV": {
        "label": "SINAN - Leishmaniose Visceral",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "LEIV{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-LEIT": {
        "label": "SINAN - Leishmaniose Tegumentar",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "LEIT{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-HANS": {
        "label": "SINAN - Hanseníase",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "HANS{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-TUBE": {
        "label": "SINAN - Tuberculose",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "TUBE{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-MALA": {
        "label": "SINAN - Malária",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "MALA{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-CHAG": {
        "label": "SINAN - Chagas",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "CHAG{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-RAIV": {
        "label": "SINAN - Raiva",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "RAIV{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-TETA": {
        "label": "SINAN - Tétano Acidental",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "TETA{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-TETN": {
        "label": "SINAN - Tétano Neonatal",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "TETN{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-MENI": {
        "label": "SINAN - Meningite",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "MENI{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-COQU": {
        "label": "SINAN - Coqueluche",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "COQU{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-DIFT": {
        "label": "SINAN - Difteria",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "DIFT{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-ESQU": {
        "label": "SINAN - Esquistossomose",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "ESQU{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-FEAM": {
        "label": "SINAN - Febre Amarela",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "FEAM{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-HANT": {
        "label": "SINAN - Hantavirose",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "HANT{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-HEPA": {
        "label": "SINAN - Hepatites Virais",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "HEPA{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-LEPC": {
        "label": "SINAN - Leptospirose",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "LEPT{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-PEST": {
        "label": "SINAN - Peste",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "PEST{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-PFAN": {
        "label": "SINAN - Paralisia Flácida Aguda",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "PFAN{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-ROTA": {
        "label": "SINAN - Rotavírus",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "ROTA{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-SIFA": {
        "label": "SINAN - Sífilis Adquirida",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "SIFA{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-SIFC": {
        "label": "SINAN - Sífilis Congênita",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "SIFC{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-SIFG": {
        "label": "SINAN - Sífilis em Gestante",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "SIFG{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-AIDS": {
        "label": "SINAN - AIDS",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "AIDS{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-BOTI": {
        "label": "SINAN - Botulismo",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "BOTI{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-CRIO": {
        "label": "SINAN - Criptococose",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "CRIO{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-ACBI": {
        "label": "SINAN - Acidente de Trabalho Biológico",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "ACBI{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-ACGR": {
        "label": "SINAN - Acidente de Trabalho Grave",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "ACGR{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-ANIM": {
        "label": "SINAN - Acidente por Animais Peçonhentos",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "ANIM{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-VIOL": {
        "label": "SINAN - Violência Doméstica/Sexual",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "VIOL{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    "SINAN-IEXO": {
        "label": "SINAN - Intoxicação Exógena",
        "ftp_path": "/dissemin/publicos/SINAN/DADOS/FINAIS/",
        "file_pattern": "IEXO{uf}{year}.dbc",
        "type": "annual",
        "category": "SINAN (Agravos)",
    },
    # --- PNI (Imunizações) ---
    "PNI": {
        "label": "PNI (Imunizações)",
        "ftp_path": "/dissemin/publicos/PNI/DADOS/",
        "file_pattern": "PNI{uf}{yy}{mm}.dbc",
        "type": "monthly",
        "category": "Imunizações",
    },
}


def get_systems_by_category():
    """Retorna os sistemas agrupados por categoria para exibição no dashboard."""
    categories = {}
    for code, info in SYSTEMS_CATALOG.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((code, info["label"]))
    return categories


# Famílias principais dos sistemas do DataSUS (visão prática para o usuário).
SYSTEM_FAMILIES = {
    "SIM":    {"nome": "SIM — Mortalidade",                  "icone": "⚰️"},
    "SINASC": {"nome": "SINASC — Nascidos Vivos",            "icone": "👶"},
    "SIH":    {"nome": "SIH — Internações Hospitalares",     "icone": "🏥"},
    "SIA":    {"nome": "SIA — Produção Ambulatorial",        "icone": "🩺"},
    "CNES":   {"nome": "CNES — Estabelecimentos de Saúde",   "icone": "🏢"},
    "SINAN":  {"nome": "SINAN — Agravos de Notificação",     "icone": "🦟"},
    "CIHA":   {"nome": "CIHA — Comunicação Internação/Alta", "icone": "📋"},
    "PNI":    {"nome": "PNI — Imunizações",                  "icone": "💉"},
}


def get_system_family(code):
    """Retorna a chave da família principal de um sistema a partir do seu código."""
    for fam in ("SINASC", "SIM", "SIH", "SIA", "CNES", "SINAN", "CIHA", "PNI"):
        if code.startswith(fam):
            return fam
    return "Outros"


def get_systems_by_family():
    """Agrupa os sistemas por família principal (SIM, SINASC, SIH, SIA, ...).

    Retorna um dict ordenado conforme SYSTEM_FAMILIES:
    {familia: [(code, label), ...]}.
    """
    fams = {}
    for code, info in SYSTEMS_CATALOG.items():
        fams.setdefault(get_system_family(code), []).append((code, info["label"]))
    ordered = {f: fams[f] for f in SYSTEM_FAMILIES if f in fams}
    for f in fams:
        if f not in ordered:
            ordered[f] = fams[f]
    return ordered


def get_all_system_labels():
    """Retorna lista de labels para selectbox do Streamlit."""
    return [(code, info["label"]) for code, info in SYSTEMS_CATALOG.items()]


# ============================================================
# FTP Helpers
# ============================================================

def _connect_ftp(max_retries=3, timeout=60):
    """Conecta ao FTP do DataSUS com retry e timeout melhorado."""
    for attempt in range(1, max_retries + 1):
        try:
            ftp = FTP('ftp.datasus.gov.br', timeout=timeout)
            ftp.login()
            return ftp
        except Exception as e:
            print(f"Tentativa {attempt}/{max_retries} de conexão FTP falhou: {e}")
            if attempt == max_retries:
                raise ConnectionError(
                    f"Não foi possível conectar ao FTP do DataSUS após {max_retries} tentativas. "
                    f"Verifique sua internet ou tente novamente mais tarde. Último erro: {e}"
                )
            time.sleep(2 * attempt)


def fetch_and_convert_dbc_preview(ftp, filename, dbf_name, n_rows=10, progress_callback=None):
    """
    FASE 1: Baixa DBC → converte para DBF → lê APENAS N linhas para preview.
    MANTÉM o DBF no disco para leitura completa posterior (Fase 2).
    Se o DBF já existe em disco (cache), pula download+conversão.
    Retorna: (df_preview, columns_list, dbf_path)
    """
    try:
        # OTIMIZAÇÃO: Se o DBF já existe em disco, pular download+conversão (parte lenta)
        if os.path.exists(dbf_name):
            if progress_callback: progress_callback(0.8, f"DBF em cache! Lendo {n_rows} linhas de {os.path.basename(dbf_name)}...")
            else: print(f"DBF já existe em disco: {dbf_name} — pulando download.")
            
            table = DBF(dbf_name, encoding='latin1', load=False)
            columns = table.field_names
            preview_rows = []
            for i, record in enumerate(table):
                if i >= n_rows: break
                preview_rows.append(record)
            
            df_preview = pd.DataFrame(preview_rows)
            if progress_callback: progress_callback(1.0, "Preview pronto (do cache)!")
            return df_preview, columns, dbf_name
        
        # Sem cache: precisa baixar DBC e converter (parte inevitavelmente lenta)
        if progress_callback: progress_callback(0.1, f"Baixando {filename} do FTP...")
        else: print(f"Baixando {filename} do FTP...")
        
        with open(filename, 'wb') as f:
            ftp.retrbinary(f"RETR {filename}", f.write)
        
        if progress_callback: progress_callback(0.5, f"Convertendo {filename} → DBF (pode demorar em bases grandes)...")
        else: print(f"Convertendo {filename} → DBF...")
        
        dbc2dbf = DBCDecompress()
        dbc2dbf.decompressFile(filename, dbf_name)
        
        # Remover o DBC (não precisamos mais), mas MANTER o DBF no disco
        if os.path.exists(filename): os.remove(filename)
        
        if progress_callback: progress_callback(0.8, f"Lendo cabeçalho + {n_rows} linhas...")
        else: print(f"Lendo preview de {dbf_name} ({n_rows} linhas)...")
        
        # Ler SEM load=True (modo iterador, econômico em memória)
        table = DBF(dbf_name, encoding='latin1', load=False)
        columns = table.field_names
        
        # Ler apenas N linhas
        preview_rows = []
        for i, record in enumerate(table):
            if i >= n_rows: break
            preview_rows.append(record)
        
        df_preview = pd.DataFrame(preview_rows)
        
        if progress_callback: progress_callback(1.0, "Preview pronto!")
        return df_preview, columns, dbf_name
    
    except Exception as e:
        if progress_callback: progress_callback(1.0, f"Erro: {e}")
        print(f"Aviso: Erro ao processar preview de {filename}: {e}")
        if os.path.exists(filename):
            try: os.remove(filename)
            except: pass
        return pd.DataFrame(), [], ""


def fetch_and_convert_dbc_full(dbf_name, columns_to_keep=None, progress_callback=None):
    """
    FASE 2: Lê o DBF COMPLETO do disco (já baixado na Fase 1).
    Filtra apenas as colunas selecionadas pelo usuário.
    Remove o DBF após leitura.
    """
    if not os.path.exists(dbf_name):
        raise FileNotFoundError(f"Arquivo DBF '{dbf_name}' não encontrado no disco. Refaça o preview.")
    
    if progress_callback: progress_callback(0.1, f"Carregando base completa de {dbf_name}...")
    else: print(f"Carregando base completa de {dbf_name}...")
    
    try:
        table = DBF(dbf_name, encoding='latin1', load=True)
        df = pd.DataFrame(iter(table))
        
        if progress_callback: progress_callback(0.7, "Filtrando colunas selecionadas...")
        
        # Filtrar apenas colunas escolhidas pelo usuário
        if columns_to_keep:
            valid_cols = [c for c in columns_to_keep if c in df.columns]
            if valid_cols:
                df = df[valid_cols]
        
        if progress_callback: progress_callback(0.9, "Limpando arquivo temporário...")
        
        # Agora sim remover o DBF
        if os.path.exists(dbf_name):
            try: os.remove(dbf_name)
            except: pass
        
        if progress_callback: progress_callback(1.0, "Base completa carregada!")
        return df
    
    except Exception as e:
        print(f"Erro ao ler DBF completo: {e}")
        return pd.DataFrame()


def fetch_and_convert_dbc(ftp, filename, dbf_name, progress_callback=None):
    """
    Legacy: Baixa DBC → DBF → DataFrame COMPLETO. Usado internamente quando
    se precisa do dataset inteiro de uma vez (ex: leitura direto do cache).
    """
    if progress_callback: progress_callback(0.1, f"Baixando {filename} do FTP...")
    else: print(f"Baixando {filename} do FTP...")
    
    try:
        with open(filename, 'wb') as f:
            ftp.retrbinary(f"RETR {filename}", f.write)
            
        if progress_callback: progress_callback(0.5, f"Convertendo {filename} para DBF...")
        else: print(f"Convertendo {filename} para DBF...")
        
        dbc2dbf = DBCDecompress()
        dbc2dbf.decompressFile(filename, dbf_name)
        
        if progress_callback: progress_callback(0.8, f"Montando Datatable em Memória...")
        else: print(f"Lendo DBF ({dbf_name})...")
        
        table = DBF(dbf_name, encoding='latin1', load=True)
        df = pd.DataFrame(iter(table))
        
        if progress_callback: progress_callback(1.0, f"Concluído!")
        if os.path.exists(filename): os.remove(filename)
        if os.path.exists(dbf_name): os.remove(dbf_name)
            
        return df
    except Exception as e:
        if progress_callback: progress_callback(1.0, f"Erro: {e}")
        print(f"Aviso: Erro ao processar {filename}: {e}")
        for f_path in [filename, dbf_name]:
            if os.path.exists(f_path):
                try: os.remove(f_path)
                except: pass
        return pd.DataFrame()


# ============================================================
# Otimização de memória e leitura em streaming (big data)
# ============================================================

# Campos de município usados para filtro geográfico em streaming
MUNI_FILTER_FIELDS = [
    'CODMUNRES', 'MUNRES', 'CODMUNOCOR', 'CODUFMUN', 'CODMUNGE',
    'ID_MUNICIP', 'ID_MUNIRES', 'CO_MUNIRES', 'MUNIC_RES',
    'PA_MUNPCN', 'CO_MUN_RES',
]


def _optimize_dtypes(df):
    """
    Reduz o consumo de memória de um DataFrame:
      - object de baixa cardinalidade → category
      - inteiros/floats → menor subtipo possível (downcast)
    Pode reduzir 30–70% da RAM em bases DataSUS.
    """
    if df is None or df.empty:
        return df
    n = len(df)
    for col in df.columns:
        s = df[col]
        if s.dtype == 'object':
            try:
                nun = s.nunique(dropna=False)
                if n > 0 and nun / n < 0.5:
                    df[col] = s.astype('category')
            except Exception:
                pass
        elif pd.api.types.is_integer_dtype(s):
            try: df[col] = pd.to_numeric(s, downcast='integer')
            except Exception: pass
        elif pd.api.types.is_float_dtype(s):
            try: df[col] = pd.to_numeric(s, downcast='float')
            except Exception: pass
    return df


def fetch_and_convert_dbc_stream(ftp, filename, dbf_name, columns_to_keep=None,
                                 city_code="", cid_matcher=None, batch_size=50_000,
                                 progress_callback=None):
    """
    Leitura em STREAMING (econômica em memória):
      Baixa DBC → converte para DBF → itera registro a registro aplicando
      filtro de município e de CID *antes* de montar o DataFrame, e projeta
      apenas as colunas selecionadas. Nunca mantém a base inteira em RAM.

    Retorna: DataFrame já filtrado e projetado (somente linhas/colunas desejadas).
    """
    try:
        if not os.path.exists(dbf_name):
            if progress_callback: progress_callback(0.1, f"Baixando {filename} do FTP...")
            else: print(f"Baixando {filename} do FTP...")
            with open(filename, 'wb') as f:
                ftp.retrbinary(f"RETR {filename}", f.write)

            if progress_callback: progress_callback(0.5, f"Convertendo {filename} → DBF...")
            dbc2dbf = DBCDecompress()
            dbc2dbf.decompressFile(filename, dbf_name)
            if os.path.exists(filename): os.remove(filename)

        if progress_callback: progress_callback(0.7, "Lendo e filtrando registros (modo econômico)...")

        table = DBF(dbf_name, encoding='latin1', load=False)
        all_cols = table.field_names
        keep = [c for c in columns_to_keep if c in all_cols] if columns_to_keep else list(all_cols)

        city = city_code.strip() if city_code else ""
        muni_field = next((c for c in MUNI_FILTER_FIELDS if c in all_cols), None) if city else None

        frames = []
        batch = []
        for rec in table:
            # Filtro geográfico (município) — aplicado direto no registro
            if muni_field and city:
                val = rec.get(muni_field)
                if val is None or not str(val).startswith(city):
                    continue
            # Filtro por CID/morbidade — aplicado no registro completo
            if cid_matcher is not None and not cid_matcher(rec):
                continue
            # Projeção de colunas
            if columns_to_keep:
                batch.append({c: rec.get(c) for c in keep})
            else:
                batch.append(dict(rec))

            if len(batch) >= batch_size:
                frames.append(pd.DataFrame(batch))
                batch = []

        if batch:
            frames.append(pd.DataFrame(batch))

        # Limpeza dos temporários
        for f_path in [filename, dbf_name]:
            if os.path.exists(f_path):
                try: os.remove(f_path)
                except Exception: pass

        if frames:
            df = pd.concat(frames, ignore_index=True)
        else:
            df = pd.DataFrame(columns=keep)

        if progress_callback: progress_callback(1.0, "Registros filtrados carregados!")
        return df

    except Exception as e:
        if progress_callback: progress_callback(1.0, f"Erro: {e}")
        print(f"Aviso: Erro no streaming de {filename}: {e}")
        for f_path in [filename, dbf_name]:
            if os.path.exists(f_path):
                try: os.remove(f_path)
                except Exception: pass
        return pd.DataFrame()


# ============================================================
# Gerenciamento de Memória
# ============================================================

def check_system_resources():
    """Avalia a capacidade do PC para ler/salvar databases."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "ram_available_gb": round(mem.available / (1024**3), 1),
            "ram_percent_used": mem.percent,
            "can_load_large": mem.available > 2 * (1024**3),
            "recommended_chunk_size": _calc_chunk_size(mem.available),
        }
    except ImportError:
        return {
            "ram_total_gb": -1, "ram_available_gb": -1,
            "ram_percent_used": -1, "can_load_large": True,
            "recommended_chunk_size": 100_000,
        }


def _calc_chunk_size(available_bytes):
    available_gb = available_bytes / (1024**3)
    if available_gb > 8: return 500_000
    elif available_gb > 4: return 200_000
    elif available_gb > 2: return 100_000
    else: return 50_000


def estimate_parquet_memory(parquet_path):
    if not os.path.exists(parquet_path): return 0
    file_size_mb = os.path.getsize(parquet_path) / (1024**2)
    return round(file_size_mb * 4, 1)


# ============================================================
# FASE 1: Download de PREVIEW (apenas N linhas, leve)
# ============================================================

def download_preview_datasus(system_code, uf, year_start, year_end, month="Todos", city_code="", n_rows=10, progress_callback=None):
    """
    FASE 1: Baixa os DBC do FTP, converte para DBF, lê APENAS N linhas.
    Mantém os DBFs no disco para a Fase 2 (carga completa).
    Retorna: (df_preview, columns, dbf_files_list)
    """
    if system_code not in SYSTEMS_CATALOG:
        raise ValueError(f"Sistema '{system_code}' não encontrado no catálogo.")
    
    sys_info = SYSTEMS_CATALOG[system_code]
    ftp_path = sys_info["ftp_path"]
    file_pattern = sys_info["file_pattern"]
    sys_type = sys_info["type"]
    
    # Primeiro verificar cache parquet — se existe, lê preview instantâneo
    cache_dir = "data"
    os.makedirs(cache_dir, exist_ok=True)
    city_str = city_code if city_code.strip() else "Todos"
    cache_file = os.path.join(cache_dir, f"{system_code}_{uf}_{year_start}-{year_end}_{month}_{city_str}.parquet")
    
    if os.path.exists(cache_file):
        if progress_callback: progress_callback(1.0, "Cache encontrado! Preview instantâneo.")
        try:
            df = pd.read_parquet(cache_file)
            return df.head(n_rows), df.columns.tolist(), len(df), [], cache_file
        except:
            pass
    
    if progress_callback: progress_callback(0.02, f"Conectando ao FTP DataSUS...")
    
    ftp = _connect_ftp()
    previews = []
    all_columns = []
    dbf_files = []
    
    anos_range = range(year_start, year_end + 1)
    total_steps = len(anos_range)
    
    for idx_ano, current_year in enumerate(anos_range):
        year_str = str(current_year)
        year2 = year_str[-2:]
        prog_base = (idx_ano / total_steps) * 0.9
        
        try:
            ftp.cwd(ftp_path)
            files = ftp.nlst()
            
            if sys_type == "annual":
                target = file_pattern.replace("{uf}", uf).replace("{year}", year_str)
                if target not in files:
                    target = file_pattern.replace("{uf}", uf).replace("{year}", year2)
                if target not in files:
                    continue
                
                if progress_callback:
                    progress_callback(prog_base + 0.05, f"Baixando preview {system_code} {uf} {year_str}...")
                
                dbf_name = os.path.join(cache_dir, target.replace(".dbc", ".dbf"))
                df_prev, cols, dbf_path = fetch_and_convert_dbc_preview(ftp, target, dbf_name, n_rows, progress_callback)
                if not df_prev.empty:
                    previews.append(df_prev)
                    all_columns = cols
                    dbf_files.append(dbf_path)
            
            elif sys_type == "monthly":
                meses_download = [month] if month != "Todos" else [f"{m:02d}" for m in range(1, 13)]
                
                for idx_mes, mes in enumerate(meses_download):
                    target = file_pattern.replace("{uf}", uf).replace("{yy}", year2).replace("{mm}", mes)
                    
                    if target in files:
                        if progress_callback:
                            prog_mes = prog_base + (idx_mes / len(meses_download)) * (0.9 / total_steps)
                            progress_callback(prog_mes, f"Baixando preview {system_code} {uf} {year_str}/{mes}...")
                        
                        dbf_name = os.path.join(cache_dir, target.replace(".dbc", ".dbf"))
                        df_prev, cols, dbf_path = fetch_and_convert_dbc_preview(ftp, target, dbf_name, n_rows, progress_callback)
                        if not df_prev.empty:
                            previews.append(df_prev)
                            all_columns = cols
                            dbf_files.append(dbf_path)
                            # Para preview, só precisamos de 1 arquivo com dados
                            break
        
        except FileNotFoundError as e:
            try: ftp.quit()
            except: pass
            raise e
        except Exception as e:
            try: ftp.pwd()
            except:
                try: ftp = _connect_ftp()
                except:
                    try: ftp.quit()
                    except: pass
                    raise Exception(f"Erro FTP: {e}")
        
        # Para preview, 1 ano com dados já basta
        if previews:
            break
    
    try: ftp.quit()
    except: pass
    
    if previews:
        df_preview = pd.concat(previews, ignore_index=True).head(n_rows)
        # Normalizar tipos
        for col in df_preview.select_dtypes(include=['category', 'object']).columns:
            df_preview[col] = df_preview[col].astype(str)
        
        if progress_callback: progress_callback(1.0, "Preview pronto!")
        return df_preview, all_columns, -1, dbf_files, cache_file  # -1 = total desconhecido
    else:
        return pd.DataFrame(), [], 0, [], cache_file


# ============================================================
# FASE 2: Carga COMPLETA (após usuário selecionar variáveis)
# ============================================================

def load_full_datasus(system_code, uf, year_start, year_end, month="Todos", city_code="",
                      columns_to_keep=None, cid_filter=None, memory_efficient=False,
                      progress_callback=None):
    """
    FASE 2: Carrega o dataset COMPLETO, filtrando apenas as colunas selecionadas.
    
    1. Se cache Parquet existe → lê do cache (filtra colunas)
    2. Senão → baixa do FTP, processa, salva cache, retorna filtrado
    
    cid_filter: estrutura de filtro por CID-10 (ver cid_catalog.build_cid_filter).
                Aplicado às linhas ANTES da seleção de colunas. O cache Parquet é
                sempre salvo COMPLETO (o filtro CID não entra na chave do cache).

    memory_efficient: se True, usa leitura em STREAMING — filtra município/CID e
                projeta colunas DURANTE a leitura do DBF, sem carregar a base inteira
                em RAM. Ideal para bases grandes. Neste modo o cache é específico para
                a combinação de colunas + filtro (chave com hash).
    
    Retorna: DataFrame completo com apenas as colunas selecionadas
    """
    resolved_code = _resolve_system_code(system_code)
    
    if year_end is None:
        year_end = year_start
    
    cache_dir = "data"
    os.makedirs(cache_dir, exist_ok=True)
    
    city_str = city_code if city_code.strip() else "Todos"

    # ---------- MODO ECONÔMICO (streaming) ----------
    if memory_efficient:
        import hashlib
        sig_src = "|".join([
            ",".join(sorted(columns_to_keep)) if columns_to_keep else "ALL",
            ",".join(cid_filter.get("prefixes", [])) if cid_filter else "",
            repr(cid_filter.get("ranges", [])) if cid_filter else "",
        ])
        sig = hashlib.md5(sig_src.encode()).hexdigest()[:8]
        cache_file = os.path.join(
            cache_dir, f"{resolved_code}_{uf}_{year_start}-{year_end}_{month}_{city_str}_econ_{sig}.parquet"
        )

        if os.path.exists(cache_file):
            if progress_callback: progress_callback(1.0, "Cache econômico encontrado!")
            print(f"Cache econômico encontrado: {cache_file}")
            return pd.read_parquet(cache_file)

        if progress_callback: progress_callback(0.05, "Modo econômico: baixando e filtrando em streaming...")
        df = download_and_process_datasus(
            resolved_code, uf, year_start, year_end, month, city_code, progress_callback,
            columns_to_keep=columns_to_keep, cid_filter=cid_filter, memory_efficient=True,
        )
        df = _optimize_dtypes(df)

        if df is not None and not df.empty:
            try:
                df.to_parquet(cache_file, index=False)
                print(f"Cache econômico salvo: {len(df)} linhas.")
            except Exception as e:
                print(f"Aviso: Não foi possível salvar cache econômico: {e}")

        _cleanup_temp_dbfs(cache_dir)
        if progress_callback: progress_callback(1.0, "Base carregada (modo econômico)!")
        return df

    # ---------- MODO PADRÃO (cache completo) ----------
    cache_file = os.path.join(cache_dir, f"{resolved_code}_{uf}_{year_start}-{year_end}_{month}_{city_str}.parquet")
    
    # Opção 1: Cache Parquet já existe
    if os.path.exists(cache_file):
        if progress_callback: progress_callback(0.5, "Lendo do cache Parquet...")
        print(f"Cache Parquet encontrado: {cache_file}")
        df = pd.read_parquet(cache_file)
        
        df = _apply_cid_filter(df, resolved_code, cid_filter, progress_callback)
        
        if columns_to_keep:
            valid_cols = [c for c in columns_to_keep if c in df.columns]
            if valid_cols:
                df = df[valid_cols]
        
        if progress_callback: progress_callback(1.0, "Dados carregados do cache!")
        return df
    
    # Opção 2: Download completo do FTP
    if progress_callback: progress_callback(0.05, "Cache não encontrado. Baixando base completa do FTP...")
    print(f"Cache inexistente. Extraindo do FTP DATASUS...")
    
    df = download_and_process_datasus(resolved_code, uf, year_start, year_end, month, city_code, progress_callback)
    
    if df is not None and not df.empty:
        # Otimizar tipos para reduzir memória e tamanho do cache
        df = _optimize_dtypes(df)
        # Salvar cache COMPLETO (todas as colunas) para futura reutilização
        try:
            df.to_parquet(cache_file, index=False)
            print(f"Cache Parquet salvo: {len(df)} linhas.")
        except Exception as e:
            print(f"Aviso: Não foi possível salvar cache: {e}")
        
        # Aplicar filtro por CID-10 (linhas) antes da seleção de colunas
        df = _apply_cid_filter(df, resolved_code, cid_filter, progress_callback)
        
        # Retornar apenas colunas selecionadas
        if columns_to_keep:
            valid_cols = [c for c in columns_to_keep if c in df.columns]
            if valid_cols:
                df = df[valid_cols]
    
    # Limpar DBFs temporários da Fase 1
    _cleanup_temp_dbfs(cache_dir)
    
    if progress_callback: progress_callback(1.0, "Base completa carregada!")
    return df


def _apply_cid_filter(df, system_code, cid_filter, progress_callback=None):
    """Aplica o filtro por CID-10 usando o cid_catalog, se disponível e ativo."""
    if not cid_filter or not cid_filter.get("active"):
        return df
    try:
        from cid_catalog import filter_dataframe_by_cid, get_cid_fields
    except Exception as e:
        print(f"Aviso: filtro CID indisponível ({e}).")
        return df

    if not get_cid_fields(system_code):
        # Sistema sem campo de diagnóstico (ex: CNES/PNI) — não filtra
        return df

    if progress_callback: progress_callback(0.95, "Aplicando filtro por CID/morbidade...")
    n_antes = len(df)
    df = filter_dataframe_by_cid(df, system_code, cid_filter)
    print(f"Filtro CID: {n_antes} → {len(df)} linhas.")
    return df


def _cleanup_temp_dbfs(cache_dir):
    """Remove arquivos DBF temporários deixados pela Fase 1."""
    try:
        for f in os.listdir(cache_dir):
            if f.endswith('.dbf'):
                fpath = os.path.join(cache_dir, f)
                try: os.remove(fpath)
                except: pass
    except: pass


# ============================================================
# Download genérico completo (usado internamente pela Fase 2)
# ============================================================

def download_and_process_datasus(system_code, uf, year_start, year_end, month="Todos", city_code="",
                                 progress_callback=None, columns_to_keep=None, cid_filter=None,
                                 memory_efficient=False):
    """Baixa dados direto do FTP do DATASUS. Retorna DataFrame completo.

    memory_efficient: se True, filtra município/CID e projeta colunas durante a
    leitura de cada DBF (streaming), evitando carregar a base inteira em RAM.
    """
    if system_code not in SYSTEMS_CATALOG:
        raise ValueError(f"Sistema '{system_code}' não encontrado no catálogo.")
    
    sys_info = SYSTEMS_CATALOG[system_code]
    ftp_path = sys_info["ftp_path"]
    file_pattern = sys_info["file_pattern"]
    sys_type = sys_info["type"]
    
    # Preparar matcher de CID para streaming (se aplicável)
    cid_matcher = None
    if memory_efficient and cid_filter and cid_filter.get("active"):
        try:
            from cid_catalog import make_cid_record_matcher
            _, cid_matcher = make_cid_record_matcher(system_code, cid_filter)
        except Exception as e:
            print(f"Aviso: matcher CID indisponível ({e}).")
    
    if progress_callback: progress_callback(0.02, f"Conectando ao FTP para {sys_info['label']}...")
    
    ftp = _connect_ftp()
    dfs = []
    
    anos_range = range(year_start, year_end + 1)
    total_steps = len(anos_range)
    
    for idx_ano, current_year in enumerate(anos_range):
        year_str = str(current_year)
        year2 = year_str[-2:]
        prog_base = (idx_ano / total_steps) * 0.9
        
        try:
            ftp.cwd(ftp_path)
            files = ftp.nlst()
            
            if sys_type == "annual":
                target = file_pattern.replace("{uf}", uf).replace("{year}", year_str)
                if target not in files:
                    target = file_pattern.replace("{uf}", uf).replace("{year}", year2)
                if target not in files:
                    continue
                
                if progress_callback:
                    progress_callback(prog_base + 0.05, f"Baixando {system_code} {uf} {year_str} (completo)...")
                
                dbf_name = target.replace(".dbc", ".dbf")
                if memory_efficient:
                    dfs.append(fetch_and_convert_dbc_stream(
                        ftp, target, dbf_name, columns_to_keep=columns_to_keep,
                        city_code=city_code, cid_matcher=cid_matcher, progress_callback=progress_callback))
                else:
                    dfs.append(fetch_and_convert_dbc(ftp, target, dbf_name, progress_callback))
            
            elif sys_type == "monthly":
                meses_download = [month] if month != "Todos" else [f"{m:02d}" for m in range(1, 13)]
                
                for idx_mes, mes in enumerate(meses_download):
                    target = file_pattern.replace("{uf}", uf).replace("{yy}", year2).replace("{mm}", mes)
                    
                    if target in files:
                        if progress_callback:
                            prog_mes = prog_base + (idx_mes / len(meses_download)) * (0.9 / total_steps)
                            progress_callback(prog_mes, f"Baixando {system_code} {uf} {year_str}/{mes} (completo)...")
                        
                        dbf_name = target.replace(".dbc", ".dbf")
                        if memory_efficient:
                            dfs.append(fetch_and_convert_dbc_stream(
                                ftp, target, dbf_name, columns_to_keep=columns_to_keep,
                                city_code=city_code, cid_matcher=cid_matcher, progress_callback=progress_callback))
                        else:
                            dfs.append(fetch_and_convert_dbc(ftp, target, dbf_name, progress_callback))
                    
        except FileNotFoundError as e:
            try: ftp.quit()
            except: pass
            raise e
        except Exception as e:
            try: ftp.pwd()
            except:
                try: ftp = _connect_ftp()
                except:
                    try: ftp.quit()
                    except: pass
                    raise Exception(f"Erro FTP: {e}")

    try: ftp.quit()
    except: pass
    
    if progress_callback: progress_callback(0.92, "Consolidando dados...")
    
    if len(dfs) > 0:
        dfs = [d for d in dfs if not d.empty]
        if len(dfs) == 0: return pd.DataFrame()
        
        df_final = pd.concat(dfs, ignore_index=True)
        
        if month != "Todos" and sys_type == "annual":
            dt_cols = [c for c in df_final.columns if c in ['DTOBITO', 'DTNASC', 'DT_NOTIFIC', 'DT_SIN_PRI']]
            if dt_cols:
                df_final = df_final[df_final[dt_cols[0]].astype(str).str[2:4] == month]
        
        # No modo econômico o filtro de município já foi aplicado em streaming
        if not memory_efficient and city_code.strip() != "":
            mun_cols = [c for c in df_final.columns if c in [
                'CODMUNRES', 'MUNRES', 'CODMUNOCOR', 'CODUFMUN', 'CODMUNGE',
                'ID_MUNICIP', 'ID_MUNIRES', 'CO_MUNIRES', 'MUNIC_RES'
            ]]
            if mun_cols:
                df_final = df_final[df_final[mun_cols[0]].astype(str).str.startswith(city_code.strip())]
        
        categorias = df_final.select_dtypes(include=['category', 'object']).columns
        if len(categorias) > 0:
            df_final[categorias] = df_final[categorias].astype(str)
        
        if progress_callback: progress_callback(0.98, "Dados prontos!")
        return df_final
    else:
        return pd.DataFrame()


# ============================================================
# Compatibilidade e Helpers
# ============================================================

def get_datasus_head(system_code, uf, year_start, year_end=None, month="Todos", city_code="", n_rows=10):
    """Atalho para verificar cache existente antes de download."""
    if year_end is None: year_end = year_start
    cache_dir = "data"
    os.makedirs(cache_dir, exist_ok=True)
    city_str = city_code if city_code.strip() else "Todos"
    cache_file = os.path.join(cache_dir, f"{system_code}_{uf}_{year_start}-{year_end}_{month}_{city_str}.parquet")
    
    if os.path.exists(cache_file):
        try:
            df = pd.read_parquet(cache_file)
            return df.head(n_rows), df.columns.tolist(), len(df), cache_file
        except: pass
    return None, [], 0, cache_file


def get_datasus_data(system_code, uf, year_start, year_end=None, month="Todos", city_code="", progress_callback=None, max_rows=None):
    """Compatibilidade: carrega dataset completo (sem seleção de colunas)."""
    return load_full_datasus(
        system_code=system_code, uf=uf,
        year_start=year_start, year_end=year_end,
        month=month, city_code=city_code,
        columns_to_keep=None, progress_callback=progress_callback
    )


def _resolve_system_code(input_code):
    """Resolve código/label de sistema para código canônico."""
    if input_code in SYSTEMS_CATALOG: return input_code
    for code, info in SYSTEMS_CATALOG.items():
        if info["label"] == input_code: return code
    for code, info in SYSTEMS_CATALOG.items():
        if input_code.startswith(code) or code.startswith(input_code): return code
    return input_code
