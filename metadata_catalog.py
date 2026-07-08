"""
Catálogo de Metadados dos Sistemas DataSUS.
Contém nomes de colunas, tipos e descrições para cada sistema.
Permite preview INSTANTÂNEO sem download do FTP.

Fontes: Dicionários de dados oficiais do DATASUS
- SIM: ftp.datasus.gov.br/dissemin/publicos/SIM/ 
- SINASC: ftp.datasus.gov.br/dissemin/publicos/SINASC/
- SIH: ftp.datasus.gov.br/dissemin/publicos/SIHSUS/
- SIA: ftp.datasus.gov.br/dissemin/publicos/SIASUS/
- SINAN: datasus.saude.gov.br - Dicionário de dados SINAN
- CNES: ftp.datasus.gov.br/dissemin/publicos/CNES/
"""

# Formato: {"coluna": {"type": "C(8)|N(4)|D", "desc": "Descrição em PT-BR"}}
# Tipos: C = Character, N = Numeric, D = Date

METADATA_CATALOG = {

    # ================================================================
    # SIM - Sistema de Informações sobre Mortalidade (Declaração de Óbito)
    # ================================================================
    "SIM-DO": {
        "CONTADOR":   {"type": "N(8)",  "desc": "Contador sequencial do registro"},
        "TIPOBITO":   {"type": "N(1)",  "desc": "Tipo de óbito: 1=Fetal, 2=Não fetal"},
        "DTOBITO":    {"type": "C(8)",  "desc": "Data do óbito (ddmmaaaa)"},
        "HORAOBITO":  {"type": "C(4)",  "desc": "Hora do óbito (hhmm)"},
        "NATURAL":    {"type": "C(3)",  "desc": "Naturalidade do falecido"},
        "CODMUNRES":  {"type": "C(6)",  "desc": "Código IBGE do município de residência"},
        "DTNASC":     {"type": "C(8)",  "desc": "Data de nascimento (ddmmaaaa)"},
        "IDADE":      {"type": "N(3)",  "desc": "Idade no momento do óbito (codificada)"},
        "SEXO":       {"type": "N(1)",  "desc": "Sexo: 1=Masc, 2=Fem, 9=Ignorado"},
        "RACACOR":    {"type": "N(1)",  "desc": "Raça/Cor: 1=Branca, 2=Preta, 3=Amarela, 4=Parda, 5=Indígena"},
        "ESTCIV":     {"type": "N(1)",  "desc": "Estado civil: 1=Solteiro, 2=Casado, 3=Viúvo, 4=Sep/Div, 5=União estável, 9=Ignorado"},
        "ESC":        {"type": "N(1)",  "desc": "Escolaridade (em anos de estudo)"},
        "ESC2010":    {"type": "N(1)",  "desc": "Escolaridade (classificação 2010)"},
        "OCUP":       {"type": "C(6)",  "desc": "Ocupação (CBO)"},
        "CODMUNOCOR": {"type": "C(6)",  "desc": "Código IBGE do município de ocorrência"},
        "LOCOCOR":    {"type": "N(1)",  "desc": "Local de ocorrência: 1=Hospital, 2=Outro estab saúde, 3=Domicílio, 4=Via pública, 5=Outros, 9=Ignorado"},
        "CODESTAB":   {"type": "C(7)",  "desc": "Código CNES do estabelecimento de ocorrência"},
        "CODMUNNASC": {"type": "C(6)",  "desc": "Código IBGE do município de nascimento"},
        "IDADEMAE":   {"type": "N(2)",  "desc": "Idade da mãe (óbitos fetais/menores 1 ano)"},
        "ESCMAE":     {"type": "N(1)",  "desc": "Escolaridade da mãe"},
        "ESCMAE2010": {"type": "N(1)",  "desc": "Escolaridade da mãe (classificação 2010)"},
        "OCUPMAE":    {"type": "C(6)",  "desc": "Ocupação da mãe (CBO)"},
        "QTDFILVIVO": {"type": "N(2)",  "desc": "Quantidade de filhos vivos"},
        "QTDFILMORT": {"type": "N(2)",  "desc": "Quantidade de filhos mortos"},
        "GRAESSION":  {"type": "N(2)",  "desc": "Semanas de gestação"},
        "GESTACAO":   {"type": "N(1)",  "desc": "Semanas de gestação (categorizado)"},
        "PARTO":      {"type": "N(1)",  "desc": "Tipo de parto: 1=Vaginal, 2=Cesáreo, 9=Ignorado"},
        "OBITOPARTO": {"type": "N(1)",  "desc": "Óbito em relação ao parto: 1=Antes, 2=Durante, 3=Após, 9=Ignorado"},
        "PESO":       {"type": "N(4)",  "desc": "Peso ao nascer (em gramas)"},
        "NUMERODN":   {"type": "C(11)", "desc": "Número da Declaração de Nascido Vivo"},
        "OBITOGRAV":  {"type": "N(1)",  "desc": "Óbito durante gravidez: 1=Sim, 2=Não, 9=Ignorado"},
        "OBITOPUERP": {"type": "N(1)",  "desc": "Óbito no puerpério: 1=Sim (até 42d), 2=Sim (43d-1a), 3=Não, 9=Ignorado"},
        "ASSISTMED":  {"type": "N(1)",  "desc": "Assistência médica: 1=Sim, 2=Não, 9=Ignorado"},
        "EXAME":      {"type": "N(1)",  "desc": "Exame complementar: 1=Sim, 2=Não, 9=Ignorado"},
        "CIRURGIA":   {"type": "N(1)",  "desc": "Cirurgia: 1=Sim, 2=Não, 9=Ignorado"},
        "NECROPSIA":  {"type": "N(1)",  "desc": "Necropsia: 1=Sim, 2=Não, 9=Ignorado"},
        "LINHAA":     {"type": "C(20)", "desc": "Causa na Linha A da DO (CID-10)"},
        "LINHAB":     {"type": "C(20)", "desc": "Causa na Linha B da DO (CID-10)"},
        "LINHAC":     {"type": "C(20)", "desc": "Causa na Linha C da DO (CID-10)"},
        "LINHAD":     {"type": "C(20)", "desc": "Causa na Linha D da DO (CID-10)"},
        "LINHAII":    {"type": "C(20)", "desc": "Causa na Linha II da DO (CID-10)"},
        "CAUSABAS":   {"type": "C(4)",  "desc": "Causa básica do óbito (CID-10)"},
        "CAUSABAS_O": {"type": "C(4)",  "desc": "Causa básica original antes da re-seleção"},
        "CB_PRE":     {"type": "C(4)",  "desc": "Causa básica pré investigação"},
        "NUMERODO":   {"type": "C(11)", "desc": "Número da Declaração de Óbito"},
        "TPPOS":      {"type": "N(1)",  "desc": "Tipo de posição (investigação)"},
        "DTINVESTIG":  {"type": "C(8)", "desc": "Data da investigação (ddmmaaaa)"},
        "ATESSION":   {"type": "N(1)",  "desc": "Atestante: 1=Médico assistente, 2=Substituto, 3=IML, 4=SVO, 5=Outros"},
        "FONTEINV":   {"type": "N(1)",  "desc": "Fonte de investigação"},
        "DTCADASTRO":  {"type": "C(8)", "desc": "Data de cadastro no sistema (ddmmaaaa)"},
        "DTRECEBIM":  {"type": "C(8)",  "desc": "Data de recebimento (ddmmaaaa)"},
        "CODINST":    {"type": "C(4)",  "desc": "Código da instância regional"},
        "NUDIASOBam": {"type": "N(8)",  "desc": "Número de dias entre óbito e AM"},
    },

    # ================================================================
    # SINASC - Sistema de Informações sobre Nascidos Vivos
    # ================================================================
    "SINASC": {
        "CONTADOR":   {"type": "N(8)",  "desc": "Contador sequencial do registro"},
        "CODMUNNASC": {"type": "C(6)",  "desc": "Código IBGE do município de nascimento"},
        "CODMUNRES":  {"type": "C(6)",  "desc": "Código IBGE do município de residência da mãe"},
        "LOCNASC":    {"type": "N(1)",  "desc": "Local de nascimento: 1=Hospital, 2=Outro estab saúde, 3=Domicílio, 4=Outros, 9=Ignorado"},
        "IDADEMAE":   {"type": "N(2)",  "desc": "Idade da mãe em anos"},
        "ESTCIVMAE":  {"type": "N(1)",  "desc": "Estado civil da mãe: 1=Solteira, 2=Casada, 3=Viúva, 4=Sep/Div, 5=União estável, 9=Ignorado"},
        "ESCMAE":     {"type": "N(1)",  "desc": "Escolaridade da mãe (em anos de estudo)"},
        "ESCMAE2010": {"type": "N(1)",  "desc": "Escolaridade da mãe (classificação 2010)"},
        "CODOCUPMAE": {"type": "C(6)",  "desc": "Ocupação da mãe (CBO)"},
        "QTDFILVIVO": {"type": "N(2)",  "desc": "Quantidade de filhos vivos anteriores"},
        "QTDFILMORT": {"type": "N(2)",  "desc": "Quantidade de filhos mortos anteriores"},
        "GESTACAO":   {"type": "N(1)",  "desc": "Semanas de gestação: 1=<22, 2=22-27, 3=28-31, 4=32-36, 5=37-41, 6≥42, 9=Ignorado"},
        "GRAESSION":  {"type": "N(2)",  "desc": "Semanas de gestação (número exato)"},
        "PARTO":      {"type": "N(1)",  "desc": "Tipo de parto: 1=Vaginal, 2=Cesáreo, 9=Ignorado"},
        "CONSULTAS":  {"type": "N(1)",  "desc": "Nº de consultas pré-natal: 1=Nenhuma, 2=1-3, 3=4-6, 4=7+, 9=Ignorado"},
        "DTNASC":     {"type": "C(8)",  "desc": "Data de nascimento (ddmmaaaa)"},
        "HORANASC":   {"type": "C(4)",  "desc": "Hora do nascimento (hhmm)"},
        "SEXO":       {"type": "N(1)",  "desc": "Sexo: 1=Masculino, 2=Feminino, 0=Ignorado"},
        "APGAR1":     {"type": "N(2)",  "desc": "Apgar no 1º minuto (0-10)"},
        "APGAR5":     {"type": "N(2)",  "desc": "Apgar no 5º minuto (0-10)"},
        "RACACOR":    {"type": "N(1)",  "desc": "Raça/Cor do RN: 1=Branca, 2=Preta, 3=Amarela, 4=Parda, 5=Indígena"},
        "RACACORMAE": {"type": "N(1)",  "desc": "Raça/Cor da mãe"},
        "PESO":       {"type": "N(4)",  "desc": "Peso ao nascer em gramas"},
        "IDANOMAL":   {"type": "N(1)",  "desc": "Anomalia congênita: 1=Sim, 2=Não, 9=Ignorado"},
        "CODANOMAL":  {"type": "C(20)", "desc": "Código da anomalia congênita (CID-10)"},
        "DTCADASTRO": {"type": "C(8)",  "desc": "Data de cadastro no sistema"},
        "NUMEROLOTE": {"type": "N(8)",  "desc": "Número do lote"},
        "KOESSION":   {"type": "N(1)",  "desc": "Informação sobre Konsultas (consultas)"},
        "CODESTAB":   {"type": "C(7)",  "desc": "Código CNES do estabelecimento de nascimento"},
        "NUMERODNV":  {"type": "C(11)", "desc": "Número da Declaração de Nascido Vivo"},
        "STDONOVADN": {"type": "N(1)",  "desc": "Status da nova DN"},
        "STDNNOVA":   {"type": "N(1)",  "desc": "Status DN nova"},
        "CODPAISRES": {"type": "C(3)",  "desc": "Código do país de residência"},
        "TPAPESSION": {"type": "N(1)",  "desc": "Tipo de apresentação do parto"},
        "STTRABPART": {"type": "N(1)",  "desc": "Status trabalho de parto (induzido/espontâneo)"},
        "STCESPARTO": {"type": "N(1)",  "desc": "Status cesárea antes do parto"},
        "TPNASCASSI": {"type": "N(1)",  "desc": "Tipo de assistência no nascimento: 1=Médico, 2=Enfermeira, 3=Parteira, 4=Outros, 9=Ignorado"},
        "TPFUNCRESP": {"type": "N(1)",  "desc": "Tipo de função do responsável pelo preenchimento"},
        "TPDOCRESP":  {"type": "N(1)",  "desc": "Tipo de documento do responsável"},
        "DTDECLARAC": {"type": "C(8)",  "desc": "Data da declaração"},
        "DTRECEBIM":  {"type": "C(8)",  "desc": "Data de recebimento"},
        "DIFDATA":    {"type": "N(4)",  "desc": "Diferença em dias (nascimento vs registro)"},
    },

    # ================================================================
    # SIH-RD - Sistema de Informações Hospitalares (AIH Reduzida)
    # ================================================================
    "SIH-RD": {
        "UF_ZI":      {"type": "C(6)",  "desc": "UF + Zona de Informação"},
        "ANO_CMPT":   {"type": "C(4)",  "desc": "Ano de competência (aaaa)"},
        "MES_CMPT":   {"type": "C(2)",  "desc": "Mês de competência (mm)"},
        "ESPEC":      {"type": "C(2)",  "desc": "Especialidade do leito"},
        "CGC_HOSP":   {"type": "C(14)", "desc": "CNPJ do hospital"},
        "N_AIH":      {"type": "C(13)", "desc": "Número da AIH"},
        "IDENT":      {"type": "N(1)",  "desc": "Identificação: 1=Normal, 5=Longa permanência"},
        "CEP":        {"type": "C(8)",  "desc": "CEP do paciente"},
        "MUNIC_RES":  {"type": "C(6)",  "desc": "Código IBGE do município de residência"},
        "MUNIC_MOV":  {"type": "C(6)",  "desc": "Código IBGE do município de internação"},
        "NAESSION":   {"type": "C(4)",  "desc": "Relevância paciente"},
        "NACIONAL":   {"type": "C(3)",  "desc": "Nacionalidade"},
        "NUM_PROC":   {"type": "C(4)",  "desc": "Número do processamento"},
        "INSTESSION": {"type": "N(1)",  "desc": "Instrução (escolaridade)"},
        "SEXO":       {"type": "N(1)",  "desc": "Sexo: 1=Masc, 3=Fem"},
        "DT_INTER":   {"type": "C(8)",  "desc": "Data de internação (aaaammdd)"},
        "DT_SAIDA":   {"type": "C(8)",  "desc": "Data de saída (aaaammdd)"},
        "PROC_REA":   {"type": "C(10)", "desc": "Procedimento realizado (código SIGTAP)"},
        "PROC_SOLIC": {"type": "C(10)", "desc": "Procedimento solicitado (código SIGTAP)"},
        "VAL_SH":     {"type": "N(14)", "desc": "Valor dos serviços hospitalares (R$)"},
        "VAL_SP":     {"type": "N(14)", "desc": "Valor dos serviços profissionais (R$)"},
        "VAL_TOT":    {"type": "N(14)", "desc": "Valor total da AIH (R$)"},
        "VAL_UTI":    {"type": "N(14)", "desc": "Valor de UTI (R$)"},
        "US_TOT":     {"type": "N(14)", "desc": "Total de unidades de serviço"},
        "MARCA_UTI":  {"type": "N(1)",  "desc": "Marcador de UTI"},
        "UTI_MES_IN": {"type": "N(2)",  "desc": "Dias de UTI (mês de internação)"},
        "UTI_MES_AN": {"type": "N(2)",  "desc": "Dias de UTI (mês anterior)"},
        "UTI_MES_AL": {"type": "N(2)",  "desc": "Dias de UTI (mês de alta)"},
        "UTI_MES_TO": {"type": "N(2)",  "desc": "Total dias UTI"},
        "UTI_INT_IN": {"type": "N(2)",  "desc": "Dias de UTI intermediária (mês int)"},
        "UTI_INT_AN": {"type": "N(2)",  "desc": "Dias de UTI intermediária (mês ant)"},
        "UTI_INT_AL": {"type": "N(2)",  "desc": "Dias de UTI intermediária (mês alt)"},
        "UTI_INT_TO": {"type": "N(2)",  "desc": "Total dias UTI intermediária"},
        "DESSION":    {"type": "N(1)",  "desc": "Informações complementares"},
        "QTD_DIARIAS": {"type": "N(3)", "desc": "Quantidade de diárias autorizadas"},
        "DIAG_PRINC": {"type": "C(4)",  "desc": "Diagnóstico principal (CID-10)"},
        "DIAG_SECUN": {"type": "C(4)",  "desc": "Diagnóstico secundário (CID-10)"},
        "COBRANCA":   {"type": "N(2)",  "desc": "Tipo de cobrança"},
        "NATURESSION":{"type": "N(2)",  "desc": "Natureza da organização"},
        "GESTAO":     {"type": "N(1)",  "desc": "Tipo de gestão: E=Estadual, M=Municipal"},
        "IND_VDRL":   {"type": "N(1)",  "desc": "Indicador de VDRL"},
        "MUNIC_MOV2": {"type": "C(6)",  "desc": "Município de movimentação (alternativo)"},
        "CNES":       {"type": "C(7)",  "desc": "Código CNES do hospital"},
        "CNPJ_MANT":  {"type": "C(14)", "desc": "CNPJ da mantenedora"},
        "COMPLEX":    {"type": "N(2)",  "desc": "Complexidade: 01=Atenção básica, 02=Média, 03=Alta"},
        "FINANC":     {"type": "N(2)",  "desc": "Tipo de financiamento"},
        "FAESSION":   {"type": "N(2)",  "desc": "Subtipo de financiamento"},
        "REGCT":      {"type": "C(4)",  "desc": "Regra contratual"},
        "RESSION":    {"type": "N(1)",  "desc": "Raça/Cor do paciente"},
        "MORTE":      {"type": "N(1)",  "desc": "Óbito: 0=Não, 1=Sim"},
        "NAESSION2":  {"type": "N(4)",  "desc": "Data de nascimento (aaaa ou mm/aaaa)"},
        "IDADE":      {"type": "N(3)",  "desc": "Idade do paciente (codificada)"},
        "DIAS_PERM":  {"type": "N(4)",  "desc": "Dias de permanência"},
        "COBRANCA2":  {"type": "N(2)",  "desc": "Cobrança (tipo 2)"},
        "CNES_RE":    {"type": "C(7)",  "desc": "CNES de referência"},
        "CAR_INT":    {"type": "C(2)",  "desc": "Caráter da internação: 1=Eletiva, 2=Urgência, 3=Acidente, 5=Judicial, 6=Outros"},
    },

    # ================================================================
    # SIA-PA - Sistema de Informações Ambulatoriais (Procedimentos)
    # ================================================================
    "SIA-PA": {
        "PA_CODUNI":  {"type": "C(7)",  "desc": "Código CNES do estabelecimento"},
        "PA_GESTAO":  {"type": "C(6)",  "desc": "Código da gestão (UF + MUN)"},
        "PA_CONDIC":  {"type": "C(2)",  "desc": "Condição: EP=Estadual próprio, EG=Est gestão plena, MP=Mun próprio, MG=Mun gestão plena"},
        "PA_UFMUN":   {"type": "C(6)",  "desc": "Código IBGE do município do estabelecimento"},
        "PA_REGCT":   {"type": "C(4)",  "desc": "Regra contratual"},
        "PA_INCOUT":  {"type": "C(4)",  "desc": "Incremento/Outros"},
        "PA_INCURG":  {"type": "C(4)",  "desc": "Incremento urgência"},
        "PA_TPUPS":   {"type": "C(2)",  "desc": "Tipo de estabelecimento"},
        "PA_TIPPRE":  {"type": "C(2)",  "desc": "Tipo de prestador"},
        "PA_MN_IND":  {"type": "C(1)",  "desc": "Indicador: M=Mantido, I=Individual"},
        "PA_CNPJCPF": {"type": "C(14)", "desc": "CNPJ/CPF do prestador"},
        "PA_CNPJMNT": {"type": "C(14)", "desc": "CNPJ da mantenedora"},
        "PA_CNPJ_CC": {"type": "C(14)", "desc": "CNPJ do prestador (complementar)"},
        "PA_MVM":     {"type": "C(6)",  "desc": "Ano/Mês de movimento (aaaamm)"},
        "PA_CMP":     {"type": "C(6)",  "desc": "Ano/Mês de competência (aaaamm)"},
        "PA_PROC_ID": {"type": "C(10)", "desc": "Código do procedimento (SIGTAP)"},
        "PA_TPFIN":   {"type": "C(2)",  "desc": "Tipo de financiamento"},
        "PA_SUBFIN":  {"type": "C(4)",  "desc": "Subtipo de financiamento"},
        "PA_NIESSION":{"type": "C(2)",  "desc": "Nível de complexidade: 01=Atenção básica, 02=Média, 03=Alta"},
        "PA_DOESSION":{"type": "C(10)", "desc": "Documento do paciente"},
        "PA_CBESSION":{"type": "C(4)",  "desc": "CBO do profissional"},
        "PA_QTDAPR":  {"type": "N(6)",  "desc": "Quantidade aprovada"},
        "PA_QTDPRO":  {"type": "N(6)",  "desc": "Quantidade produzida"},
        "PA_VALAPR":  {"type": "N(14)", "desc": "Valor aprovado (R$)"},
        "PA_VALPRO":  {"type": "N(14)", "desc": "Valor produzido (R$)"},
        "PA_UFDIF":   {"type": "N(1)",  "desc": "UF diferente: 0=Mesma, 1=Diferente"},
        "PA_MESSION": {"type": "N(1)", "desc": "Município diferente: 0=Mesmo, 1=Diferente"},
        "PA_DIF_VAL": {"type": "N(14)", "desc": "Diferença de valores"},
        "PA_FLR":     {"type": "N(10)", "desc": "Folha de registro"},
        "PA_FLER":    {"type": "N(10)", "desc": "Folha/Registro de erro"},
        "PA_ETESSION":{"type": "N(2)",  "desc": "Idade do paciente"},
        "PA_FLIDADE": {"type": "N(1)",  "desc": "Flag de idade"},
        "PA_SEXO":    {"type": "C(1)",  "desc": "Sexo: M=Masc, F=Fem"},
        "PA_RACACOR": {"type": "C(2)",  "desc": "Raça/Cor do paciente"},
        "PA_MUNPCN":  {"type": "C(6)",  "desc": "Código IBGE do município de residência do paciente"},
        "PA_MOTSAI":  {"type": "C(2)",  "desc": "Motivo saída/permanência"},
        "PA_OBESSION":{"type": "N(1)", "desc": "Indicador de óbito"},
        "PA_NUMAPA":  {"type": "C(13)", "desc": "Número da APAC"},
        "PA_CODOCO":  {"type": "N(1)",  "desc": "Código da ocorrência"},
        "PA_AUTORIZ": {"type": "C(13)", "desc": "Número da autorização"},
        "PA_CATEND":  {"type": "C(2)",  "desc": "Caráter de atendimento"},
        "PA_CIDPRI":  {"type": "C(4)",  "desc": "CID principal (CID-10)"},
        "PA_CIDSEC":  {"type": "C(4)",  "desc": "CID secundário (CID-10)"},
        "PA_CIDCAS":  {"type": "C(4)",  "desc": "CID causas associadas (CID-10)"},
        "IDADEMIN":   {"type": "N(3)",  "desc": "Idade mínima do procedimento"},
        "IDADEMAX":   {"type": "N(3)",  "desc": "Idade máxima do procedimento"},
    },

    # ================================================================
    # SIH-SP - Serviços Profissionais (AIH)
    # ================================================================
    "SIH-SP": {
        "SP_GESTAO":  {"type": "C(6)",  "desc": "Código da gestão (UF + MUN)"},
        "SP_UF":      {"type": "C(2)",  "desc": "UF de residência do paciente"},
        "SP_AA":      {"type": "C(4)",  "desc": "Ano de competência (aaaa)"},
        "SP_MM":      {"type": "C(2)",  "desc": "Mês de competência (mm)"},
        "SP_CNES":    {"type": "C(7)",  "desc": "Código CNES do estabelecimento"},
        "SP_NAIH":    {"type": "C(13)", "desc": "Número da AIH"},
        "SP_PROCREA": {"type": "C(10)", "desc": "Procedimento realizado (SIGTAP)"},
        "SP_ATOPROF": {"type": "C(10)", "desc": "Ato profissional / procedimento (SIGTAP)"},
        "SP_QTD_ATO": {"type": "N(6)",  "desc": "Quantidade do ato profissional"},
        "SP_PTSP":    {"type": "N(1)",  "desc": "Indicador de ponto (serviço profissional)"},
        "SP_NF":      {"type": "N(1)",  "desc": "Indicador de nota fiscal"},
        "SP_VALATO":  {"type": "N(14)", "desc": "Valor do ato profissional (R$)"},
        "SP_M_HOSP":  {"type": "N(1)",  "desc": "Indicador de mês/hospitalar"},
        "SP_M_PAC":   {"type": "N(1)",  "desc": "Indicador relativo ao paciente"},
        "SP_DES_HOSP":{"type": "N(1)",  "desc": "Desconto hospitalar"},
        "SP_DES_PAC": {"type": "N(1)",  "desc": "Desconto do paciente"},
        "SP_COMPLEX": {"type": "N(2)",  "desc": "Complexidade: 01=Básica, 02=Média, 03=Alta"},
        "SP_FINANC":  {"type": "N(2)",  "desc": "Tipo de financiamento"},
        "SP_CO_FAEC": {"type": "C(6)",  "desc": "Subtipo de financiamento (FAEC)"},
        "SP_PF_CBO":  {"type": "C(6)",  "desc": "CBO do profissional executante"},
        "SP_PF_DOC":  {"type": "C(15)", "desc": "Documento do profissional (CNS/CPF)"},
        "SP_PJ_DOC":  {"type": "C(14)", "desc": "Documento da pessoa jurídica (CNPJ)"},
        "IN_TP_VAL":  {"type": "N(1)",  "desc": "Indicador de tipo de valor"},
        "SERV_CLA":   {"type": "C(6)",  "desc": "Serviço/Classificação"},
        "SP_CIDPRI":  {"type": "C(4)",  "desc": "CID principal (CID-10)"},
        "SP_CIDSEC":  {"type": "C(4)",  "desc": "CID secundário (CID-10)"},
        "SP_QT_PROC": {"type": "N(6)",  "desc": "Quantidade do procedimento"},
        "SP_U_AIH":   {"type": "C(13)", "desc": "AIH de referência (unificação)"},
    },

    # ================================================================
    # SIA-APAC - Campos comuns aos grupos APAC/RAAS do SIA
    #   (AM, AQ, AR, AN, ATD, AD, AB, ABO, ACF, AMP, PS, SAD)
    # ================================================================
    "SIA-APAC": {
        "AP_MVM":     {"type": "C(6)",  "desc": "Ano/Mês de movimento (aaaamm)"},
        "AP_CONDIC":  {"type": "C(2)",  "desc": "Condição da gestão (EP/EG/MP/MG)"},
        "AP_GESTAO":  {"type": "C(6)",  "desc": "Código da gestão (UF + MUN)"},
        "AP_CODUNI":  {"type": "C(7)",  "desc": "Código CNES do estabelecimento"},
        "AP_AUTORIZ": {"type": "C(13)", "desc": "Número da APAC"},
        "AP_CMP":     {"type": "C(6)",  "desc": "Ano/Mês de competência (aaaamm)"},
        "AP_PRIPAL":  {"type": "C(10)", "desc": "Procedimento principal (SIGTAP)"},
        "AP_VL_AP":   {"type": "N(14)", "desc": "Valor total da APAC (R$)"},
        "AP_UFMUN":   {"type": "C(6)",  "desc": "Código IBGE do município do estabelecimento"},
        "AP_TPUPS":   {"type": "C(2)",  "desc": "Tipo de estabelecimento"},
        "AP_TIPPRE":  {"type": "C(2)",  "desc": "Tipo de prestador"},
        "AP_MN_IND":  {"type": "C(1)",  "desc": "Mantido (M) ou Individual (I)"},
        "AP_CNPJCPF": {"type": "C(14)", "desc": "CNPJ/CPF do prestador"},
        "AP_CNPJMNT": {"type": "C(14)", "desc": "CNPJ da mantenedora"},
        "AP_CNSPCN":  {"type": "C(15)", "desc": "Cartão Nacional de Saúde do paciente"},
        "AP_COIDADE": {"type": "C(1)",  "desc": "Código da unidade de idade"},
        "AP_NUIDADE": {"type": "N(3)",  "desc": "Idade do paciente"},
        "AP_SEXO":    {"type": "C(1)",  "desc": "Sexo: M=Masc, F=Fem"},
        "AP_RACACOR": {"type": "C(2)",  "desc": "Raça/Cor do paciente"},
        "AP_MUNPCN":  {"type": "C(6)",  "desc": "Código IBGE do município de residência do paciente"},
        "AP_UFNACIO": {"type": "C(3)",  "desc": "Nacionalidade do paciente"},
        "AP_CEPPCN":  {"type": "C(8)",  "desc": "CEP do paciente"},
        "AP_UFDIF":   {"type": "N(1)",  "desc": "UF de residência diferente da de atendimento"},
        "AP_MNDIF":   {"type": "N(1)",  "desc": "Município de residência diferente"},
        "AP_DTINIC":  {"type": "C(8)",  "desc": "Data de início da validade da APAC (aaaammdd)"},
        "AP_DTFIM":   {"type": "C(8)",  "desc": "Data de fim da validade da APAC (aaaammdd)"},
        "AP_TPATEN":  {"type": "C(2)",  "desc": "Tipo de atendimento"},
        "AP_TPAPAC":  {"type": "C(1)",  "desc": "Tipo de APAC: 1=Inicial, 2=Continuidade, 3=Única"},
        "AP_MOTSAI":  {"type": "C(2)",  "desc": "Motivo de saída/permanência"},
        "AP_OBITO":   {"type": "N(1)",  "desc": "Óbito: 1=Sim, 0=Não"},
        "AP_ENCERR":  {"type": "N(1)",  "desc": "Encerramento"},
        "AP_PERMAN":  {"type": "N(1)",  "desc": "Permanência"},
        "AP_ALTA":    {"type": "N(1)",  "desc": "Alta"},
        "AP_TRANSF":  {"type": "N(1)",  "desc": "Transferência"},
        "AP_DTOCOR":  {"type": "C(8)",  "desc": "Data de ocorrência (saída/óbito) (aaaammdd)"},
        "AP_CODEMI":  {"type": "C(10)", "desc": "Código do órgão emissor da APAC"},
        "AP_CATEND":  {"type": "C(2)",  "desc": "Caráter de atendimento"},
        "AP_APACANT": {"type": "C(13)", "desc": "Número da APAC anterior"},
        "AP_UNISOL":  {"type": "C(7)",  "desc": "CNES da unidade solicitante"},
        "AP_DTSOLIC": {"type": "C(8)",  "desc": "Data da solicitação (aaaammdd)"},
        "AP_DTAUT":   {"type": "C(8)",  "desc": "Data da autorização (aaaammdd)"},
        "AP_CIDCAS":  {"type": "C(4)",  "desc": "CID causa associada (CID-10)"},
        "AP_CIDPRI":  {"type": "C(4)",  "desc": "CID principal (CID-10)"},
        "AP_CIDSEC":  {"type": "C(4)",  "desc": "CID secundário (CID-10)"},
        "AP_ETNIA":   {"type": "C(4)",  "desc": "Etnia (quando indígena)"},
        "AP_NATJUR":  {"type": "C(4)",  "desc": "Natureza jurídica do estabelecimento"},
    },

    # ================================================================
    # SINAN - Campos comuns a TODOS os agravos do SINAN
    # ================================================================
    "SINAN_COMMON": {
        "TP_NOT":      {"type": "N(1)",  "desc": "Tipo de notificação: 1=Negativa, 2=Individual, 3=Surto, 4=Agregado"},
        "ID_AGRAVO":   {"type": "C(4)",  "desc": "Código do agravo (CID-10)"},
        "DT_NOTIFIC":  {"type": "D",     "desc": "Data da notificação"},
        "SEM_NOT":     {"type": "N(6)",  "desc": "Semana epidemiológica da notificação (aaaa+se)"},
        "NU_ANO":      {"type": "N(4)",  "desc": "Ano da notificação"},
        "SG_UF_NOT":   {"type": "C(2)",  "desc": "UF de notificação"},
        "ID_MUNICIP":  {"type": "C(6)",  "desc": "Código IBGE do município de notificação"},
        "ID_REGIONA":  {"type": "C(6)",  "desc": "Código da regional de saúde"},
        "ID_UNIDADE":  {"type": "C(7)",  "desc": "Código CNES da unidade de saúde"},
        "DT_SIN_PRI":  {"type": "D",     "desc": "Data dos primeiros sintomas"},
        "SEM_PRI":     {"type": "N(6)",  "desc": "Semana epidemiológica dos primeiros sintomas"},
        "DT_NASC":     {"type": "D",     "desc": "Data de nascimento do paciente"},
        "NU_IDADE_N":  {"type": "N(4)",  "desc": "Idade (codificada): 1ºdig=tipo(1=hora,2=dia,3=mês,4=ano), demais=valor"},
        "CS_SEXO":     {"type": "C(1)",  "desc": "Sexo: M=Masculino, F=Feminino, I=Ignorado"},
        "CS_GESTANT":  {"type": "N(1)",  "desc": "Gestante: 1=1ºTri, 2=2ºTri, 3=3ºTri, 4=IG desconhecida, 5=Não, 6=Não se aplica, 9=Ignorado"},
        "CS_RACA":     {"type": "N(1)",  "desc": "Raça/Cor: 1=Branca, 2=Preta, 3=Amarela, 4=Parda, 5=Indígena, 9=Ignorado"},
        "CS_ESCOL_N":  {"type": "N(2)",  "desc": "Escolaridade: 0=Analfabeto, 1-3=Fundamental, 4=Médio inc, 5=Médio compl, 6-8=Superior, 9=Ignorado, 10=Não se aplica"},
        "SG_UF":       {"type": "C(2)",  "desc": "UF de residência"},
        "ID_MN_RESI":  {"type": "C(6)",  "desc": "Código IBGE do município de residência"},
        "ID_RG_RESI":  {"type": "C(6)",  "desc": "Regional de saúde de residência"},
        "ID_PAIS":     {"type": "C(4)",  "desc": "Código do país de residência"},
        "DT_INVEST":   {"type": "D",     "desc": "Data de investigação"},
        "ID_OCUPA_N":  {"type": "C(6)",  "desc": "Ocupação (CBO-2002)"},
        "CLASSI_FIN":  {"type": "N(1)",  "desc": "Classificação final: valores variam por agravo"},
        "CRITERIO":    {"type": "N(1)",  "desc": "Critério de confirmação: 1=Lab, 2=Clínico-epidemiológico"},
        "EVOLUCAO":    {"type": "N(1)",  "desc": "Evolução: 1=Cura, 2=Óbito pelo agravo, 3=Óbito outras causas, 9=Ignorado"},
        "DT_OBITO":    {"type": "D",     "desc": "Data do óbito"},
        "DT_ENCERRA":  {"type": "D",     "desc": "Data de encerramento"},
        "DT_DIGITA":   {"type": "D",     "desc": "Data de digitação"},
        "NU_NOTIFIC":  {"type": "C(7)",  "desc": "Número da notificação"},
        "FLESSION":    {"type": "N(1)",  "desc": "Indicador de fluxo"},
    },

    # ================================================================
    # CNES-ST - Estabelecimentos de Saúde
    # ================================================================ 
    "CNES-ST": {
        "CNES":        {"type": "C(7)",  "desc": "Código CNES do estabelecimento"},
        "CODUFMUN":    {"type": "C(6)",  "desc": "Código IBGE do município"},
        "COD_CEP":     {"type": "C(8)",  "desc": "CEP do estabelecimento"},
        "CPF_CNPJ":    {"type": "C(14)", "desc": "CPF ou CNPJ do estabelecimento"},
        "FANTESSION":  {"type": "C(60)", "desc": "Nome fantasia do estabelecimento"},
        "RAZESSION":   {"type": "C(60)", "desc": "Razão social do estabelecimento"},
        "VINC_SUS":    {"type": "N(1)",  "desc": "Vínculo com SUS: 1=Sim, 0=Não"},
        "TPGESTAO":    {"type": "C(1)",  "desc": "Tipo de gestão: E=Estadual, M=Municipal, D=Dupla, S=Sem gestão"},
        "PF_PJ":       {"type": "N(1)",  "desc": "Pessoa Física ou Jurídica: 1=PF, 3=PJ"},
        "NIV_DEP":     {"type": "N(1)",  "desc": "Nível de dependência: 1=Individual, 2=Mantido, 3=Filial"},
        "COD_IR":      {"type": "N(2)",  "desc": "Código na Receita Federal"},
        "ESESSION_P":  {"type": "N(2)",  "desc": "Esfera administrativa: 01=Federal, 02=Estadual, 03=Municipal, 04=Privada"},
        "RETESSION":   {"type": "N(2)",  "desc": "Retenção de tributos"},
        "ESSION_PR":   {"type": "N(1)",  "desc": "Atividade de ensino/pesquisa"},
        "NATURESSION": {"type": "N(2)",  "desc": "Natureza da organização"},
        "CLIENTEL":    {"type": "N(1)",  "desc": "Fluxo de clientela: 1=Atend demanda espontânea, 2=Referência, 3=Ambos"},
        "TP_UNID":     {"type": "N(2)",  "desc": "Tipo de unidade: 01=Central consultório, 02=Centro saúde, 05=Hospital geral, 07=Hospital especializado..."},
        "TURESSION":   {"type": "N(1)",  "desc": "Turno de atendimento"},
        "NIV_HIER":    {"type": "N(2)",  "desc": "Nível de hierarquia: 01=PAB, 02=Média M1, 03=Média M2-M3, 04=Alta"},
        "TP_PREST":    {"type": "C(2)",  "desc": "Tipo de prestador"},
        "COMPESSION":  {"type": "C(6)", "desc": "Competência (aaaamm)"},
    },

    # ================================================================
    # CNES-LT - Leitos
    # ================================================================
    "CNES-LT": {
        "CNES":        {"type": "C(7)",  "desc": "Código CNES do estabelecimento"},
        "CODUFMUN":    {"type": "C(6)",  "desc": "Código IBGE do município"},
        "TP_LEITO":    {"type": "N(2)",  "desc": "Tipo de leito: 01=Cirúrgico, 02=Clínico, 03=Complementar, 04=Obstétrico, 05=Pediátrico, 06=Outras especialidades, 07=Hospital dia"},
        "CODLEITO":    {"type": "C(2)",  "desc": "Código do leito (subtipo)"},
        "QT_EXIST":    {"type": "N(4)",  "desc": "Quantidade de leitos existentes"},
        "QT_CONTR":    {"type": "N(4)",  "desc": "Quantidade de leitos contratados SUS"},
        "QT_SUS":      {"type": "N(4)",  "desc": "Quantidade disponível SUS"},
        "COMPESSION":  {"type": "C(6)", "desc": "Competência (aaaamm)"},
    },

    # ================================================================
    # CNES-PF - Profissionais
    # ================================================================
    "CNES-PF": {
        "CNES":        {"type": "C(7)",  "desc": "Código CNES do estabelecimento"},
        "CODUFMUN":    {"type": "C(6)",  "desc": "Código IBGE do município"},
        "CBO":         {"type": "C(6)",  "desc": "Código CBO do profissional"},
        "CBOUNICO":    {"type": "C(6)",  "desc": "CBO único (desambiguação)"},
        "NOMEPROF":    {"type": "C(60)", "desc": "Nome do profissional"},
        "CNS_PROF":    {"type": "C(15)", "desc": "Cartão Nacional de Saúde do profissional"},
        "CONSESSION":  {"type": "C(10)", "desc": "Número do conselho de classe"},
        "VINCULAC":    {"type": "C(6)",  "desc": "Tipo de vínculo empregatício"},
        "VINCULSION":  {"type": "C(1)",  "desc": "Vínculo SUS: S=Sim, N=Não"},
        "HOESSION":    {"type": "N(3)",  "desc": "Carga horária ambulatorial SUS"},
        "HOESSION2":   {"type": "N(3)",  "desc": "Carga horária hospitalar SUS"},
        "COMPESSION":  {"type": "C(6)", "desc": "Competência (aaaamm)"},
    },

    # ================================================================
    # CNES-EP - Equipamentos
    # ================================================================
    "CNES-EP": {
        "CNES":        {"type": "C(7)",  "desc": "Código CNES do estabelecimento"},
        "CODUFMUN":    {"type": "C(6)",  "desc": "Código IBGE do município"},
        "CODEQUIP":    {"type": "C(6)",  "desc": "Código do tipo de equipamento"},
        "TIPEQUIP":    {"type": "C(2)",  "desc": "Tipo de equipamento"},
        "QT_EXIST":    {"type": "N(3)",  "desc": "Quantidade existente"},
        "QT_USO":      {"type": "N(3)",  "desc": "Quantidade em uso"},
        "IND_SUS":     {"type": "N(1)",  "desc": "Indicador SUS: 1=Sim, 0=Não"},
        "IND_NSUS":    {"type": "N(1)",  "desc": "Indicador Não-SUS: 1=Sim, 0=Não"},
        "COMPESSION":  {"type": "C(6)", "desc": "Competência (aaaamm)"},
    },

    # ================================================================
    # CIHA - Comunicação de Internação Hospitalar e Ambulatorial
    # ================================================================
    "CIHA": {
        "ANO_CMPT":   {"type": "C(4)",  "desc": "Ano de competência"},
        "MES_CMPT":   {"type": "C(2)",  "desc": "Mês de competência"},
        "CNES":       {"type": "C(7)",  "desc": "Código CNES do hospital"},
        "MUNIC_MOV":  {"type": "C(6)",  "desc": "Código IBGE do município de internação"},
        "MUNIC_RES":  {"type": "C(6)",  "desc": "Código IBGE do município de residência do paciente"},
        "SEXO":       {"type": "C(1)",  "desc": "Sexo: M=Masc, F=Fem"},
        "NASC":       {"type": "C(8)",  "desc": "Data de nascimento (aaaammdd)"},
        "IDADE":      {"type": "N(3)",  "desc": "Idade do paciente (codificada)"},
        "PROC_REA":   {"type": "C(10)", "desc": "Procedimento realizado (SIGTAP)"},
        "DIAG_PRINC": {"type": "C(4)",  "desc": "Diagnóstico principal (CID-10)"},
        "DIAG_SECUN": {"type": "C(4)",  "desc": "Diagnóstico secundário (CID-10)"},
        "DT_INTER":   {"type": "C(8)",  "desc": "Data de internação (aaaammdd)"},
        "DT_SAIDA":   {"type": "C(8)",  "desc": "Data de saída (aaaammdd)"},
        "DIAS_PERM":  {"type": "N(4)",  "desc": "Dias de permanência"},
        "CAR_INT":    {"type": "C(2)",  "desc": "Caráter da internação: 1=Eletiva, 2=Urgência"},
        "COMPLEX":    {"type": "N(2)",  "desc": "Complexidade"},
        "COBRANCA":   {"type": "N(2)",  "desc": "Tipo de cobrança"},
        "RACACOR":    {"type": "N(1)",  "desc": "Raça/Cor do paciente"},
    },

    # ================================================================
    # PNI - Programa Nacional de Imunizações
    # ================================================================
    "PNI": {
        "DT_ATEND":   {"type": "C(8)",  "desc": "Data de atendimento (ddmmaaaa)"},
        "ID_PACIENTE": {"type": "C(15)", "desc": "Identificador do paciente (CNS)"},
        "CO_UF":      {"type": "C(2)",  "desc": "UF de atendimento"},
        "CO_MUN_ATD": {"type": "C(6)",  "desc": "Código IBGE do município de atendimento"},
        "CO_MUN_RES": {"type": "C(6)",  "desc": "Código IBGE do município de residência"},
        "CO_CNES":    {"type": "C(7)",  "desc": "Código CNES da unidade"},
        "NU_LOTE":    {"type": "C(10)", "desc": "Número do lote da vacina"},
        "CO_IMUNO":   {"type": "C(5)",  "desc": "Código do imunobiológico"},
        "DS_IMUNO":   {"type": "C(50)", "desc": "Descrição do imunobiológico"},
        "NU_DOSE":    {"type": "C(2)",  "desc": "Número da dose (1,2,3,R=Reforço)"},
        "CO_LABORAT": {"type": "C(4)",  "desc": "Código do laboratório produtor"},
        "DT_NASC":    {"type": "C(8)",  "desc": "Data de nascimento (ddmmaaaa)"},
        "NU_IDADE":   {"type": "N(3)",  "desc": "Idade do paciente"},
        "CS_SEXO":    {"type": "C(1)",  "desc": "Sexo: M=Masc, F=Fem"},
        "CS_RACA":    {"type": "N(1)",  "desc": "Raça/Cor: 1=Branca, 2=Preta, 3=Amarela, 4=Parda, 5=Indígena"},
        "SISTEMA":    {"type": "C(5)",  "desc": "Sistema de origem"},
        "COMPET":     {"type": "C(6)",  "desc": "Competência (aaaamm)"},
    },
}


