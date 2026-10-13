#!/usr/bin/env python3
"""Etapa 4b — comparar: o LLM "juiz" compara pares de acórdãos do mesmo tema.

Dados dois acórdãos (A mais antigo, B mais recente) do mesmo tema, responde:
  mesma_solucao | solucao_oposta | nao_comparavel   (esta última é legítima e esperada:
  factos diferentes não são uma divergência)
com uma justificação curta e UMA citação literal de cada sumário (verificada por
substring; se falhar, repete-se uma vez e depois fica `valido=0`).

Para poupar pedidos (a conta gratuita só dá 50/dia) compara-se cada acórdão com o
seguinte, por data, dentro de cada tema escolhido: n-1 pares por tema.

Modelo: LLM_MODEL_JUIZ (omissão: o modelo gratuito nvidia/nemotron-3-super-120b-a12b:free;
com crédito, usar um modelo mais forte). Reutiliza `chamar` (cache + limites) de extrair.py.

Comandos:
  python pipeline/comparar.py correr --temas 100,1,2,4 [--max 45] [--modo vizinhos|consecutivos]
  python pipeline/comparar.py resumo
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extrair import DB, _norm, chamar, parse_json  # noqa: E402

MODELO_JUIZ = os.environ.get("LLM_MODEL_JUIZ", "nvidia/nemotron-3-super-120b-a12b:free")
SUMARIO_MAX = 2500
RESULTADOS = {"mesma_solucao", "solucao_oposta", "nao_comparavel"}

SYSTEM = """És um jurista que compara dois acórdãos do Supremo Tribunal de Justiça (direito do trabalho) para detetar divergências de jurisprudência. O acórdão A é o mais antigo e o B o mais recente. Responde SEMPRE com um único objeto JSON, sem texto à volta.

Regra de ouro: só há divergência se os dois acórdãos respondem à MESMA questão de direito e chegam a soluções opostas. Se os factos ou a questão são diferentes, a resposta correta é "nao_comparavel" — não forces uma divergência.

