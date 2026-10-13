#!/usr/bin/env python3
"""Etapa 6 — exportar: gera app/dados.json, o ficheiro só-leitura que a app usa.

A app NÃO chama a IA nem o DGSI: lê só este ficheiro. Contém, por tema, os acórdãos
com ficha da IA (questão, solução, citação) e as comparações de pares com as citações.

  python pipeline/exportar.py
"""
import json
import sqlite3
from pathlib import Path

DB, OUT = Path("data/acordaos.db"), Path("app/dados.json")
TEMA_AUJ = 100
NOME_AUJ = "Responsabilidade agravada do empregador em acidente de trabalho (art. 18.º da LAT)"
DATA_AUJ = "2024-11-27"  # primeira citação do AUJ n.º 6/2024 nos dados


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    base = """SELECT a.doc_id, a.data_acordao AS data, a.processo, a.relator, a.url, a.sumario,
                     e.questao_juridica AS questao, e.solucao, e.trecho, e.tipo, e.normas, e.confianca, e.modelo
              FROM extracoes e JOIN acordaos a USING(doc_id) WHERE e.valido=1 AND e.tipo='merito'"""
    temas = {}
    for r in con.execute(base + " AND doc_id IN (SELECT doc_id FROM tema_auj) ORDER BY a.data_acordao"):
        temas.setdefault(TEMA_AUJ, {"id": TEMA_AUJ, "nome": NOME_AUJ, "data_auj": DATA_AUJ, "acordaos": []})["acordaos"].append(dict(r))
    for t in con.execute("SELECT tema_id, tema_nome FROM temas GROUP BY tema_id ORDER BY tema_id"):
        acs = [dict(r) for r in con.execute(base + " AND doc_id IN (SELECT doc_id FROM temas WHERE tema_id=?) ORDER BY a.data_acordao", (t["tema_id"],))]
        temas[t["tema_id"]] = {"id": t["tema_id"], "nome": "Tema " + str(t["tema_id"]) + ": " + t["tema_nome"], "data_auj": None, "acordaos": acs}
    comps = {}
    for c in con.execute("SELECT * FROM comparacoes WHERE valido=1"):
        comps[(c["a_doc"], c["b_doc"])] = dict(c)
    for t in temas.values():
        ids = {a["doc_id"] for a in t["acordaos"]}
        t["comparacoes"] = [c for (a, b), c in comps.items() if a in ids and b in ids]
    out = {"gerado_de": "2026-10", "temas": [t for t in temas.values() if t["acordaos"]]}
    OUT.write_text(json.dumps(out, ensure_ascii=False))
    print({t["id"]: (len(t["acordaos"]), len(t["comparacoes"])) for t in out["temas"]}, OUT.stat().st_size // 1024, "KB")


main()
