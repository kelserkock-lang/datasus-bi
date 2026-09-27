"""
datasus_engine.py — Motor de ingestão e consulta do DataSUS com memória controlada.
================================================================================

Substitui o carregamento integral em pandas por uma arquitetura em duas camadas:

    .dbc  --FTP-->  .dbf  --lotes-->  Parquet (staging)  --DuckDB-->  resultado

Por que isso resolve o estouro de memória
-----------------------------------------
O caminho antigo (`download_and_process_datasus`) fazia:

    DBF(load=True) -> DataFrame          # pico ~3x o tamanho final
    dfs.append(df)  (todos os anos/meses # tudo residente em RAM, ao mesmo tempo
    pd.concat(dfs)                       # + mais uma cópia completa

Em uma base como o SIA (município/estado por vários anos) isso gera
`2 x N` DataFrames simultâneos e estoura a RAM.

Aqui:

  * a leitura do DBF acontece em LOTES (`batch_size` registros). O pico de
    memória é proporcional ao lote, NÃO ao tamanho da base;
  * cada arquivo-fonte vira um Parquet em disco (17x menor que o DBF, no teste
    real com RDSC1709);
  * não existe `pd.concat` de bases inteiras — o DuckDB lê a lista de Parquet
    com *projection pushdown* e *predicate pushdown*, processando em fluxo;
  * o DuckDB recebe `memory_limit` e `temp_directory`, então passa a
    derramar em disco (out-of-core) em vez de estourar a RAM.

O DataFrame pandas só é materializado no final, já filtrado e projetado —
e é a única etapa que consome memória proporcional ao resultado.

Compatibilidade
---------------
`load_full_datasus()` mantém assinatura e semântica equivalentes à versão
antiga (mesmo filtro de município, mesmo filtro CID, mesma seleção de colunas),
para que `app.py` continue funcionando sem alterações.

Diferença conhecida: ORDEM DAS LINHAS
-------------------------------------
Sem filtros, a ordem do arquivo-fonte é preservada (verificado). Quando há
`WHERE` (município/CID), o scan paralelo do DuckDB pode devolver as MESMAS
linhas em ordem diferente. O CONTEÚDO é idêntico — verificado comparando o
conjunto completo de linhas ordenadas (multiset equality).

Não impomos `ORDER BY` para garantir ordem porque ordenar um resultado grande
custa memória/tempo — exatamente o que este motor existe para evitar. Para
análises do DataSUS a ordem não tem significado; se precisar de ordem estável,
ordene o DataFrame resultante explicitamente.
"""

from __future__ import annotations

import glob
import hashlib
import os
import shutil
from typing import Iterator, Optional, Sequence

import pandas as pd

from data_ingestion import (
    MUNI_FILTER_FIELDS,
    SYSTEMS_CATALOG,
    UF_CODIGO_IBGE,
    UF_FILTER_FIELDS,
    _connect_ftp,
    _decompress_dbc,
    _resolve_system_code,
)

# ============================================================================
# Configuração
# ============================================================================

DATA_DIR = "data"
STAGING_DIR = os.path.join(DATA_DIR, "staging")
TEMP_DIR = os.path.join(DATA_DIR, "_duckdb_tmp")

#: Registros por lote na conversão DBF -> Parquet. É o único "botão" que
#: controla o pico de memória da ingestão. 50k mantém o pico na casa de
#: poucas dezenas de MB mesmo em bases com centenas de colunas.
DEFAULT_BATCH_SIZE = 50_000

#: Teto de memória do DuckDB. Ao atingir, ele derrama em disco (TEMP_DIR).
DEFAULT_MEMORY_LIMIT = "1GB"

#: Cache de conexões DuckDB por (memory_limit, threads).
_CONNECTIONS: dict = {}


def _ensure_dirs() -> None:
    for d in (DATA_DIR, STAGING_DIR, TEMP_DIR):
        os.makedirs(d, exist_ok=True)


# ============================================================================
# Conexão DuckDB
# ============================================================================