def get_metadata_for_system(system_code):
    """
    Retorna os metadados (colunas, tipos, descrições) para um sistema.
    Para SINAN, combina campos comuns + campos específicos (se disponíveis).
    Retorna: dict {coluna: {type, desc}}
    """
    # Verificar match direto
    if system_code in METADATA_CATALOG:
        return METADATA_CATALOG[system_code]
    
    # Para agravos do SINAN, retornar os campos comuns
    if system_code.startswith("SINAN-"):
        return METADATA_CATALOG.get("SINAN_COMMON", {})
    
    # Para variantes do CNES não mapeadas, usar CNES-ST como base
    if system_code.startswith("CNES-"):
        return METADATA_CATALOG.get("CNES-ST", {})
    
    # SIH-RJ/ER espelham a AIH Reduzida (SIH-RD); SIH-SP tem catálogo próprio
    if system_code.startswith("SIH-"):
        return METADATA_CATALOG.get("SIH-RD", {})
    
    # Grupos APAC/RAAS do SIA compartilham os campos AP_*; SIA-BI aproxima do PA
    if system_code == "SIA-BI":
        return METADATA_CATALOG.get("SIA-PA", {})
    if system_code.startswith("SIA-"):
        return METADATA_CATALOG.get("SIA-APAC", {})
    
    return {}


