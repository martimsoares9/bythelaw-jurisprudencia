#!/usr/bin/env python3
"""Etapa 4a — agrupar: junta os acórdãos que tratam da mesma questão (tema).

Sem LLM e sem custos: TF-IDF sobre a `questao_juridica` + as normas citadas, e
agrupamento hierárquico por distância do cosseno. (O plano inicial era usar
embeddings de sentence-transformers, mas o HuggingFace está bloqueado neste
ambiente; TF-IDF é mais simples e dá resultados legíveis com poucos acórdãos.)

Só entram acórdãos de mérito com extração válida. O nome do tema são as palavras
mais características do grupo. Tabela de saída: `temas` (doc_id, tema_id, tema_nome).

Comandos:
  python pipeline/agrupar.py               # (re)constrói `temas` e mostra os maiores
  python pipeline/agrupar.py ver <tema_id> # lista os acórdãos de um tema
"""
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

DB = Path("data/acordaos.db")
DISTANCIA = 0.85   # mais baixo = temas mais apertados e mais numerosos
MIN_TEMA = 3       # abaixo disto, o acórdão fica sem tema (não dá para ver evolução)
STOP = set("""a o os as um uma uns umas de do da dos das em no na nos nas por para com sem sobre ao aos à às que se
e ou é são ser foi pode podem quando qual quais como mesmo mesma entre pelo pela pelos pelas há ter tem
tribunal acórdão recurso revista stj trabalhador trabalhadores empregador entidade empregadora ação autor réu
saber caso casos nos termos art artigo n.º cc ct cpc cpt""".split())


def sem_acentos(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def texto_tema(q: str, normas_json: str) -> str:
    # as normas contam como palavras especiais: "ct_366" pesa mais do que uma palavra comum
    normas = " ".join("norma_" + re.sub(r"\W+", "_", sem_acentos(n.lower())).strip("_") for n in json.loads(normas_json or "[]"))
    return f"{sem_acentos((q or '').lower())} {normas} {normas}"


def agrupar(con):
    con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT e.doc_id, e.questao_juridica, e.normas FROM extracoes e
                          WHERE e.valido=1 AND e.tipo='merito'""").fetchall()
    docs = [texto_tema(r["questao_juridica"], r["normas"]) for r in rows]
    vec = TfidfVectorizer(stop_words=[sem_acentos(w) for w in STOP], ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    X = vec.fit_transform(docs)
    cl = AgglomerativeClustering(n_clusters=None, distance_threshold=DISTANCIA, metric="cosine", linkage="average")
    lab = cl.fit_predict(X.toarray())
    termos = np.array(vec.get_feature_names_out())
    con.executescript("DROP TABLE IF EXISTS temas; CREATE TABLE temas (doc_id TEXT PRIMARY KEY, tema_id INTEGER, tema_nome TEXT)")
    nomes, n_temas = {}, 0
    for t in sorted(set(lab), key=lambda t: -(lab == t).sum()):
        idx = np.where(lab == t)[0]
        if len(idx) < MIN_TEMA:
            continue
        n_temas += 1
        peso = np.asarray(X[idx].mean(axis=0)).ravel()
        top = [x.replace("norma_", "").replace("_", " ") for x in termos[np.argsort(-peso)[:4]]]
        nomes[t] = (n_temas, ", ".join(top))
    for r, t in zip(rows, lab):
        if t in nomes:
            con.execute("INSERT INTO temas VALUES (?,?,?)", (r["doc_id"], nomes[t][0], nomes[t][1]))
    con.commit()
    return len(rows), n_temas


if __name__ == "__main__":
    con = sqlite3.connect(DB)
    if len(sys.argv) > 2 and sys.argv[1] == "ver":
        con.row_factory = sqlite3.Row
        for r in con.execute("""SELECT a.data_acordao, a.processo, e.questao_juridica, e.solucao FROM temas t
                                JOIN extracoes e USING(doc_id) JOIN acordaos a USING(doc_id)
                                WHERE t.tema_id=? ORDER BY a.data_acordao""", (int(sys.argv[2]),)):
            print(f"[{r['data_acordao']}] {r['processo']}\n  Q: {r['questao_juridica']}\n  S: {r['solucao']}\n")
        sys.exit()
    n, k = agrupar(con)
    sem = n - con.execute("SELECT count(*) FROM temas").fetchone()[0]
    print(f"{n} acórdãos de mérito -> {k} temas (>= {MIN_TEMA} acórdãos); {sem} ficaram sem tema")
    for tid, nome, c, a0, a1 in con.execute("""SELECT t.tema_id, t.tema_nome, count(*), min(substr(a.data_acordao,1,4)), max(substr(a.data_acordao,1,4))
                                               FROM temas t JOIN acordaos a USING(doc_id) GROUP BY t.tema_id ORDER BY 3 DESC LIMIT 15"""):
        print(f"  tema {tid:2} | {c:3} acórdãos | {a0}-{a1} | {nome}")
