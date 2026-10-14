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
# Nomes legíveis escritos à mão (os automáticos são listas de palavras). Só valem se as palavras-chave
# do tema não mudaram; se se voltar a correr `agrupar.py` os números dos temas podem mudar.
NOMES = json.loads(Path("pipeline/nomes_temas.json").read_text())
TEMA_AUJ = 100
NOME_AUJ = "Responsabilidade agravada do empregador em acidente de trabalho (art. 18.º da LAT)"
DATA_AUJ = "2024-11-27"  # primeira citação do AUJ n.º 6/2024 nos dados


def revisoes():
    """Pares já revistos à mão (revisao/pares_revistos.csv): marcam falsos positivos para a app os mostrar com aviso."""
    f = Path("revisao/pares_revistos.csv")
    if not f.exists():
        return {}
    import csv
    return {(r["a_doc"], r["b_doc"]): r for r in csv.DictReader(f.open(encoding="utf-8"))}


def main():
    rev = revisoes()
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
        temas[t["tema_id"]] = {"id": t["tema_id"], "nome": (NOMES.get(str(t["tema_id"]), {}).get("nome") if NOMES.get(str(t["tema_id"]), {}).get("termos") == t["tema_nome"] else None) or "Tema " + str(t["tema_id"]) + ": " + t["tema_nome"], "data_auj": None, "acordaos": acs}
    comps = {}
    for c in con.execute("SELECT * FROM comparacoes WHERE valido=1"):
        d = dict(c)
        r = rev.get((c["a_doc"], c["b_doc"]))
        d["revisao"], d["revisao_nota"] = (r["veredicto_revisao"], r["nota"]) if r else (None, None)
        comps[(c["a_doc"], c["b_doc"])] = d
    for t in temas.values():
        ids = {a["doc_id"] for a in t["acordaos"]}
        t["comparacoes"] = [c for (a, b), c in comps.items() if a in ids and b in ids]
        t["viragens"] = [dict(v) for v in con.execute("SELECT * FROM viragens WHERE a_doc IN (%s)" % ",".join("?" * len(ids)), list(ids))] if ids else []
    tot = con.execute("SELECT count(*), sum(tipo='merito') FROM extracoes WHERE valido=1").fetchone()
    out = {"gerado_de": "2026-10", "fichas": tot[0], "fichas_merito": tot[1], "total_trabalho": 1820, "temas": [t for t in temas.values() if t["acordaos"]]}
    OUT.write_text(json.dumps(out, ensure_ascii=False))
    print({t["id"]: (len(t["acordaos"]), len(t["comparacoes"])) for t in out["temas"]}, OUT.stat().st_size // 1024, "KB")


main()