def get_metadata_as_dataframe(system_code):
    """
    Retorna um DataFrame formatado com os metadados de um sistema.
    Colunas: Variável, Tipo, Formato, Descrição
    """
    import pandas as pd
    
    meta = get_metadata_for_system(system_code)
    if not meta:
        return pd.DataFrame(columns=["Variável", "Tipo", "Formato", "Descrição"])
    
    rows = []
    for col_name, col_info in meta.items():
        tipo_raw = col_info["type"]
        # Extrair tipo base e formato
        if tipo_raw == "D":
            tipo = "Data"
            formato = "dd/mm/aaaa"
        elif tipo_raw.startswith("C"):
            tipo = "Texto"
            formato = tipo_raw  # ex: C(8)
        elif tipo_raw.startswith("N"):
            tipo = "Numérico"
            formato = tipo_raw  # ex: N(4)
        else:
            tipo = tipo_raw
            formato = "-"
        
        rows.append({
            "Variável": col_name,
            "Tipo": tipo,
            "Formato": formato,
            "Descrição": col_info["desc"],
        })
    
    return pd.DataFrame(rows)


# ================================================================
# CATÁLOGO DE CHAVES DE JOIN ENTRE BASES DATASUS
# ================================================================
# Define grupos semânticos de campos que podem ser usados para joins
# Cada grupo representa um conceito unificador (município, estabelecimento, etc)

