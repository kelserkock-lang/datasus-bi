import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import re
import requests

# Configuração da página
st.set_page_config(page_title="DataSUS BI Pro", layout="wide", initial_sidebar_state="expanded")

# --- CSS Customizado ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
    h1 { color: #0d47a1; font-weight: 700; letter-spacing: -0.5px; border-bottom: 3px solid #1565c0; padding-bottom: 0.5rem; }
    h2 { color: #1565c0; font-weight: 600; }
    h3 { color: #1976d2; font-weight: 500; }
    .stAlert { border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: #f8f9fa; border-radius: 12px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 12px 20px; background-color: transparent; font-weight: 500; transition: all 0.2s ease; }
    .stTabs [aria-selected="true"] { background-color: #ffffff; border-bottom: none; box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-weight: 600; color: #0d47a1; }
    div[data-testid="metric-container"] { background: linear-gradient(135deg, #ffffff 0%, #f0f4ff 100%); border: 1px solid #d0dff5; padding: 18px 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(13, 71, 161, 0.06); transition: transform 0.2s ease, box-shadow 0.2s ease; }
    div[data-testid="metric-container"]:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(13, 71, 161, 0.12); }
    div[data-testid="stExpander"] { background-color: #ffffff; border: 1px solid #e3e8f0; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d47a1 0%, #1565c0 40%, #1976d2 100%); }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stSelectbox label, section[data-testid="stSidebar"] h2 { color: #ffffff !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%); border: none; border-radius: 10px; font-weight: 600; letter-spacing: 0.3px; padding: 0.6rem 1.2rem; transition: all 0.3s ease; }
    .stButton > button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(13, 71, 161, 0.3); }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    hr { border-color: #e3e8f0; }
    .base-badge { display: inline-block; background: linear-gradient(135deg, #e3f2fd, #bbdefb); color: #0d47a1; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500; margin: 2px 4px; border: 1px solid #90caf9; }
    .mem-ok { color: #2e7d32; font-weight: 600; }
    .mem-warn { color: #e65100; font-weight: 600; }
    .mem-danger { color: #b71c1c; font-weight: 600; }
    .phase-info { background: linear-gradient(135deg, #fff3e0, #ffe0b2); border: 1px solid #ffb74d; border-radius: 10px; padding: 12px 16px; margin: 8px 0; }
    </style>
""", unsafe_allow_html=True)

# --- IMPORTS do módulo de ingestão ---
from data_ingestion import (
    SYSTEMS_CATALOG,
    get_systems_by_category,
    get_systems_by_family,
    SYSTEM_FAMILIES,
    load_full_datasus,
    check_system_resources,
)
from metadata_catalog import (
    get_metadata_for_system, 
    get_metadata_as_dataframe,
    get_join_suggestions,
    get_join_suggestions_as_dataframe,
    generate_join_code,
)
from cid_catalog import (
    CID10_CHAPTERS,
    MORBIDITIES,
    build_cid_filter,
    system_supports_cid,
    search_cid10,
    cid10_label,
)
from patient_linkage import (
    available_patient_keys,
    get_patient_quasi_identifiers,
    link_field_names,
    approximate_patient_merge,
    CANONICAL_LABELS,
)

# --- CABEÇALHO ---
st.title("📊 Painel de BI Avançado — MicroDataSUS")
st.markdown("Plataforma para exploração, cruzamento e download de dados públicos de saúde do Brasil.")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("🎯 Parâmetros de Busca")

categories = get_systems_by_category()

st.sidebar.markdown("##### 📁 Bases de Dados")

# Passo 1 — família principal (SIM, SINASC, SIH, SIA, CNES, SINAN...)
familias = get_systems_by_family()
fam_keys = list(familias.keys())
fam_display = [
    f"{SYSTEM_FAMILIES[f]['icone']} {SYSTEM_FAMILIES[f]['nome']} ({len(familias[f])})"
    if f in SYSTEM_FAMILIES else f"{f} ({len(familias[f])})"
    for f in fam_keys
]

fam_sel_display = st.sidebar.multiselect(
    "1️⃣ Família de dados",
    options=fam_display,
    default=[],
    help="Comece pelo sistema principal. Depois escolha as bases específicas dele.",
)
fam_sel_keys = [fam_keys[fam_display.index(d)] for d in fam_sel_display]

# Passo 2 — bases específicas dentro das famílias escolhidas
sistemas_selecionados = []
if fam_sel_keys:
    base_display, base_codes = [], []
    for fk in fam_sel_keys:
        for code, label in familias[fk]:
            base_display.append(label)
            base_codes.append(code)

    bases_sel_display = st.sidebar.multiselect(
        "2️⃣ Base(s) específica(s)",
        options=base_display,
        default=base_display if len(base_display) == 1 else [],
        help="Selecione uma ou mais bases dentro das famílias escolhidas.",
    )
    for d in bases_sel_display:
        sistemas_selecionados.append(base_codes[base_display.index(d)])
else:
    st.sidebar.caption("👆 Escolha uma família para ver as bases disponíveis.")

st.sidebar.markdown("---")

uf = st.sidebar.selectbox(
    "Estado (UF)", 
    ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", 
     "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
)

st.sidebar.markdown("##### 📅 Período de Coleta")
col_ano1, col_ano2 = st.sidebar.columns(2)
ano_inicio = col_ano1.number_input("Ano Início", min_value=1996, max_value=2025, value=2010, step=1)
ano_fim = col_ano2.number_input("Ano Fim", min_value=1996, max_value=2025, value=2020, step=1)

if ano_fim < ano_inicio:
    st.sidebar.error("⚠️ O Ano Fim deve ser ≥ Ano Início.")
    ano_fim = ano_inicio

mes = st.sidebar.selectbox("Mês", ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])

# --- IBGE ---
@st.cache_data(ttl=86400)
def get_municipios_ibge(sigla_uf):
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{sigla_uf}/municipios"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            mun_data = response.json()
            return [{"id": str(m["id"])[:6], "nome": f"{str(m['id'])[:6]} - {m['nome']}"} for m in mun_data]
    except: pass
    return []

lista_municipios_ativos = get_municipios_ibge(uf)
opcoes_mun = ["Todos (Estado Completo)"] + [m["nome"] for m in lista_municipios_ativos]
municipio_selecionado = st.sidebar.selectbox("Município (Filtro Inteligente)", opcoes_mun,
    help="Deixe em 'Todos' para o estado inteiro. Cidade reduz memória.")

codigo_municipio = ""
if municipio_selecionado != "Todos (Estado Completo)":
    codigo_municipio = municipio_selecionado.split(" - ")[0]

st.sidebar.markdown("---")

# --- Filtro por CID-10 / Morbidade ---
st.sidebar.markdown("##### 🩺 Filtro por CID-10 / Morbidade")
with st.sidebar.expander("Selecionar CIDs e morbidades", expanded=False):
    st.caption("Aplicado às bases com diagnóstico (SIM, SIH, SIA, CIHA, SINAN, SINASC). "
               "Deixe vazio para trazer todos os registros.")

    cap_options = [f'{c["cap"]} — {c["titulo"]}' for c in CID10_CHAPTERS]
    sel_caps_display = st.multiselect(
        "Capítulos CID-10", cap_options, default=[],
        help="Filtra por grandes grupos de doenças (faixas de códigos)."
    )
    sel_caps = [CID10_CHAPTERS[cap_options.index(d)]["cap"] for d in sel_caps_display]

    sel_morb = st.multiselect(
        "Morbidades comuns", sorted(MORBIDITIES.keys()), default=[],
        help="Grupos de CIDs pré-mapeados para doenças frequentes."
    )

    # --- Seleção de CIDs específicos (código + nome da doença) ---
    st.markdown("**CIDs específicos (código + doença)**")
    cid_busca = st.text_input(
        "Buscar CID por código ou nome",
        placeholder="Ex: infarto, diabetes, I21, J45",
        help="Digite parte do nome da doença ou o código. Busca na tabela oficial CID-10 do DATASUS.",
        key="cid_busca_txt",
    )
    _sel_prev = st.session_state.get('cid_especificos_sel', [])
    if cid_busca and cid_busca.strip():
        _resultados = search_cid10(cid_busca, limit=500)
        _opcoes_cid = [cid10_label(c, n) for c, n in _resultados]
        if not _opcoes_cid:
            st.caption("Nenhum CID encontrado para essa busca.")
    else:
        _opcoes_cid = []
        st.caption("🔎 Digite acima (nome da doença ou código) para listar os CIDs.")
    # preserva os CIDs já selecionados mesmo ao trocar/limpar a busca
    _opcoes_cid = list(dict.fromkeys(_opcoes_cid + _sel_prev))
    sel_cids_display = st.multiselect(
        "Selecione os CIDs",
        _opcoes_cid,
        help="Busque acima e marque os CIDs. As seleções são mantidas ao trocar a busca.",
        key="cid_especificos_sel",
    )
    sel_cids_codes = [d.split(" — ", 1)[0].strip() for d in sel_cids_display]

    custom_txt = st.text_input(
        "Códigos CID específicos",
        placeholder="Ex: I21, J45, A90",
        help="Separe por vírgula. Aceita prefixos (ex: I21 pega I210–I219)."
    )
    custom_codes = [c.strip() for c in re.split(r"[,;\s]+", custom_txt) if c.strip()]
    # une os códigos selecionados na lista com os digitados livremente
    custom_codes = sorted(set(custom_codes) | set(sel_cids_codes))

cid_filter_ui = build_cid_filter(sel_caps, sel_morb, custom_codes)
if cid_filter_ui["active"]:
    st.sidebar.caption(
        f"🩺 Filtro CID ativo: {len(cid_filter_ui['ranges'])} capítulo(s) + "
        f"{len(cid_filter_ui['prefixes'])} código(s)/prefixo(s)"
    )

st.sidebar.markdown("---")

# --- Modo econômico de memória (big data) ---
st.sidebar.markdown("##### 🧠 Modo Econômico de Memória")
memory_efficient_ui = st.sidebar.toggle(
    "Filtrar durante a leitura (streaming)",
    value=False,
    help="Recomendado para bases grandes (SIH, SIA, estado inteiro). Aplica os filtros de "
         "município e CID e seleciona as colunas ENQUANTO lê o arquivo, sem carregar a base "
         "inteira na RAM. O cache gerado é específico para os filtros/colunas escolhidos."
)
if memory_efficient_ui:
    st.sidebar.caption("🧠 Streaming ativo — menor uso de RAM.")

st.sidebar.markdown("---")

# --- Recursos do PC ---
st.sidebar.markdown("##### 💻 Recursos do Sistema")
sys_resources = check_system_resources()
if sys_resources["ram_total_gb"] > 0:
    pct = sys_resources["ram_percent_used"]
    avail = sys_resources["ram_available_gb"]
    total = sys_resources["ram_total_gb"]
    if pct < 60:
        st.sidebar.markdown(f'<p class="mem-ok">✅ RAM: {avail}GB livres de {total}GB ({pct}% em uso)</p>', unsafe_allow_html=True)
    elif pct < 80:
        st.sidebar.markdown(f'<p class="mem-warn">⚠️ RAM: {avail}GB livres de {total}GB ({pct}% em uso)</p>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f'<p class="mem-danger">🔴 RAM: {avail}GB livres de {total}GB ({pct}% em uso)</p>', unsafe_allow_html=True)
else:
    st.sidebar.caption("⚠️ Instale `psutil` para monitorar memória")

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div class="phase-info">'
    '🔍 <b>Fase 1:</b> Estrutura instantânea (sem download)<br>'
    '📥 <b>Fase 2:</b> Download completo após seleção'
    '</div>', unsafe_allow_html=True
)
carregar_estrutura = st.sidebar.button("⚡ Ver Estrutura dos Dados", type="primary", width='stretch')


# ================================================================
# FASE 1: CARREGAR METADADOS INSTANTÂNEOS (SEM DOWNLOAD)
# ================================================================

if carregar_estrutura and len(sistemas_selecionados) > 0:
    previews = {}
    periodo_label = f"{ano_inicio}" if ano_inicio == ano_fim else f"{ano_inicio}-{ano_fim}"
    
    for sys_code in sistemas_selecionados:
        sys_label = SYSTEMS_CATALOG[sys_code]["label"]
        meta = get_metadata_for_system(sys_code)
        
        if meta:
            df_meta = get_metadata_as_dataframe(sys_code)
            previews[sys_code] = {
                "label": sys_label,
                "columns": list(meta.keys()),
                "metadata": meta,
                "df_meta": df_meta,
                "n_columns": len(meta),
            }
        else:
            st.warning(f"⚠️ {sys_label}: Metadados não encontrados no catálogo.")
    
    if previews:
        st.session_state['previews'] = previews
        st.session_state['uf_carregada'] = uf
        st.session_state['periodo_carregado'] = periodo_label
        st.session_state['mes_carregado'] = mes
        st.session_state['municipio_carregado'] = codigo_municipio
        st.session_state['cid_filter_carregado'] = cid_filter_ui
        st.session_state['memory_efficient_carregado'] = memory_efficient_ui
        if 'df_join_result' in st.session_state:
            del st.session_state['df_join_result']

elif carregar_estrutura and len(sistemas_selecionados) == 0:
    st.warning("👈 Selecione pelo menos uma base de dados na barra lateral.")


# ================================================================
# EXIBIÇÃO DAS ABAS (metadados carregados)
# ================================================================

if 'previews' in st.session_state and st.session_state['previews']:
    previews = st.session_state['previews']
    
    st.success(f"⚡ **{len(previews)} base(s)** com estrutura carregada **instantaneamente** — sem download do FTP!")
    
    badges_html = " ".join([
        f'<span class="base-badge">📋 {info["label"]} ({info["n_columns"]} variáveis)</span>'
        for code, info in previews.items()
    ])
    st.markdown(badges_html, unsafe_allow_html=True)
    st.markdown("---")
    
    # --- ABAS ---
    aba_estrutura, aba_selecao, aba_join, aba_download = st.tabs([
        "🔍 Estrutura dos Dados",
        "✅ Seleção de Variáveis",
        "🔗 Join entre Bases",
        "📥 Download Completo",
    ])
    
    # ================================================================
    # ABA 1: Estrutura (Metadados — instantâneo)
    # ================================================================
    with aba_estrutura:
        st.subheader("🔍 Estrutura dos Dados — Catálogo de Variáveis")
        st.info("⚡ **Carregamento instantâneo** a partir do catálogo de metadados. "
                "Nenhum download do FTP foi necessário. "
                "Selecione as variáveis na próxima aba e baixe os dados completos na aba **Download**.")
        
        for sys_code, info in previews.items():
            df_meta = info.get("df_meta")
            
            with st.expander(f"📋 {info['label']} — {info['n_columns']} variáveis disponíveis", expanded=True):
                if df_meta is not None and not df_meta.empty:
                    # Tabela com colunas, tipos e descrições
                    st.dataframe(
                        df_meta,
                        width='stretch',
                        hide_index=True,
                        height=min(400, 35 * len(df_meta) + 40),
                        column_config={
                            "Variável": st.column_config.TextColumn("Variável", width="medium"),
                            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                            "Formato": st.column_config.TextColumn("Formato", width="small"),
                            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
                        }
                    )
                else:
                    st.warning("Metadados detalhados não disponíveis para esta base.")
    
    # ================================================================
    # ABA 2: Seleção de Variáveis
    # ================================================================
    with aba_selecao:
        st.subheader("✅ Seleção de Variáveis para o Banco Final")
        st.markdown("Escolha quais colunas incluir. **Somente essas colunas serão baixadas** do FTP na Fase 2.")
        
        for sys_code, info in previews.items():
            all_cols = info["columns"]
            meta = info.get("metadata", {})
            
            st.markdown(f"#### 📋 {info['label']}")
            
            col_select, col_desc = st.columns([1, 2])
            
            with col_select:
                quick_col1, quick_col2, quick_col3 = st.columns(3)
                select_all = quick_col1.button("Todas", key=f"all_{sys_code}")
                select_none = quick_col2.button("Nenhuma", key=f"none_{sys_code}")
                select_important = quick_col3.button("Sugeridas", key=f"imp_{sys_code}")
                
                default_selection = st.session_state.get(f'sel_vars_{sys_code}', all_cols)
                
                if select_none:
                    default_selection = []
                elif select_important:
                    important_patterns = ['COD', 'MUN', 'DT', 'DATA', 'IDADE', 'SEXO', 'RACA', 'ESC', 
                                          'OCUP', 'CID', 'PROC', 'DIAG', 'UF', 'CEP', 'NASC', 'OBITO',
                                          'QTD', 'VAL', 'N_AIH', 'CNES', 'IDENT', 'CAUSABAS', 'PESO',
                                          'ID_AGRAVO', 'CLASSI_FIN', 'EVOLUCAO', 'CRITERIO']
                    default_selection = [c for c in all_cols if any(p in c.upper() for p in important_patterns)]
                    if not default_selection: default_selection = all_cols[:10]
                elif select_all:
                    default_selection = all_cols
                
                selected = st.multiselect(
                    f"Variáveis de {info['label']}",
                    options=all_cols,
                    default=default_selection,
                    key=f"ms_{sys_code}",
                    help=f"Total: {len(all_cols)} colunas disponíveis."
                )
                
                st.session_state[f'sel_vars_{sys_code}'] = selected
                st.caption(f"✅ {len(selected)} de {len(all_cols)} variáveis selecionadas")
            
            with col_desc:
                # Mostrar descrição e tipo das variáveis selecionadas
                if selected:
                    desc_rows = []
                    for var in selected:
                        if var in meta:
                            desc_rows.append({
                                "Variável": var,
                                "Tipo": meta[var]["type"],
                                "Descrição": meta[var]["desc"],
                            })
                        else:
                            desc_rows.append({"Variável": var, "Tipo": "?", "Descrição": "—"})
                    
                    df_desc = pd.DataFrame(desc_rows)
                    st.markdown("**Detalhes das variáveis selecionadas:**")
                    st.dataframe(df_desc, width='stretch', hide_index=True, height=min(350, 35 * len(desc_rows) + 40))
                else:
                    st.info("Nenhuma variável selecionada.")
            
            st.markdown("---")
    
    # ================================================================
    # ABA 3: Join entre Bases
    # ================================================================
    with aba_join:
        st.subheader("🔗 Join (Mesclagem) entre Bases de Dados")
        
        if len(previews) < 2:
            st.info("🔗 Carregue pelo menos **2 bases** para configurar um Join.")
            st.markdown("O Join será executado durante o **Download Completo** (Fase 2).")
        else:
            # --- SUGESTÕES AUTOMÁTICAS DE JOIN ---
            st.markdown("### 💡 Sugestões Inteligentes de Join")
            st.markdown("As bases DataSUS possuem campos em comum que permitem cruzamento de dados. "
                       "Abaixo estão os joins possíveis entre as bases selecionadas.")
            
            base_codes = list(previews.keys())
            join_suggestions = get_join_suggestions(base_codes)
            
            if join_suggestions:
                # Mostrar tabela de sugestões
                df_suggestions = get_join_suggestions_as_dataframe(base_codes)
                st.dataframe(
                    df_suggestions,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Chave de Join": st.column_config.TextColumn("Chave de Join", width="medium"),
                        "Descrição": st.column_config.TextColumn("Descrição", width="large"),
                        "Bases Compatíveis": st.column_config.TextColumn("Bases", width="medium"),
                        "Campos": st.column_config.TextColumn("Campos (mapeamento)", width="large"),
                        "Qualidade": st.column_config.TextColumn("Qualidade", width="small"),
                        "Tabela Referência": st.column_config.TextColumn("Ref", width="small"),
                    }
                )
                
                st.markdown("---")
                
                # Seleção rápida de sugestão
                st.markdown("##### 🎯 Aplicar Sugestão de Join")
                suggestion_names = ["(Manual)"] + [s["descricao"] for s in join_suggestions]
                selected_suggestion = st.selectbox(
                    "Selecione uma sugestão para aplicar ou configure manualmente",
                    options=suggestion_names,
                    key="join_suggestion_select"
                )
                
                # Se selecionou uma sugestão, preencher automaticamente
                if selected_suggestion != "(Manual)":
                    chosen = next((s for s in join_suggestions if s["descricao"] == selected_suggestion), None)
                    if chosen:
                        st.success(f"✅ **{chosen['descricao']}** — Qualidade: {chosen['qualidade'].upper()}")
                        
                        # Mostrar mapeamento
                        mapping_text = " | ".join([f"**{sys}**: `{col}`" for sys, col in chosen["mapeamento"].items()])
                        st.markdown(f"📋 Campos correspondentes: {mapping_text}")
                        
                        if chosen["ref_table"]:
                            st.caption(f"ℹ️ Tabela de referência: {chosen['ref_table']}")
                        
                        # Mostrar código gerado
                        with st.expander("📝 Código Python para reproduzir este join"):
                            code = generate_join_code(base_codes, chosen["chave"])
                            st.code(code, language="python")
                        
                        # Salvar config automática
                        if len(chosen["sistemas_compativeis"]) >= 2:
                            base1 = chosen["sistemas_compativeis"][0]
                            base2 = chosen["sistemas_compativeis"][1]
                            key1 = chosen["mapeamento"][base1]
                            key2 = chosen["mapeamento"][base2]
                            
                            vars1 = st.session_state.get(f'sel_vars_{base1}', previews[base1]["columns"])
                            vars2 = st.session_state.get(f'sel_vars_{base2}', previews[base2]["columns"])
                            
                            st.session_state['join_config'] = {
                                'base1': base1, 'base2': base2,
                                'key1': key1, 'key2': key2,
                                'type': 'left',  # default
                                'vars1': vars1, 'vars2': vars2,
                                'suggestion_used': chosen["chave"],
                            }
                
                st.markdown("---")
            else:
                st.warning("⚠️ Nenhum campo em comum encontrado entre as bases selecionadas para sugerir joins automáticos.")
            
            # --- CONFIGURAÇÃO MANUAL ---
            st.markdown("### ⚙️ Configuração Manual de Join")
            st.markdown("Configure a junção manualmente ou ajuste a sugestão acima.")
            
            base_labels = {code: previews[code]["label"] for code in base_codes}
            
            col_j1, col_j2, col_j3 = st.columns(3)
            
            # Pegar valores default da sugestão se existir
            default_base1 = base_codes[0]
            default_base2 = base_codes[1] if len(base_codes) > 1 else base_codes[0]
            default_key1 = None
            default_key2 = None
            default_type = "left"
            
            if 'join_config' in st.session_state:
                jc = st.session_state['join_config']
                if jc.get('base1') in base_codes:
                    default_base1 = jc['base1']
                if jc.get('base2') in base_codes:
                    default_base2 = jc['base2']
                default_key1 = jc.get('key1')
                default_key2 = jc.get('key2')
                default_type = jc.get('type', 'left')
            
            base1_idx = base_codes.index(default_base1) if default_base1 in base_codes else 0
            base1_code = col_j1.selectbox("Base Principal", base_codes, index=base1_idx, format_func=lambda x: base_labels[x], key="join_base1")
            
            base2_options = [c for c in base_codes if c != base1_code]
            base2_idx = 0
            if default_base2 in base2_options:
                base2_idx = base2_options.index(default_base2)
            base2_code = col_j2.selectbox("Base Secundária", base2_options, index=base2_idx, format_func=lambda x: base_labels[x], key="join_base2") if base2_options else None
            
            join_types = ["inner", "left", "right", "outer"]
            join_type_idx = join_types.index(default_type) if default_type in join_types else 1
            join_type = col_j3.selectbox("Tipo de Join", join_types, index=join_type_idx)
            
            if base2_code:
                cols1 = previews[base1_code]["columns"]
                cols2 = previews[base2_code]["columns"]

                # --- Modo de junção: exata (chave única) x aproximada (mesmo paciente) ---
                pat_keys_disponiveis = available_patient_keys(base1_code, base2_code)
                modo_opcoes = ["🔑 Exata (chave única)"]
                if pat_keys_disponiveis:
                    modo_opcoes.append("👤 Aproximada — mesmo paciente (probabilística)")

                default_mode = st.session_state.get('join_config', {}).get('mode', 'exata')
                modo_idx = 1 if (default_mode == 'aproximada' and len(modo_opcoes) > 1) else 0
                modo_join = st.radio(
                    "Modo de junção",
                    modo_opcoes,
                    index=modo_idx,
                    horizontal=True,
                    help="Exata: usa uma chave única compartilhada. Aproximada: pareia o "
                         "provável mesmo paciente por município + sexo + nascimento/idade + CEP "
                         "(pareamento probabilístico, sem garantia de unicidade).",
                )
                modo_aproximado = modo_join.startswith("👤")

                chave1 = chave2 = None
                patient_keys_sel = []

                if not modo_aproximado:
                    col_k1, col_k2 = st.columns(2)

                    # Determinar índice default para chave1
                    key1_idx = 0
                    if default_key1 and default_key1 in cols1:
                        key1_idx = cols1.index(default_key1)
                    chave1 = col_k1.selectbox(f"Chave — {base_labels[base1_code]}", cols1, index=key1_idx, key="join_key1")

                    # Determinar índice default para chave2
                    key2_idx = 0
                    if default_key2 and default_key2 in cols2:
                        key2_idx = cols2.index(default_key2)
                    elif chave1 in cols2:
                        key2_idx = cols2.index(chave1)
                    chave2 = col_k2.selectbox(f"Chave — {base_labels[base2_code]}", cols2, index=key2_idx, key="join_key2")
                else:
                    st.warning(
                        "⚠️ **Pareamento probabilístico (aproximado).** Não há identificador único "
                        "de paciente compartilhado entre SIA e SIH nos dados públicos. Este modo "
                        "casa o **provável mesmo paciente** pela combinação dos campos abaixo. "
                        "O resultado **não é uma identificação garantida** e pode gerar "
                        "correspondências múltiplas (um-para-muitos). Use e reporte como "
                        "*record linkage probabilístico por quase-identificadores*."
                    )
                    default_patk = st.session_state.get('join_config', {}).get('patient_keys', pat_keys_disponiveis)
                    default_patk = [k for k in default_patk if k in pat_keys_disponiveis] or pat_keys_disponiveis
                    patient_keys_sel = st.multiselect(
                        "Quase-identificadores para o pareamento",
                        options=pat_keys_disponiveis,
                        default=default_patk,
                        format_func=lambda k: CANONICAL_LABELS.get(k, k),
                        help="Quanto mais campos, mais restrito (e confiável) o pareamento. "
                             "Município + sexo sozinhos são muito abrangentes.",
                    )
                    mapa1 = get_patient_quasi_identifiers(base1_code)
                    mapa2 = get_patient_quasi_identifiers(base2_code)
                    mapping_txt = " | ".join([
                        f"**{CANONICAL_LABELS.get(k, k)}**: `{mapa1.get(k)}` ↔ `{mapa2.get(k)}`"
                        for k in patient_keys_sel
                    ])
                    if mapping_txt:
                        st.caption(f"🔗 Campos pareados: {mapping_txt}")
                    else:
                        st.error("Selecione ao menos um quase-identificador.")

                st.markdown("---")
                st.markdown("##### Variáveis no resultado do Join")
                
                vars1 = st.session_state.get(f'sel_vars_{base1_code}', cols1)
                vars2 = st.session_state.get(f'sel_vars_{base2_code}', cols2)
                
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    join_vars1 = st.multiselect(
                        f"Colunas de {base_labels[base1_code]}",
                        options=cols1, default=vars1, key="join_vars1"
                    )
                with col_v2:
                    join_vars2 = st.multiselect(
                        f"Colunas de {base_labels[base2_code]}",
                        options=cols2, default=vars2, key="join_vars2"
                    )
                
                st.session_state['join_config'] = {
                    'base1': base1_code, 'base2': base2_code,
                    'key1': chave1, 'key2': chave2,
                    'type': join_type,
                    'vars1': join_vars1, 'vars2': join_vars2,
                    'mode': 'aproximada' if modo_aproximado else 'exata',
                    'patient_keys': patient_keys_sel,
                }
                
                st.success("✅ Configuração de Join salva. Vá para a aba **Download Completo** para executar.")
    
    # ================================================================
    # ABA 4: Download Completo (FASE 2 — aqui sim baixa do FTP)
    # ================================================================
    with aba_download:
        st.subheader("📥 Download Completo — Fase 2")
        st.markdown(
            '<div class="phase-info">'
            '📡 <b>Aqui os dados serão baixados do FTP do DataSUS</b>. '
            'Somente as variáveis selecionadas serão mantidas em memória. '
            'O cache Parquet será salvo para reutilização futura.'
            '</div>', unsafe_allow_html=True
        )
        
        st.markdown("---")
        
        # --- Aviso de filtro CID ativo ---
        cid_filter_dl = st.session_state.get('cid_filter_carregado')
        if cid_filter_dl and cid_filter_dl.get("active"):
            st.info(
                f"🩺 **Filtro por CID/morbidade ativo** — "
                f"{len(cid_filter_dl['ranges'])} capítulo(s) + {len(cid_filter_dl['prefixes'])} código(s)/prefixo(s). "
                "Só serão mantidos os registros de diagnóstico correspondentes "
                "(bases sem CID, como CNES/PNI, não são filtradas)."
            )
        
        # --- Download Bases Individuais ---
        st.markdown("#### 📋 Bases Individuais")
        
        for sys_code, info in previews.items():
            selected_vars = st.session_state.get(f'sel_vars_{sys_code}', info["columns"])
            
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                n_vars = len(selected_vars)
                st.markdown(f"**{info['label']}** — {n_vars} variáveis selecionadas de {info['n_columns']} disponíveis")
            
            with col_btn:
                if st.button(f"📥 Baixar {sys_code}", key=f"dl_full_{sys_code}"):
                    prog = st.progress(0, text=f"Conectando ao FTP DataSUS para {info['label']}...")
                    
                    def dl_progress(pct, msg):
                        prog.progress(min(pct, 1.0), text=msg)
                    
                    try:
                        df_full = load_full_datasus(
                            system_code=sys_code,
                            uf=st.session_state.get('uf_carregada', 'AC'),
                            year_start=ano_inicio,
                            year_end=ano_fim,
                            month=st.session_state.get('mes_carregado', 'Todos'),
                            city_code=st.session_state.get('municipio_carregado', ''),
                            columns_to_keep=selected_vars,
                            cid_filter=st.session_state.get('cid_filter_carregado'),
                            memory_efficient=st.session_state.get('memory_efficient_carregado', False),
                            progress_callback=dl_progress,
                        )
                        
                        prog.empty()
                        
                        if df_full is not None and not df_full.empty:
                            st.success(f"✅ {info['label']}: **{len(df_full):,}** linhas carregadas com **{len(df_full.columns)}** colunas.".replace(",", "."))
                            st.dataframe(df_full.head(20), width='stretch', hide_index=True)
                            
                            csv_data = df_full.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"💾 Salvar CSV ({len(df_full):,} linhas)".replace(",", "."),
                                data=csv_data,
                                file_name=f"DataSUS_{sys_code}_{st.session_state.get('uf_carregada', '')}_{st.session_state.get('periodo_carregado', '')}.csv",
                                mime='text/csv',
                                key=f"csv_dl_{sys_code}"
                            )
                        else:
                            st.error(f"❌ A base retornou vazia.")
                    except Exception as e:
                        prog.empty()
                        st.error(f"❌ Erro: {e}")
        
        st.markdown("---")
        
        # --- Download com Join ---
        st.markdown("#### 🔗 Download com Join")
        
        if 'join_config' in st.session_state:
            jc = st.session_state['join_config']
            _modo_aprox = jc.get('mode') == 'aproximada'
            if _modo_aprox:
                _pk_txt = ", ".join(CANONICAL_LABELS.get(k, k) for k in jc.get('patient_keys', []))
                st.markdown(
                    f"**Join configurado (👤 aproximado — mesmo paciente):** "
                    f"`{previews[jc['base1']]['label']}` **{jc['type'].upper()}** "
                    f"`{previews[jc['base2']]['label']}`"
                )
                st.caption(f"🔗 Pareamento probabilístico por: {_pk_txt or '—'}")
            else:
                st.markdown(
                    f"**Join configurado:** `{previews[jc['base1']]['label']}` "
                    f"**{jc['type'].upper()}** "
                    f"`{previews[jc['base2']]['label']}` "
                    f"(chave: `{jc['key1']}` ↔ `{jc['key2']}`)"
                )
            
            if st.button("⚡ Executar Join e Baixar", type="primary"):
                status_join = st.empty()
                prog_join = st.progress(0, text="Iniciando download para Join...")
                
                try:
                    # Baixar base 1 (inclui a chave exata ou os campos de linkage por paciente)
                    if _modo_aprox:
                        extra1 = link_field_names(jc['base1'])
                        extra2 = link_field_names(jc['base2'])
                    else:
                        extra1 = [jc['key1']]
                        extra2 = [jc['key2']]
                    vars1_with_key = list(set(jc['vars1'] + extra1))
                    status_join.info(f"⏳ Baixando {previews[jc['base1']]['label']} do FTP...")
                    
                    def prog1(pct, msg):
                        prog_join.progress(min(pct * 0.4, 0.4), text=f"[Base 1] {msg}")
                    
                    df1_full = load_full_datasus(
                        system_code=jc['base1'],
                        uf=st.session_state.get('uf_carregada', 'AC'),
                        year_start=ano_inicio, year_end=ano_fim,
                        month=st.session_state.get('mes_carregado', 'Todos'),
                        city_code=st.session_state.get('municipio_carregado', ''),
                        columns_to_keep=vars1_with_key,
                        cid_filter=st.session_state.get('cid_filter_carregado'),
                        memory_efficient=st.session_state.get('memory_efficient_carregado', False),
                        progress_callback=prog1,
                    )
                    
                    # Baixar base 2
                    vars2_with_key = list(set(jc['vars2'] + extra2))
                    status_join.info(f"⏳ Baixando {previews[jc['base2']]['label']} do FTP...")
                    
                    def prog2(pct, msg):
                        prog_join.progress(min(0.4 + pct * 0.4, 0.8), text=f"[Base 2] {msg}")
                    
                    df2_full = load_full_datasus(
                        system_code=jc['base2'],
                        uf=st.session_state.get('uf_carregada', 'AC'),
                        year_start=ano_inicio, year_end=ano_fim,
                        month=st.session_state.get('mes_carregado', 'Todos'),
                        city_code=st.session_state.get('municipio_carregado', ''),
                        columns_to_keep=vars2_with_key,
                        cid_filter=st.session_state.get('cid_filter_carregado'),
                        memory_efficient=st.session_state.get('memory_efficient_carregado', False),
                        progress_callback=prog2,
                    )
                    
                    if df1_full is not None and df2_full is not None and not df1_full.empty and not df2_full.empty:
                        prog_join.progress(0.85, text="Executando Join...")
                        status_join.info("⏳ Executando Join entre as bases...")
                        
                        if _modo_aprox:
                            df_joined, keys_usados, _keycols, _stats = approximate_patient_merge(
                                df1_full, jc['base1'], df2_full, jc['base2'],
                                how=jc['type'], keys=jc.get('patient_keys'),
                                suffixes=(f'_{jc["base1"]}', f'_{jc["base2"]}'),
                            )
                            _kt = ", ".join(CANONICAL_LABELS.get(k, k) for k in keys_usados)
                        else:
                            df1_full[jc['key1']] = df1_full[jc['key1']].astype(str).str.strip()
                            df2_full[jc['key2']] = df2_full[jc['key2']].astype(str).str.strip()
                            
                            df_joined = pd.merge(
                                df1_full, df2_full,
                                left_on=jc['key1'], right_on=jc['key2'],
                                how=jc['type'],
                                suffixes=(f'_{jc["base1"]}', f'_{jc["base2"]}')
                            )
                        
                        prog_join.progress(1.0, text="Join concluído!")
                        status_join.empty()
                        prog_join.empty()
                        
                        if _modo_aprox:
                            st.success(
                                f"✅ Pareamento aproximado concluído! **{len(df_joined):,}** registros "
                                f"({jc['type']} join).".replace(",", ".")
                            )
                            st.warning(
                                f"⚠️ Pareamento **probabilístico** por {_kt}. Correspondências podem ser "
                                "um-para-muitos — não interprete como identificação individual garantida."
                            )
                            # --- Qualidade do pareamento ---
                            st.markdown("##### 🎯 Qualidade do pareamento")
                            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
                            mcol1.metric(
                                "Base 1 pareada",
                                f"{_stats['match_rate']*100:.1f}%",
                                help=f"{_stats['matched']:,} de {_stats['left_total']:,} registros da base 1 "
                                     "tiveram ao menos 1 correspondência.".replace(",", "."),
                            )
                            mcol2.metric(
                                "Match único (1-para-1)",
                                f"{_stats['unique_rate']*100:.1f}%",
                                help=f"{_stats['unique']:,} registros com correspondência única — "
                                     "os mais confiáveis.".replace(",", "."),
                            )
                            mcol3.metric(
                                "Múltiplo (1-para-N)",
                                f"{_stats['multi']:,}".replace(",", "."),
                                help="Registros da base 1 com mais de uma correspondência (ambíguos).",
                            )
                            mcol4.metric(
                                "Sem match",
                                f"{_stats['unmatched']:,}".replace(",", "."),
                                help="Registros da base 1 sem nenhuma correspondência na base 2.",
                            )
                            _uniq = _stats['unique_rate'] * 100
                            if _uniq >= 70:
                                st.success(f"🟢 Boa especificidade: {_uniq:.1f}% de matches únicos.")
                            elif _uniq >= 40:
                                st.info(f"🟡 Especificidade moderada: {_uniq:.1f}% de matches únicos. "
                                        "Considere incluir mais quase-identificadores (ex.: nascimento/CEP).")
                            else:
                                st.warning(f"🔴 Baixa especificidade: apenas {_uniq:.1f}% de matches únicos. "
                                           "O pareamento está muito abrangente — adicione mais campos "
                                           "(CEP, data de nascimento) para reduzir ambiguidade.")
                        else:
                            st.success(f"✅ Join concluído! **{len(df_joined):,}** registros ({jc['type']} join).".replace(",", "."))
                        st.dataframe(df_joined.head(50), width='stretch', hide_index=True)
                        
                        join_final_vars = st.multiselect(
                            "Filtrar colunas do resultado (todas por padrão)",
                            options=df_joined.columns.tolist(),
                            default=df_joined.columns.tolist(),
                            key="join_final_vars"
                        )
                        
                        if join_final_vars:
                            df_export = df_joined[join_final_vars]
                            csv_join = df_export.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"💾 Salvar Join CSV ({len(df_export):,} linhas)".replace(",", "."),
                                data=csv_join,
                                file_name=f"DataSUS_Join_{jc['base1']}_{jc['base2']}_{st.session_state.get('uf_carregada', '')}_{st.session_state.get('periodo_carregado', '')}.csv",
                                mime='text/csv',
                                key="dl_join_csv"
                            )
                    else:
                        prog_join.empty()
                        status_join.empty()
                        st.error("❌ Uma ou ambas as bases retornaram vazias.")
                
                except Exception as e:
                    prog_join.empty()
                    status_join.empty()
                    st.error(f"❌ Erro no Join: {e}")
        else:
            st.info("Nenhum Join configurado. Vá para a aba 'Join entre Bases' para configurar.")

else:
    # --- LANDING PAGE ---
    st.info("👈 Selecione as bases, localidade e período na barra lateral e clique em **Ver Estrutura dos Dados**.")
    
    st.markdown("### 🏗️ Fluxo de Trabalho em 2 Fases")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("""
        #### ⚡ Fase 1 — Estrutura Instantânea
        - **Sem download do FTP** — carregamento instantâneo
        - Mostra todas as variáveis com **nome, tipo e descrição**
        - Permite selecionar variáveis e configurar Joins
        - Zero peso na memória
        """)
    with col_f2:
        st.markdown("""
        #### 📥 Fase 2 — Download Completo
        - Carrega a base inteira **somente com as colunas selecionadas**
        - Executa Joins com dados reais
        - Salva cache Parquet para reutilização futura
        - Exporta CSV para download
        """)
    
    st.markdown("---")
    
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown("#### 📡 Ingestão Direta\nExtrai **DBCs oficiais** do FTP do DataSUS, converte para DBF em Python puro.")
    with col_feat2:
        st.markdown("#### ⚡ Cache Inteligente\nDados são salvos em **Parquet** para carregamento instantâneo futuro.")
    with col_feat3:
        st.markdown("#### 💾 Gestão de Memória\nMonitoramento de RAM e carregamento seletivo de colunas.")
    
    st.markdown("---")
    st.markdown("### 📚 Bases de Dados Disponíveis")
    
    cols = st.columns(3)
    for idx, (cat_name, systems) in enumerate(categories.items()):
        with cols[idx % 3]:
            st.markdown(f"**{cat_name}**")
            for code, label in systems:
                st.markdown(f"- {label}")
