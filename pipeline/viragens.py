#!/usr/bin/env python3
"""Etapa 5b — viragens: distingue divergência isolada, coexistente ou viragem de entendimento.

Funciona com pares escolhidos de qualquer forma (consecutivos ou por semelhança):
  - ligam-se em GRUPOS os acórdãos unidos por `mesma_solucao` (se A=B e B=C, os três têm a mesma solução);
    `nao_comparavel` não liga nada;
  - cada par `solucao_oposta` (A mais antigo, B mais recente) tem o grupo de A (orientação antiga) e o de B (nova);
  - `divergencia_isolada`: um dos grupos tem menos de MIN_LADO acórdãos (pouca prova para falar de orientação);
  - `viragem`: ambos os grupos têm >= MIN_LADO acórdãos e o grupo antigo é anterior ao recente (a maior parte do grupo
    de A é anterior à maior parte do de B);
  - `inconsistente`: o par oposto está ligado por cadeias de `mesma_solucao` (o juiz contradiz-se); precisa de leitura humana.
  - `divergencia_coexistente`: ambos os grupos têm >= MIN_LADO mas as datas se sobrepõem (duas orientações em simultâneo).
MIN_LADO é pequeno (2) porque a amostra é pequena; é configurável.

  python pipeline/viragens.py [MIN_LADO]   # grava a tabela `viragens` e mostra o resultado
"""
import sqlite3
import sys
from pathlib import Path

MIN_LADO = int(sys.argv[1]) if len(sys.argv) > 1 else 2
DB = Path("data/acordaos.db")


def analisar(con, tema_id):
    con.row_factory = sqlite3.Row
    pares = con.execute("""SELECT c.a_doc,c.b_doc,c.resultado,a.data_acordao da,b.data_acordao db FROM comparacoes c
                           JOIN acordaos a ON a.doc_id=c.a_doc JOIN acordaos b ON b.doc_id=c.b_doc
                           WHERE c.tema_id=? AND c.valido=1""", (tema_id,)).fetchall()
    data, pai = {}, {}
    for p in pares:
        data[p["a_doc"]], data[p["b_doc"]] = p["da"], p["db"]

    def raiz(x):
        pai.setdefault(x, x)
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    for p in pares:
        if p["resultado"] == "mesma_solucao":
            pai[raiz(p["a_doc"])] = raiz(p["b_doc"])
    grupos = {}
    for d in data:
        grupos.setdefault(raiz(d), []).append(data[d])
    res = []
    for p in pares:
        if p["resultado"] != "solucao_oposta":
            continue
        ga, gb = sorted(grupos[raiz(p["a_doc"])]), sorted(grupos[raiz(p["b_doc"])])
        a, b = p["a_doc"], p["b_doc"]
        if raiz(a) == raiz(b):
            # O juiz disse "oposta" para A e B, mas cadeias de "mesma solução" ligam-nos: o sistema contradiz-se.
            # Não se conclui nada sobre viragem; o caso precisa de leitura humana.
            estado = "inconsistente"
        elif len(ga) < MIN_LADO or len(gb) < MIN_LADO:
            estado = "divergencia_isolada"
        elif ga[(3 * len(ga)) // 4 - (1 if len(ga) % 4 == 0 else 0)] < gb[len(gb) // 4]:
            estado = "viragem"
        else:
            estado = "divergencia_coexistente"
        res.append({"tema_id": tema_id, "data": p["db"], "a_doc": a, "b_doc": b, "antes": len(ga), "depois": len(gb), "estado": estado})
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
