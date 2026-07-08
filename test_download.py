import urllib.request
from dbctodbf.dbc_decompress import DBCDecompress
from dbfread import DBF
import pandas as pd
from dbfread import DBF
import pandas as pd
import os

year = 2020
uf = "SP"
year2 = str(year)[-2:] # '20'

from ftplib import FTP
import os

year = 2020
uf = "SP"
year2 = str(year)[-2:] # '20'

ftp = FTP('ftp.datasus.gov.br')
ftp.login()
ftp.cwd('/dissemin/publicos/SIM/CID10/DORES/')
files = ftp.nlst()
print(f"Arquivos no diretorio: {files[:5]}...")

filename = f"DO{uf}{year}.dbc"
if filename not in files:
    filename = f"DO{uf}{year2}.dbc"

if filename in files:
    print(f"Baixando {filename}...")
    with open(filename, 'wb') as f:
        ftp.retrbinary(f"RETR {filename}", f.write)
    print("Download concluído!")
    
    print("Convertendo DBC para DBF...")
    dbc2dbf = DBCDecompress()
    dbc2dbf.decompressFile(filename, filename.replace('.dbc', '.dbf'))
    print("Conversão concluída!")
    
    print("Lendo DBF...")
    table = DBF(filename.replace('.dbc', '.dbf'), encoding='latin1')
    df = pd.DataFrame(iter(table))
    print(f"Sucesso! Lidos {len(df)} registros.")
    print(df.head())
else:
    print(f"Arquivo não encontrado no FTP para {uf} e {year}.")
ftp.quit()
