#!/usr/bin/env python3
"""Etapa 4c — atribuir_temas: põe as fichas NOVAS nos temas que já existem.

Não volta a agrupar tudo (isso mudaria os números e os nomes dos temas, os nomes legíveis e as
comparações já feitas). Em vez disso, cada ficha de mérito sem tema vai para o tema existente cujo
centro (média TF-IDF das questões + normas) está mais perto, desde que a semelhança (cosseno)
chegue a LIMIAR; senão fica sem tema, como acontece com os raros.

  python pipeline/atribuir_temas.py            # atribui e mostra quantos foram
  python pipeline/atribuir_temas.py validar    # testa o método nas fichas que já têm tema
"""
import sqlite3
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).parent))
from agrupar import STOP, sem_acentos, texto_tema  # noqa: E402

DB = Path("data/acordaos.db")
LIMIAR = 0.40


def modelo(con):
    con.row_factory = sqlite3.Row
    com = con.execute("SELECT e.doc_id, e.questao_juridica q, e.normas n, t.tema_id FROM extracoes e JOIN temas t USING(doc_id)").fetchall()
    vec = TfidfVectorizer(stop_words=[sem_acentos(w) for w in STOP], ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    X = vec.fit_transform([texto_tema(r["q"], r["n"]) for r in com]).toarray()
    ids = np.array([r["tema_id"] for r in com])
    cent = {t: X[ids == t].mean(axis=0) for t in set(ids)}
    return vec, cent, com, X, ids


def melhor(vec, cent, q, n):
    v = vec.transform([texto_tema(q, n)]).toarray()[0]
    nv = np.linalg.norm(v) or 1
    sims = {t: float(v @ c / (nv * (np.linalg.norm(c) or 1))) for t, c in cent.items()}
    t = max(sims, key=sims.get)
    return t, sims[t]


def main():
    con = sqlite3.connect(DB)
    vec, cent, com, X, ids = modelo(con)
    if sys.argv[1:] == ["validar"]:
        # deixa cada ficha de fora do seu próprio centro (aproximação: tira-a da média) e vê se volta ao mesmo tema
        ok = tot = 0
        for i, r in enumerate(com):
            m = ids == ids[i]
            if m.sum() < 2:
                continue
            c = dict(cent); c[ids[i]] = (X[m].sum(axis=0) - X[i]) / (m.sum() - 1)
            t, s = melhor(vec, c, r["q"], r["n"]); tot += 1; ok += (t == ids[i])
        print(f"validação: {ok}/{tot} fichas voltam ao seu tema ({100 * ok / tot:.0f}%)")
        return
    nomes = {r[0]: r[1] for r in con.execute("SELECT tema_id, tema_nome FROM temas GROUP BY tema_id")}
    novas = con.execute("""SELECT e.doc_id, e.questao_juridica q, e.normas n FROM extracoes e
                           WHERE e.valido=1 AND e.tipo='merito' AND e.doc_id NOT IN (SELECT doc_id FROM temas)
                           AND e.doc_id NOT IN (SELECT doc_id FROM tema_auj)""").fetchall()
    n = 0
    for r in novas:
        t, s = melhor(vec, cent, r[1], r[2])
        if s >= LIMIAR:
            con.execute("INSERT INTO temas VALUES (?,?,?)", (r[0], int(t), nomes[int(t)])); n += 1
    con.commit()
    print(f"{len(novas)} fichas de mérito sem tema -> {n} atribuídas (limiar {LIMIAR}), {len(novas) - n} ficam sem tema")


main()
