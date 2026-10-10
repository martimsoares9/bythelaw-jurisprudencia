#!/usr/bin/env python3
"""Guarda/restaura só as tabelas produzidas pela IA (extracoes, temas, comparacoes) em
dados/ia_tabelas.json.gz (~centenas de KB), para não perder o trabalho se o contentor
for reclamado. NÃO substitui a cópia completa da base (essa só se guarda no fim).

  python pipeline/guardar_ia.py guardar   # base -> dados/ia_tabelas.json.gz
  python pipeline/guardar_ia.py restaurar # dados/ia_tabelas.json.gz -> base (descomprimir antes a base)
"""
import gzip, json, sqlite3, sys
from pathlib import Path

DB, F = Path("data/acordaos.db"), Path("dados/ia_tabelas.json.gz")
TABELAS = ["extracoes", "temas", "comparacoes"]

con = sqlite3.connect(DB)
if sys.argv[1:] == ["guardar"]:
    out = {}
    for t in TABELAS:
        if con.execute("SELECT 1 FROM sqlite_master WHERE name=?", (t,)).fetchone():
            cur = con.execute(f"SELECT * FROM {t}")
            out[t] = {"colunas": [d[0] for d in cur.description], "linhas": cur.fetchall()}
    F.write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False).encode()))
    print({t: len(v["linhas"]) for t, v in out.items()}, F.stat().st_size // 1024, "KB")
elif sys.argv[1:] == ["restaurar"]:
    for t, v in json.loads(gzip.decompress(F.read_bytes())).items():
        cols = v["colunas"]
        con.execute(f"DROP TABLE IF EXISTS {t}")
        con.execute(f"CREATE TABLE {t} ({','.join(cols)}{', PRIMARY KEY (a_doc,b_doc)' if t=='comparacoes' else ''})")
        con.executemany(f"INSERT INTO {t} VALUES ({','.join('?'*len(cols))})", v["linhas"])
        print(t, len(v["linhas"]))
    con.commit()
else:
    sys.exit(__doc__)