def get_connection(memory_limit: str = DEFAULT_MEMORY_LIMIT, threads: Optional[int] = None):
    """Retorna uma conexão DuckDB configurada para spill em disco.

    Levanta RuntimeError com instrução clara se o duckdb não estiver instalado.
    """
    try:
        import duckdb
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "O motor de memória controlada requer o pacote 'duckdb'. "
            "Instale com:  pip install duckdb"
        ) from e

    _ensure_dirs()
    key = (memory_limit, threads)
    con = _CONNECTIONS.get(key)
    if con is not None:
        return con

    con = duckdb.connect(database=":memory:")
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute(f"SET temp_directory='{TEMP_DIR}'")
    if threads:
        con.execute(f"SET threads={int(threads)}")
    _CONNECTIONS[key] = con
    return con


def close_connections() -> None:
    """Fecha as conexões em cache (útil ao final de um job/CLI)."""
    for con in _CONNECTIONS.values():
        try:
            con.close()
        except Exception:
            pass
    _CONNECTIONS.clear()


# ============================================================================
# Conversão DBF -> Parquet (streaming, memória limitada)
# ============================================================================

def _arrow_schema_for_dbf(dbf_path: str):
    """Constrói um schema Arrow explícito a partir do cabeçalho do DBF.

    Fixar o schema evita que lotes diferentes infiram tipos diferentes (o que
    faria a escrita no Parquet falhar no meio da conversão).
    Retorna None se pyarrow não estiver disponível ou o cabeçalho for ilegível.
    """
    try:
        import pyarrow as pa
        from dbfread import DBF
    except ImportError:
        return None

    try:
        table = DBF(dbf_path, encoding="latin1", load=False)
        fields = table.fields
    except Exception:
        return None

    arrow_types = []
    for f in fields:
        ftype = (getattr(f, "type", "C") or "C").upper()
        if ftype == "C":
            arrow_types.append(pa.string())
        elif ftype == "N":
            # N com casas decimais -> ponto flutuante; senão inteiro.
            if getattr(f, "decimal_count", 0):
                arrow_types.append(pa.float64())
            else:
                arrow_types.append(pa.int64())
        elif ftype in ("F", "B", "O"):
            arrow_types.append(pa.float64())
        elif ftype == "I":
            arrow_types.append(pa.int32())
        elif ftype == "D":
            arrow_types.append(pa.date32())
        elif ftype == "L":
            arrow_types.append(pa.bool_())
        else:
            # M (memo), T (datetime), G e desconhecidos -> texto (conservador)
            arrow_types.append(pa.string())

    try:
        return pa.schema([pa.field(f.name, t) for f, t in zip(fields, arrow_types)])
    except Exception:
        return None