JOIN_KEYS_CATALOG = {
    # ---- CHAVES GEOGRÁFICAS ----
    "municipio_residencia": {
        "desc": "Código IBGE do Município de Residência",
        "campos": {
            "SIM-DO":      "CODMUNRES",
            "SINASC":      "CODMUNRES",
            "SIH-RD":      "MUNIC_RES",
            "SIA-PA":      "PA_MUNPCN",
            "SIA-APAC":    "AP_MUNPCN",
            "SINAN_COMMON":"ID_MN_RESI",
            "CIHA":        "MUNIC_RES",
            "PNI":         "CO_MUN_RES",
        },
        "tipo": "C(6)",
        "ref_table": "IBGE Municípios",
    },
    "municipio_ocorrencia": {
        "desc": "Código IBGE do Município de Ocorrência/Atendimento",
        "campos": {
            "SIM-DO":      "CODMUNOCOR",
            "SINASC":      "CODMUNNASC",
            "SIH-RD":      "MUNIC_MOV",
            "SIA-PA":      "PA_UFMUN",
            "SIA-APAC":    "AP_UFMUN",
            "SINAN_COMMON":"ID_MUNICIP",
            "CNES-ST":     "CODUFMUN",
            "CNES-LT":     "CODUFMUN",
            "CNES-PF":     "CODUFMUN",
            "CNES-EP":     "CODUFMUN",
            "CIHA":        "MUNIC_MOV",
            "PNI":         "CO_MUN_ATD",
        },
        "tipo": "C(6)",
        "ref_table": "IBGE Municípios",
    },
    
    # ---- CHAVES DE ESTABELECIMENTO ----
    "cnes_estabelecimento": {
        "desc": "Código CNES do Estabelecimento de Saúde",
        "campos": {
            "SIM-DO":      "CODESTAB",
            "SINASC":      "CODESTAB",
            "SIH-RD":      "CNES",
            "SIH-SP":      "SP_CNES",
            "SIA-PA":      "PA_CODUNI",
            "SIA-APAC":    "AP_CODUNI",
            "SINAN_COMMON":"ID_UNIDADE",
            "CNES-ST":     "CNES",
            "CNES-LT":     "CNES",
            "CNES-PF":     "CNES",
            "CNES-EP":     "CNES",
            "CIHA":        "CNES",
            "PNI":         "CO_CNES",
        },
        "tipo": "C(7)",
        "ref_table": "CNES Estabelecimentos",
    },
    
    # ---- CHAVES DE DIAGNÓSTICO ----
    "cid10_principal": {
        "desc": "Diagnóstico Principal (CID-10)",
        "campos": {
            "SIM-DO":      "CAUSABAS",
            "SIH-RD":      "DIAG_PRINC",
            "SIA-PA":      "PA_CIDPRI",
            "SINAN_COMMON":"ID_AGRAVO",
            "CIHA":        "DIAG_PRINC",
        },
        "tipo": "C(4)",
        "ref_table": "CID-10",
    },
    "cid10_secundario": {
        "desc": "Diagnóstico Secundário (CID-10)",
        "campos": {
            "SIH-RD":      "DIAG_SECUN",
            "SIA-PA":      "PA_CIDSEC",
            "CIHA":        "DIAG_SECUN",
        },
        "tipo": "C(4)",
        "ref_table": "CID-10",
    },
    
    # ---- CHAVES DE PROCEDIMENTO ----
    "sigtap_procedimento": {
        "desc": "Código do Procedimento (SIGTAP)",
        "campos": {
            "SIH-RD":      "PROC_REA",
            "SIA-PA":      "PA_PROC_ID",
            "CIHA":        "PROC_REA",
        },
        "tipo": "C(10)",
        "ref_table": "SIGTAP",
    },
    
    # ---- CHAVES DE OCUPAÇÃO ----
    "cbo_ocupacao": {
        "desc": "Código da Ocupação (CBO)",
        "campos": {
            "SIM-DO":      "OCUP",
            "SINASC":      "CODOCUPMAE",
            "SINAN_COMMON":"ID_OCUPA_N",
            "CNES-PF":     "CBO",
        },
        "tipo": "C(6)",
        "ref_table": "CBO",
    },
    
    # ---- CHAVES TEMPORAIS ----
    "ano_competencia": {
        "desc": "Ano de Competência/Referência",
        "campos": {
            "SIH-RD":      "ANO_CMPT",
            "CIHA":        "ANO_CMPT",
            "SINAN_COMMON":"NU_ANO",
        },
        "tipo": "C(4)|N(4)",
        "ref_table": None,
    },
    "mes_competencia": {
        "desc": "Mês de Competência",
        "campos": {
            "SIH-RD":      "MES_CMPT",
            "CIHA":        "MES_CMPT",
        },
        "tipo": "C(2)",
        "ref_table": None,
    },
    "competencia_aaaamm": {
        "desc": "Competência (AAAAMM)",
        "campos": {
            "SIA-PA":      "PA_CMP",
            "SIA-APAC":    "AP_CMP",
            "CNES-ST":     "COMPESSION",
            "CNES-LT":     "COMPESSION",
            "CNES-PF":     "COMPESSION",
            "CNES-EP":     "COMPESSION",
            "PNI":         "COMPET",
        },
        "tipo": "C(6)",
        "ref_table": None,
    },

    # ---- CHAVES DE PACIENTE (ligação exata do mesmo paciente/atendimento) ----
    "aih_numero": {
        "desc": "Número da AIH — liga SIH-RD ↔ SIH-SP da mesma internação (mesmo paciente)",
        "campos": {
            "SIH-RD":      "N_AIH",
            "SIH-SP":      "SP_NAIH",
        },
        "tipo": "C(13)",
        "ref_table": None,
    },
    "cns_paciente": {
        "desc": "CNS do paciente (criptografado) — liga registros APAC do mesmo paciente",
        "campos": {
            "SIA-APAC":    "AP_CNSPCN",
        },
        "tipo": "C(15)",
        "ref_table": None,
    },
}


