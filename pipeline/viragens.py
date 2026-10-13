#!/usr/bin/env python3
"""Etapa 5b — viragens: distingue divergência isolada de viragem de entendimento.

Regra: há *viragem* quando, ordenando por data, a orientação de um lado de uma
data difere da do outro lado de forma sustentada, com um mínimo de acórdãos de cada lado.

Como se mede com as comparações já feitas (sem custos de IA):
  - ligam-se acórdãos consecutivos por `mesma_solucao`; `nao_comparavel` corta a ligação;
  - cada par `solucao_oposta` (A, B) tem um bloco "antes" (o bloco de acórdãos ligados que termina
    em A) e um bloco "depois" (o que começa em B); dentro de cada bloco todos têm a mesma solução
    por transitividade;
  - é `viragem` se ambos os blocos têm >= MIN_LADO acórdãos; senão é `divergencia_isolada`.
MIN_LADO é pequeno (2) porque a amostra é pequena; é configurável.

  python pipeline/viragens.py           # grava a tabela `viragens` e mostra o resultado
"""
import sqlite3
import sys
from pathlib import Path

MIN_LADO = int(sys.argv[1]) if len(sys.argv) > 1 else 2
DB = Path("data/acordaos.db")


def blocos(con, tema_id):
    """Pares consecutivos válidos do tema, por data, e blocos ligados por mesma_solucao."""
    con.row_factory = sqlite3.Row
    pares = con.execute("""SELECT c.a_doc,c.b_doc,c.resultado,a.data_acordao da,b.data_acordao db FROM comparacoes c
                           JOIN acordaos a ON a.doc_id=c.a_doc JOIN acordaos b ON b.doc_id=c.b_doc
                           WHERE c.tema_id=? AND c.valido=1 ORDER BY da,db""", (tema_id,)).fetchall()
    return pares


def analisar(con, tema_id):
    pares = blocos(con, tema_id)
    res = []
    for i, p in enumerate(pares):
        if p["resultado"] != "solucao_oposta":
            continue
        antes = 1  # o próprio A
        j = i - 1
        while j >= 0 and pares[j]["resultado"] == "mesma_solucao" and pares[j]["b_doc"] == pares[j + 1]["a_doc"]:
            antes += 1
            j -= 1
        depois = 1  # o próprio B
        k = i + 1
        while k < len(pares) and pares[k]["resultado"] == "mesma_solucao" and pares[k]["a_doc"] == pares[k - 1]["b_doc"]:
            depois += 1
            k += 1
        res.append({"tema_id": tema_id, "data": p["db"], "a_doc": p["a_doc"], "b_doc": p["b_doc"], "antes": antes, "depois": depois,
                    "estado": "viragem" if antes >= MIN_LADO and depois >= MIN_LADO else "divergencia_isolada"})
    return res


if __name__ == "__main__":
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS viragens")
    con.execute("CREATE TABLE viragens (tema_id INT, data TEXT, a_doc TEXT, b_doc TEXT, antes INT, depois INT, estado TEXT, min_lado INT)")
    temas = [r[0] for r in con.execute("SELECT DISTINCT tema_id FROM comparacoes")]
    n = 0
    for t in temas:
        for v in analisar(con, t):
            con.execute("INSERT INTO viragens VALUES (?,?,?,?,?,?,?,?)", (v["tema_id"], v["data"], v["a_doc"], v["b_doc"], v["antes"], v["depois"], v["estado"], MIN_LADO))
            print(f'tema {t}: {v["estado"]} em {v["data"]} | acórdãos ligados antes: {v["antes"]}, depois: {v["depois"]} (mínimo {MIN_LADO})')
            n += 1
    con.commit()
    print(f"{n} divergências analisadas em {len(temas)} temas com comparações")