def iter_dbf_batches(dbf_path: str, batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[list]:
    """Itera o DBF em lotes de dicionários, sem carregar tudo em memória."""
    from dbfread import DBF

    table = DBF(dbf_path, encoding="latin1", load=False)
    buf: list = []
    for record in table:
        buf.append(record)
        if len(buf) >= batch_size:
            yield buf
            buf = []
    if buf:
        yield buf


def stage_dbf_to_parquet(
    dbf_path: str,
    parquet_path: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback=None,
) -> int:
    """Converte um DBF em Parquet escrevendo em lotes. Retorna o nº de linhas.

    O pico de memória fica limitado a ~`batch_size` registros + o buffer de
    escrita do Arrow. Nada da base inteira fica residente.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    if not os.path.exists(dbf_path):
        raise FileNotFoundError(f"DBF não encontrado: {dbf_path}")

    os.makedirs(os.path.dirname(parquet_path) or ".", exist_ok=True)
    schema = _arrow_schema_for_dbf(dbf_path)

    writer = None
    total = 0
    try:
        for batch in iter_dbf_batches(dbf_path, batch_size):
            try:
                table = pa.Table.from_pylist(batch, schema=schema)
            except Exception:
                # Schema explícito falhou (dado fora do previsto): deixa o
                # Arrow inferir, mas mantém consistência a partir daí.
                schema = None
                table = pa.Table.from_pylist(batch)

            if writer is None:
                writer = pq.ParquetWriter(parquet_path, table.schema, compression="zstd")
            writer.write_table(table)
            total += len(batch)

            if progress_callback:
                progress_callback(0.0, f"Convertendo para Parquet... {total:,} registros")
    finally:
        if writer is not None:
            writer.close()

    # Base vazia: ainda assim deixar um Parquet válido (schema preservado).
    if writer is None:
        if schema is not None:
            pq.write_table(pa.Table.from_batches([], schema=schema), parquet_path)
        else:
            pd.DataFrame().to_parquet(parquet_path, index=False)

    return total


# ============================================================================
# Staging: download FTP -> DBF -> Parquet
# ============================================================================

def _staging_name(system_code: str, uf: str, period_key: str) -> str:
    return os.path.join(STAGING_DIR, f"{system_code}_{uf}_{period_key}.parquet")


def _normalize_ufs(uf) -> list:
    """Aceita 'SC' ou ['SC', 'PR'] e devolve sempre uma lista de UFs.

    Deduplica preservando a ordem: UFs repetidas fariam o mesmo Parquet ser lido
    duas vezes na consulta, DUPLICANDO as linhas.
    """
    if uf is None:
        return []
    if isinstance(uf, str):
        candidatos = [uf]
    else:
        candidatos = list(uf)
    vistos, saida = set(), []
    for u in candidatos:
        s = str(u).strip().upper()
        if s and s not in vistos:
            vistos.add(s)
            saida.append(s)
    return saida


def _is_national(system_code: str) -> bool:
    """True quando o arquivo-fonte NÃO tem recorte por UF no nome.

    Ex.: SINAN entrega `DENGBR17.dbc` — um arquivo único para o Brasil inteiro.
    Nesses casos não adianta trocar `{uf}` no nome (a substituição não faria
    nada e o arquivo seria baixado uma vez por UF, sem efeito). O filtro de UF
    precisa então ser aplicado nos DADOS (ver `build_uf_predicate`).
    """
    return "{uf}" not in SYSTEMS_CATALOG[system_code]["file_pattern"]


def _period_targets(system_code: str, ufs: list, year_start: int, year_end: int, month: str):
    """Lista ((nomes_candidatos), uf, chave_do_periodo) por arquivo-fonte desejado.

    Espelha a lógica de nomes do catálogo: anual (`DO{uf}{ano}.dbc`) e
    mensal (`RD{uf}{aa}{mm}.dbc`).

    Para sistemas ANUAIS devolvemos dois candidatos — ano com 4 e com 2 dígitos —
    na ordem de preferência (mesmo comportamento do código legado). Isso também
    cobre padrões que já usam `{yy}` (ex.: PNI) e os nacionais (ex.: SINAN).
    """
    info = SYSTEMS_CATALOG[system_code]
    pattern = info["file_pattern"]
    targets = []

    # Arquivo nacional: um único download serve para todas as UFs pedidas.
    alvos_uf = ["BR"] if _is_national(system_code) else ufs

    def _preencher(pat: str, uf: str, ano4: str, ano2: str) -> str:
        return (pat.replace("{uf}", uf)
                   .replace("{year}", ano4)
                   .replace("{yy}", ano2))

    for uf in alvos_uf:
        for year in range(year_start, year_end + 1):
            ano4, ano2 = str(year), str(year)[-2:]
            if info["type"] == "annual":
                cands = (
                    _preencher(pattern, uf, ano4, ano2),
                    _preencher(pattern, uf, ano2, ano2),
                )
                cands = tuple(dict.fromkeys(cands))  # remove duplicado exato
                targets.append((cands, uf, ano4, None))
            else:
                meses = [month] if month != "Todos" else [f"{m:02d}" for m in range(1, 13)]
                for mes in meses:
                    name = (pattern.replace("{uf}", uf)
                                   .replace("{yy}", ano2)
                                   .replace("{mm}", mes))
                    targets.append(((name,), uf, ano4, mes))
    return targets


def ensure_staged(
    system_code: str,
    uf,
    year_start: int,
    year_end: int,
    month: str = "Todos",
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback=None,
    force: bool = False,
) -> list:
    """Garante que cada arquivo-fonte esteja em Parquet. Retorna os caminhos.

    `uf` aceita uma sigla ('SC') ou uma lista (['SC', 'PR']).

    Arquivos já convertidos são reaproveitados (cache de staging). Arquivos
    baixados mas ausentes no FTP são simplesmente ignorados, como no código
    antigo.

    IMPORTANTE: o retorno contém TODOS os arquivos válidos do período — tanto os
    que já estavam em cache quanto os convertidos agora. Retornar apenas os novos
    descartaria silenciosamente os anos/meses já convertidos.
    """
    _ensure_dirs()
    info = SYSTEMS_CATALOG[system_code]
    ftp_path = info["ftp_path"]

    ufs = _normalize_ufs(uf)
    if not ufs:
        return []

    targets = _period_targets(system_code, ufs, year_start, year_end, month)

    def _path_for(target_uf: str, year_str: str, mes) -> str:
        key = f"{year_str}{mes}" if mes else year_str
        return _staging_name(system_code, target_uf, key)

    def _is_ready(path: str) -> bool:
        return os.path.exists(path) and os.path.getsize(path) > 0

    def _all_ready() -> list:
        """Todos os arquivos válidos do período (cache + recém-convertidos).

        Deduplica preservando a ordem — um caminho repetido seria lido duas vezes
        pelo DuckDB e duplicaria as linhas do resultado.
        """
        vistos, saida = set(), []
        for _c, t_uf, y, m in targets:
            p = _path_for(t_uf, y, m)
            if p not in vistos and _is_ready(p):
                vistos.add(p)
                saida.append(p)
        return saida

    # 1) Quais já estão prontos?
    pending = []
    for cands, target_uf, year_str, mes in targets:
        out = _path_for(target_uf, year_str, mes)
        if not force and _is_ready(out):
            continue
        pending.append((cands, out))

    if not pending:
        if progress_callback:
            progress_callback(1.0, "Dados já convertidos (staging em cache).")
        return _all_ready()

    ftp = _connect_ftp()
    total = len(pending)
    convertidos = 0

    try:
        ftp.cwd(ftp_path)
        # Mapa em minúsculas -> nome real. O FTP do DataSUS é case-sensitive
        # (ex.: PNI usa `.DBF` maiúsculo) e precisamos do nome EXATO no RETR.
        listing = {n.lower(): n for n in ftp.nlst()}
    except Exception as e:
        try:
            ftp.quit()
        except Exception:
            pass
        raise RuntimeError(f"Não foi possível listar {ftp_path} no FTP: {e}")

    try:
        for idx, (cands, out) in enumerate(pending, start=1):
            base = (idx - 1) / total

            # Primeiro nome de arquivo que existe no FTP (ano com 4 ou 2 dígitos).
            name = next((listing[c.lower()] for c in cands if c.lower() in listing), None)
            if name is None:
                # Ano/mês inexistente no FTP — ignora silenciosamente.
                continue

            baixado = os.path.join(STAGING_DIR, name)
            # Nem todo sistema entrega `.dbc`: o PNI já vem `.DBF` (já pronto),
            # então nesse caso não há descompactação a fazer.
            if name.lower().endswith(".dbc"):
                dbf_path = baixado[:-4] + ".dbf"
                temporarios = (baixado, dbf_path)
                precisa_descompactar = True
            else:
                dbf_path = baixado
                temporarios = (baixado,)
                precisa_descompactar = False

            try:
                if progress_callback:
                    progress_callback(base + 0.05 / total, f"Baixando {name}...")
                with open(baixado, "wb") as fh:
                    ftp.retrbinary(f"RETR {name}", fh.write)

                if precisa_descompactar:
                    if progress_callback:
                        progress_callback(base + 0.25 / total, f"Descompactando {name}...")
                    _decompress_dbc(baixado, dbf_path)

                if progress_callback:
                    progress_callback(base + 0.45 / total, f"Convertendo {name} para Parquet...")

                def _sub(pct, msg, _base=base, _idx=idx):
                    if progress_callback:
                        progress_callback(_base + (0.45 + pct * 0.5) / total, msg)

                n = stage_dbf_to_parquet(dbf_path, out, batch_size, _sub)
                if n > 0:
                    convertidos += 1
                    if progress_callback:
                        progress_callback(
                            base + 0.98 / total, f"{name}: {n:,} registros convertidos."
                        )
                else:
                    # Arquivo veio vazio: remover para não virar cache inválido.
                    if os.path.exists(out):
                        try:
                            os.remove(out)
                        except Exception:
                            pass
            except Exception as e:
                if progress_callback:
                    progress_callback(base + 1.0 / total, f"Aviso: falha em {name}: {e}")
                print(f"Aviso: falha ao processar {name}: {e}")
            finally:
                # Limpar temporários deste arquivo, sempre.
                for tmp in temporarios:
                    if os.path.exists(tmp):
                        try:
                            os.remove(tmp)
                        except Exception:
                            pass
    finally:
        try:
            ftp.quit()
        except Exception:
            pass

    if progress_callback:
        progress_callback(
            1.0, f"Staging pronto: {convertidos} arquivo(s) convertido(s) agora."
        )

    # Devolver TODOS os arquivos válidos do período (cache + recém-convertidos),
    # preservando a ordem cronológica/por UF dos targets.
    return _all_ready()


# ============================================================================
# Predicados SQL (equivalentes à filtragem antiga em pandas)
# ============================================================================

def _q(identifier: str) -> str:
    """Escapa um identificador para uso em SQL."""
    return '"' + str(identifier).replace('"', '""') + '"'


def _norm_sql(col: str) -> str:
    """Expressão SQL que reproduz `cid_catalog._normalize` sobre uma coluna."""
    return (
        f"TRIM(REPLACE(REPLACE(UPPER(CAST({col} AS VARCHAR)), '.', ''), ' ', ''))"
    )


def _columns_of(con, parquet_paths: Sequence[str]) -> list:
    """Nomes de coluna disponíveis no conjunto de Parquet."""
    rows = con.execute(
        "SELECT * FROM read_parquet(?) LIMIT 0", [list(parquet_paths)]
    ).description
    return [r[0] for r in rows]


def build_city_predicate(columns: Sequence[str], city_code):
    """Predicado de município, equivalente a `str.startswith(city_code)`.

    Aceita um código único ('420540') ou uma lista de códigos (análise
    multi-município) — nesse caso o predicado vira uma disjunção (OR).

    Usa o mesmo conjunto de campos candidatos do modo econômico antigo
    (`MUNI_FILTER_FIELDS`), pegando o primeiro presente na base.
    """
    from data_ingestion import _normalize_cities

    cidades = _normalize_cities(city_code)
    if not cidades:
        return None
    field = next((c for c in MUNI_FILTER_FIELDS if c in columns), None)
    if field is None:
        return None
    col = f"CAST({_q(field)} AS VARCHAR)"
    return "(" + " OR ".join(f"{col} LIKE '{c}%'" for c in cidades) + ")"


def build_uf_predicate(columns: Sequence[str], ufs: Sequence[str]):
    """Filtro de UF aplicado nos DADOS — para arquivos NACIONAIS.

    Usado quando o arquivo-fonte não tem recorte por UF (ex.: SINAN, cujos
    arquivos são `{AGRAVO}BR{aa}.dbc`). Sem isso, pedir "SINAN-Dengue em SC"
    baixaria o Brasil inteiro e devolveria dados de todas as UFs — um resultado
    silenciosamente errado.

    Os campos de UF não seguem convenção única: o SINAN grava o CÓDIGO IBGE
    numérico ("42") e o SIH-SP grava a SIGLA ("SC"). Por isso testamos as duas
    formas para cada UF.

    Retorna None se nenhum campo de UF conhecido estiver presente (nesse caso o
    chamador avisa que o filtro não pôde ser aplicado).
    """
    ufs = [u for u in (ufs or []) if u]
    if not ufs:
        return None
    field = next((c for c in UF_FILTER_FIELDS if c in columns), None)
    if field is None:
        return None

    col = f"UPPER(CAST({_q(field)} AS VARCHAR))"
    alternativas = []
    for u in ufs:
        sigla = str(u).strip().upper()
        alternativas.append(f"{col} LIKE '{sigla}%'")
        codigo = UF_CODIGO_IBGE.get(sigla)
        if codigo is not None:
            alternativas.append(f"{col} LIKE '{codigo:02d}%'")
    return "(" + " OR ".join(alternativas) + ")"


def build_cid_predicate(con, parquet_paths: Sequence[str], system_code: str, cid_filter):
    """Predicado CID por lista explícita de valores, reutilizando a lógica testada.

    Estratégia: extrai apenas os VALORES DISTINTOS dos campos de diagnóstico
    (poucos milhares), aplica `cid_catalog._code_matches` em Python — a mesma
    função já validada em produção — e devolve um `IN (...)`.

    Isso garante equivalência EXATA com o comportamento anterior, sem
    reimplementar faixas de capítulo em SQL (que é onde erros sutis aparecem).
    """
    from cid_catalog import _code_matches, get_cid_fields

    if not cid_filter or not cid_filter.get("active"):
        return None

    fields_meta = get_cid_fields(system_code)
    if not fields_meta:
        return None

    columns = _columns_of(con, parquet_paths)
    fields = [f for f in fields_meta if f in columns]
    if not fields:
        return None

    ranges = cid_filter.get("ranges", [])
    prefixes = tuple(cid_filter.get("prefixes", []))

    matched = set()
    for field in fields:
        norm = _norm_sql(_q(field))
        distinct = con.execute(
            f"SELECT DISTINCT {norm} AS v FROM read_parquet(?)",
            [list(parquet_paths)],
        ).fetchall()
        for (value,) in distinct:
            if value is None:
                continue
            if _code_matches(value, ranges, prefixes):
                matched.add(value)

    if not matched:
        # Filtro ativo mas nada casou -> resultado vazio (igual ao antigo).
        return "FALSE"

    # Montar a disjunção normalizada: qualquer campo CID que case.
    parts = []
    for field in fields:
        norm = _norm_sql(_q(field))
        values = ", ".join("'" + v.replace("'", "''") + "'" for v in sorted(matched))
        parts.append(f"{norm} IN ({values})")
    return "(" + " OR ".join(parts) + ")"


def build_month_predicate(columns: Sequence[str], system_code: str, month: str):
    """Filtro de mês para sistemas ANUAIS (preserva o comportamento antigo).

    O código anterior, quando `month != 'Todos'` num sistema anual, comparava
    os caracteres 3-4 da data (`str[2:4]`) com o mês. Replicamos fielmente.
    """
    if month == "Todos" or not month:
        return None
    if SYSTEMS_CATALOG.get(system_code, {}).get("type") != "annual":
        return None

    for cand in ("DTOBITO", "DTNASC", "DT_NOTIFIC", "DT_SIN_PRI"):
        if cand in columns:
            return f"SUBSTR(CAST({_q(cand)} AS VARCHAR), 3, 2) = '{month}'"
    return None


# ============================================================================
# API principal
# ============================================================================

def query_dataset(
    system_code: str,
    uf: str,
    year_start: int,
    year_end: int,
    month: str = "Todos",
    city_code="",
    columns_to_keep: Optional[Sequence[str]] = None,
    cid_filter=None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    memory_limit: str = DEFAULT_MEMORY_LIMIT,
    threads: Optional[int] = None,
    progress_callback=None,
    to_pandas: bool = True,
):
    """Garante o staging e devolve o dataset filtrado/projetado.

    A memória usada é proporcional ao RESULTADO (não à base inteira), porque
    o DuckDB faz projeção + filtro em fluxo sobre os Parquet.
    """
    resolved = _resolve_system_code(system_code)

    if year_end is None:
        year_end = year_start

    if progress_callback:
        progress_callback(0.01, f"Preparando staging de {resolved}...")

    paths = ensure_staged(
        resolved, uf, year_start, year_end, month,
        batch_size=batch_size, progress_callback=progress_callback,
    )

    if not paths:
        return pd.DataFrame() if to_pandas else None

    con = get_connection(memory_limit, threads)
    columns = _columns_of(con, paths)

    predicates = []

    city_pred = build_city_predicate(columns, city_code)
    if city_pred:
        predicates.append(city_pred)

    # Arquivo nacional: o recorte por UF não vem do nome do arquivo, então
    # precisa ser feito nos dados.
    if _is_national(resolved):
        uf_pred = build_uf_predicate(columns, _normalize_ufs(uf))
        if uf_pred:
            predicates.append(uf_pred)
            if progress_callback:
                progress_callback(
                    0.8, f"{resolved}: arquivo nacional — filtrando UF nos dados."
                )
        else:
            print(f"Aviso: {resolved} é nacional e não tem campo de UF conhecido; "
                  f"a seleção de UF NÃO será aplicada (virá o Brasil inteiro).")

    month_pred = build_month_predicate(columns, resolved, month)
    if month_pred:
        predicates.append(month_pred)

    if progress_callback:
        progress_callback(0.85, "Aplicando filtros com DuckDB...")

    cid_pred = build_cid_predicate(con, paths, resolved, cid_filter)
    if cid_pred:
        predicates.append(cid_pred)

    # Projeção: mantém a ordem pedida, ignorando colunas inexistentes.
    select = "*"
    if columns_to_keep:
        valid = [c for c in columns_to_keep if c in columns]
        if valid:
            select = ", ".join(_q(c) for c in valid)

    where = f" WHERE {' AND '.join('(' + p + ')' for p in predicates)}" if predicates else ""

    if progress_callback:
        progress_callback(0.92, "Consulta final...")

    sql = f"SELECT {select} FROM read_parquet(?){where}"
    rel = con.execute(sql, [list(paths)])

    if not to_pandas:
        return rel

    df = rel.df()
    if progress_callback:
        progress_callback(1.0, f"{len(df):,} linhas carregadas.")
    return df


def load_full_datasus(
    system_code: str,
    uf: str,
    year_start: int,
    year_end: int = None,
    month: str = "Todos",
    city_code="",
    columns_to_keep: Optional[Sequence[str]] = None,
    cid_filter=None,
    memory_efficient: bool = False,
    progress_callback=None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    memory_limit: str = DEFAULT_MEMORY_LIMIT,
    stringify_objects: bool = True,
) -> pd.DataFrame:
    """Versão memory-safe de `data_ingestion.load_full_datasus`.

    Mantém assinatura e semântica compatíveis. `memory_efficient` é aceito por
    compatibilidade, mas o motor JÁ é sempre econômico em memória.

    city_code: código IBGE (str) de um município, OU uma lista de códigos para
    filtrar por vários municípios ao mesmo tempo (análise multi-município).

    stringify_objects: converte colunas de texto para `str` (comportamento
    antigo), preservando a compatibilidade com `patient_linkage`/joins.
    """
    df = query_dataset(
        system_code=system_code,
        uf=uf,
        year_start=year_start,
        year_end=year_end,
        month=month,
        city_code=city_code,
        columns_to_keep=columns_to_keep,
        cid_filter=cid_filter,
        batch_size=batch_size,
        memory_limit=memory_limit,
        progress_callback=progress_callback,
        to_pandas=True,
    )

    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    if stringify_objects:
        obj_cols = df.select_dtypes(include=["object"]).columns
        for col in obj_cols:
            df[col] = df[col].astype(str)

    return df


# ============================================================================
# Utilidades de manutenção
# ============================================================================

def staging_stats() -> list:
    """Inventário do staging: [(arquivo, MB), ...] ordenado por tamanho."""
    _ensure_dirs()
    out = []
    for path in glob.glob(os.path.join(STAGING_DIR, "*.parquet")):
        out.append((os.path.basename(path), round(os.path.getsize(path) / 1024**2, 2)))
    return sorted(out, key=lambda x: x[1], reverse=True)


def clear_staging(only_system: Optional[str] = None) -> int:
    """Remove Parquet de staging. Retorna quantos arquivos foram apagados."""
    _ensure_dirs()
    removed = 0
    for path in glob.glob(os.path.join(STAGING_DIR, "*.parquet")):
        if only_system and not os.path.basename(path).startswith(only_system):
            continue
        try:
            os.remove(path)
            removed += 1
        except Exception:
            pass
    return removed


def clear_temp() -> None:
    """Limpa o diretório de spill do DuckDB."""
    if os.path.isdir(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def cache_signature(columns_to_keep, cid_filter) -> str:
    """Assinatura estável de uma combinação colunas+filtro (uso opcional)."""
    src = "|".join([
        ",".join(sorted(columns_to_keep)) if columns_to_keep else "ALL",
        ",".join(cid_filter.get("prefixes", [])) if cid_filter else "",
        repr(cid_filter.get("ranges", [])) if cid_filter else "",
    ])
    return hashlib.md5(src.encode()).hexdigest()[:8]