def get_join_suggestions(selected_systems):
    """
    Dado uma lista de sistemas selecionados, retorna sugestões de joins possíveis.
    
    Args:
        selected_systems: lista de códigos de sistemas (ex: ["SIM-DO", "SIH-RD"])
    
    Returns:
        Lista de dicts com sugestões de join:
        [
            {
                "chave": "municipio_residencia",
                "descricao": "Código IBGE do Município de Residência",
                "sistemas_compativeis": ["SIM-DO", "SIH-RD"],
                "mapeamento": {"SIM-DO": "CODMUNRES", "SIH-RD": "MUNIC_RES"},
                "ref_table": "IBGE Municípios",
                "qualidade": "alta"  # alta, media, baixa
            },
            ...
        ]
    """
    suggestions = []
    
    # Normalizar nomes dos sistemas (subgrupos SIA/SIH → base canônica de campos)
    def normalize_system(sys):
        if sys.startswith("SINAN-"):
            return "SINAN_COMMON"
        if sys in ("SIA-PA", "SIA-BI"):
            return "SIA-PA"
        if sys.startswith("SIA-"):
            return "SIA-APAC"
        if sys.startswith("SIH-") and sys not in ("SIH-RD", "SIH-SP"):
            return "SIH-RD"
        return sys
    
    normalized_systems = [normalize_system(s) for s in selected_systems]
    original_map = dict(zip(normalized_systems, selected_systems))
    
    for key_name, key_info in JOIN_KEYS_CATALOG.items():
        # Encontrar quais sistemas selecionados têm essa chave
        matching_systems = []
        mapping = {}
        
        for norm_sys, orig_sys in zip(normalized_systems, selected_systems):
            if norm_sys in key_info["campos"]:
                matching_systems.append(orig_sys)
                mapping[orig_sys] = key_info["campos"][norm_sys]
        
        # Só sugerir se pelo menos 2 sistemas podem usar essa chave
        if len(matching_systems) >= 2:
            # Avaliar qualidade do join
            if key_name in ["aih_numero", "cns_paciente", "municipio_residencia",
                            "municipio_ocorrencia", "cnes_estabelecimento"]:
                qualidade = "alta"
            elif key_name in ["cid10_principal", "sigtap_procedimento"]:
                qualidade = "media"
            else:
                qualidade = "baixa"
            
            suggestions.append({
                "chave": key_name,
                "descricao": key_info["desc"],
                "sistemas_compativeis": matching_systems,
                "mapeamento": mapping,
                "ref_table": key_info.get("ref_table"),
                "tipo": key_info["tipo"],
                "qualidade": qualidade,
            })
    
    # Ordenar por qualidade (alta primeiro) e número de sistemas compatíveis
    qualidade_ordem = {"alta": 0, "media": 1, "baixa": 2}
    suggestions.sort(key=lambda x: (qualidade_ordem[x["qualidade"]], -len(x["sistemas_compativeis"])))
    
    return suggestions