Campos:
- "resultado": "mesma_solucao" | "solucao_oposta" | "nao_comparavel"
- "justificacao": 1 a 2 frases em português europeu, simples, a explicar a decisão.
- "citacao_a": citação LITERAL curta (máx. 250 caracteres) copiada do SUMÁRIO de A que sustenta a tua conclusão. Copia caracter a caracter.
- "citacao_b": o mesmo para o SUMÁRIO de B.
Se for "nao_comparavel", as citações devem mostrar a diferença (ainda literais)."""

SCHEMA = """CREATE TABLE IF NOT EXISTS comparacoes (
    a_doc TEXT, b_doc TEXT, tema_id INTEGER, resultado TEXT, justificacao TEXT,
    citacao_a TEXT, citacao_b TEXT, valido INTEGER, erro TEXT, modelo TEXT,
    comparado_em TEXT, PRIMARY KEY (a_doc, b_doc))"""


def bloco(r, rotulo):
    return (f"ACÓRDÃO {rotulo} ({r['data_acordao']}, proc. {r['processo']})\n"
            f"Questão: {r['questao_juridica']}\nSolução (resumo): {r['solucao']}\n"
            f"SUMÁRIO {rotulo}:\n{(r['sumario'] or '')[:SUMARIO_MAX]}")


def validar(d, sa, sb):
    if d.get("resultado") not in RESULTADOS:
        return f"resultado inválido: {d.get('resultado')}"
    if not str(d.get("justificacao", "")).strip():
        return "sem justificação"
    for k, s in (("citacao_a", sa), ("citacao_b", sb)):
        c = _norm(str(d.get(k) or ""))
        if not c or c not in _norm(s or ""):
            return f"{k} não é citação literal do sumário"
    return ""


def julgar(a, b):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": bloco(a, "A") + "\n\n" + bloco(b, "B")}]
    erro, d, modelo = "", {}, MODELO_JUIZ
    for _ in range(2):
        resp = chamar(msgs, max_tokens=800, modelo=MODELO_JUIZ)
        modelo = resp.get("modelo", MODELO_JUIZ)
        try:
            d = parse_json(resp["texto"])
            erro = validar(d, a["sumario"], b["sumario"])
        except (ValueError, KeyError) as e:
            d, erro = {}, f"JSON inválido: {e}"
        if not erro:
            break
        msgs = msgs[:2] + [{"role": "assistant", "content": resp["texto"]},
                           {"role": "user", "content": f"Rejeitado: {erro}. Corrige e devolve só o JSON."}]
    return {"a_doc": a["doc_id"], "b_doc": b["doc_id"], "tema_id": a["tema_id"], "resultado": d.get("resultado"),
            "justificacao": d.get("justificacao"), "citacao_a": d.get("citacao_a"), "citacao_b": d.get("citacao_b"),
            "valido": int(not erro), "erro": erro, "modelo": modelo,
            "comparado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def pares(con, temas):
    con.row_factory = sqlite3.Row
    for t in temas:
        rows = con.execute("""SELECT a.doc_id, a.data_acordao, a.processo, a.sumario, e.questao_juridica, e.solucao, t.tema_id
                              FROM temas t JOIN extracoes e USING(doc_id) JOIN acordaos a USING(doc_id)
                              WHERE t.tema_id=? ORDER BY a.data_acordao""", (t,)).fetchall()
        for x, y in zip(rows, rows[1:]):
            yield x, y


def pares_vizinhos(con, temas, k=2, min_sim=0.30):
    """Para cada acórdão do tema, os k vizinhos mais parecidos (TF-IDF da questão + normas, só no mesmo tema).

    Medimos que a semelhança prevê se dois acórdãos são comparáveis (AUC 0,75 nos 55 pares já julgados): com
    semelhança >= 0,30 passam 8 de 11 pares comparáveis e 10 de 44 não comparáveis. O par fica ordenado por data
    (A mais antigo). Pares já julgados (em qualquer ordem) saem em `cmd_correr`.
    """
    import numpy as np
    from agrupar import STOP, sem_acentos, texto_tema
    from sklearn.feature_extraction.text import TfidfVectorizer
    con.row_factory = sqlite3.Row
    base = """SELECT a.doc_id, a.data_acordao, a.processo, a.sumario, e.questao_juridica, e.solucao, e.normas, ? AS tema_id
              FROM extracoes e JOIN acordaos a USING(doc_id) WHERE e.valido=1 AND e.tipo='merito' AND a.doc_id IN ({})"""
    glob = con.execute("SELECT e.questao_juridica q, e.normas n FROM extracoes e WHERE e.valido=1 AND e.tipo='merito'").fetchall()
    vec = TfidfVectorizer(stop_words=[sem_acentos(w) for w in STOP], ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    vec.fit([texto_tema(r["q"], r["n"]) for r in glob])
    out, vistos = [], set()
    for t in temas:
        fonte = "SELECT doc_id FROM tema_auj" if t == 100 else f"SELECT doc_id FROM temas WHERE tema_id={int(t)}"
        rows = con.execute(base.format(fonte), (t,)).fetchall()
        if len(rows) < 2:
            continue
        X = vec.transform([texto_tema(r["questao_juridica"], r["normas"]) for r in rows]).toarray()
        n = np.linalg.norm(X, axis=1, keepdims=True); n[n == 0] = 1
        S = (X / n) @ (X / n).T
        np.fill_diagonal(S, -1)
        for i, r in enumerate(rows):
            for j in np.argsort(-S[i])[:k]:
                if S[i, j] < min_sim:
                    continue
                x, y = sorted((rows[i], rows[j]), key=lambda z: (z["data_acordao"], z["doc_id"]))
                chave = (x["doc_id"], y["doc_id"])
                if chave not in vistos:
                    vistos.add(chave); out.append((float(S[i, j]), x, y))
    out.sort(key=lambda z: -z[0])  # primeiro os mais parecidos: é onde há mais probabilidade de comparabilidade
    return [(x, y) for _, x, y in out]


def cmd_correr(a):
    con = sqlite3.connect(DB)
    con.execute(SCHEMA)
    feitos = {(x[0], x[1]) for x in con.execute("SELECT a_doc,b_doc FROM comparacoes")}
    lista = [int(t) for t in a.temas.split(",")]
    if a.modo == "vizinhos":
        candidatos = pares_vizinhos(con, lista, a.k, a.min_sim)
    else:
        candidatos = list(pares(con, lista))
    feitos |= {(b, a_) for a_, b in feitos}  # um par já julgado conta nas duas ordens
    todos = [(x, y) for x, y in candidatos if (x["doc_id"], y["doc_id"]) not in feitos]
    todos = todos[:a.max]
    print(f"{len(todos)} pares por comparar com {MODELO_JUIZ}")
    for i, (x, y) in enumerate(todos, 1):
        res = julgar(x, y)
        con.execute("INSERT OR REPLACE INTO comparacoes VALUES (:a_doc,:b_doc,:tema_id,:resultado,:justificacao,"
                    ":citacao_a,:citacao_b,:valido,:erro,:modelo,:comparado_em)", res)
        con.commit()
        print(f"  {i}/{len(todos)} {x['data_acordao']} -> {y['data_acordao']}: {res['resultado']} {'' if res['valido'] else '(inválido)'}")
    cmd_resumo(a)


def cmd_resumo(_):
    con = sqlite3.connect(DB)
    con.execute(SCHEMA)
    n, v = con.execute("SELECT count(*),coalesce(sum(valido),0) FROM comparacoes").fetchone()
    print(f"comparações: {n} | válidas: {v}")
    for t, r, k in con.execute("SELECT tema_id,resultado,count(*) FROM comparacoes WHERE valido=1 GROUP BY 1,2 ORDER BY 1"):
        print(f"  tema {t}: {r} = {k}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("correr"); c.set_defaults(f=cmd_correr)
    c.add_argument("--temas", required=True); c.add_argument("--max", type=int, default=45)
    c.add_argument("--modo", choices=["vizinhos", "consecutivos"], default="vizinhos",
                   help="vizinhos: pares mais parecidos (omissão); consecutivos: cada acórdão com o seguinte por data")
    c.add_argument("--k", type=int, default=2, help="vizinhos por acórdão (modo vizinhos)")
    c.add_argument("--min-sim", type=float, default=0.30, help="semelhança mínima (modo vizinhos)")
    sub.add_parser("resumo").set_defaults(f=cmd_resumo)
    a = p.parse_args()
    a.f(a)