def get_join_suggestions_as_dataframe(selected_systems):
    """
    Retorna sugestões de join formatadas como DataFrame para exibição.
    """
    import pandas as pd
    
    suggestions = get_join_suggestions(selected_systems)
    
    if not suggestions:
        return pd.DataFrame(columns=["Chave de Join", "Descrição", "Bases Compatíveis", "Campos", "Qualidade"])
    
    rows = []
    for s in suggestions:
        campos_str = " ↔ ".join([f"{sys}:{col}" for sys, col in s["mapeamento"].items()])
        rows.append({
            "Chave de Join": s["chave"].replace("_", " ").title(),
            "Descrição": s["descricao"],
            "Bases Compatíveis": ", ".join(s["sistemas_compativeis"]),
            "Campos": campos_str,
            "Qualidade": {"alta": "🟢 Alta", "media": "🟡 Média", "baixa": "🔴 Baixa"}[s["qualidade"]],
            "Tabela Referência": s["ref_table"] or "-",
        })
    
    return pd.DataFrame(rows)


def generate_join_code(selected_systems, join_key, base_system=None):
    """
    Gera código Python/Pandas para executar o join entre os sistemas.
    
    Args:
        selected_systems: lista de sistemas
        join_key: nome da chave de join (ex: "municipio_residencia")
        base_system: sistema base para o join (opcional, usa primeiro se não especificado)
    
    Returns:
        String com código Python comentado
    """
    suggestions = get_join_suggestions(selected_systems)
    join_info = next((s for s in suggestions if s["chave"] == join_key), None)
    
    if not join_info:
        return "# Chave de join não encontrada para os sistemas selecionados"
    
    mapping = join_info["mapeamento"]
    systems = list(mapping.keys())
    
    if base_system is None:
        base_system = systems[0]
    
    code_lines = [
        f"# Join por: {join_info['descricao']}",
        f"# Qualidade do Join: {join_info['qualidade']}",
        "",
    ]
    
    # Gerar merge sequencial
    code_lines.append(f"df_merged = df_{base_system.lower().replace('-', '_')}.copy()")
    
    for sys in systems:
        if sys == base_system:
            continue
        
        left_col = mapping[base_system]
        right_col = mapping[sys]
        sys_var = sys.lower().replace('-', '_')
        
        code_lines.append(f"")
        code_lines.append(f"# Merge com {sys}")
        code_lines.append(f"df_merged = df_merged.merge(")
        code_lines.append(f"    df_{sys_var},")
        code_lines.append(f"    left_on='{left_col}',")
        code_lines.append(f"    right_on='{right_col}',")
        code_lines.append(f"    how='left',  # ou 'inner' para manter só matches")
        code_lines.append(f"    suffixes=('', '_{sys_var}')")
        code_lines.append(f")")
    
    return "\n".join(code_lines)
