#!/usr/bin/env python3
"""Etapa 5 — validar com um AUJ como verdade-terreno (AUJ n.º 6/2024).

O AUJ n.º 6/2024 fixou o nexo de imputação exigido para a responsabilidade agravada do
empregador por acidente de trabalho (art. 18.º da LAT). Se o sistema funciona, comparando
acórdãos sobre ESTA questão antes e depois deve detetar mudança/oposição de entendimento.

Passos (todos retomáveis e com cache; os pedidos ao LLM gratuito têm limite diário):
  selecionar   escolhe os acórdãos do assunto por regex no sumário e grava-os como tema 100
  extrair      ficha da IA para os que faltam (reutiliza pipeline/extrair.py)
  comparar     compara acórdãos consecutivos por data (reutiliza pipeline/comparar.py)
  relatorio    mostra o que o sistema encontrou, antes/depois da data do AUJ

  python pipeline/validar_auj.py selecionar|extrair [--max N]|comparar [--max N]|relatorio
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import comparar as cmp  # noqa: E402
import extrair as ext  # noqa: E402

TEMA = 100
# Sumário fala de responsabilidade agravada / art. 18.º LAT e de acidente de trabalho
RE_TEMA = re.compile(r"responsabilidade[^.]{0,60}agravad|agravamento da responsabilidade|art(?:igo|\.)\s*18\.?\s*º?[^.]{0,40}(?:LAT|Lei n\.º 100/97|Lei n\.º 98/2009)", re.I)
RE_ACID = re.compile(r"acidente|sinistrad|LAT|100/97|98/2009", re.I)
DATA_AUJ = "2024-11-27"  # primeira citação do AUJ n.º 6/2024 nos nossos dados


def selecionar(con):
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT a.doc_id,a.data_acordao,a.sumario FROM acordaos a JOIN filtrados f USING(doc_id) WHERE f.motivo_exclusao=''").fetchall()
    sel = [r for r in rows if RE_TEMA.search(r["sumario"] or "") and RE_ACID.search(r["sumario"] or "")]
    con.execute("CREATE TABLE IF NOT EXISTS tema_auj (doc_id TEXT PRIMARY KEY)")
    con.execute("DELETE FROM tema_auj")
    con.executemany("INSERT INTO tema_auj VALUES (?)", [(r["doc_id"],) for r in sel])
    con.commit()
    antes = sum(r["data_acordao"] < DATA_AUJ for r in sel)
    feitos = con.execute("SELECT count(*) FROM tema_auj t JOIN extracoes e USING(doc_id)").fetchone()[0]
    print(f"{len(sel)} acórdãos do assunto ({antes} antes de {DATA_AUJ}, {len(sel) - antes} depois); {feitos} já com ficha")


def extrair(con, maximo):
    con.row_factory = sqlite3.Row
    con.execute(ext.SCHEMA)
    rows = con.execute("SELECT a.* FROM tema_auj t JOIN acordaos a USING(doc_id) WHERE doc_id NOT IN (SELECT doc_id FROM extracoes) ORDER BY a.data_acordao").fetchall()[:maximo]
    print(f"{len(rows)} por extrair com {ext.MODELO}")
    for i, r in enumerate(rows, 1):
        res = ext.extrair_um(r)
        con.execute("INSERT OR REPLACE INTO extracoes VALUES (:doc_id,:questao_juridica,:normas,:solucao,:tipo,:trecho,:confianca,:valido,:erro,:modelo,:tokens_in,:tokens_out,:custo,:extraido_em)", res)
        con.commit()
        print(f"  {i}/{len(rows)} {r['data_acordao']} {res['tipo']} {'' if res['valido'] else '(inválido)'}")


def lista(con):
    con.row_factory = sqlite3.Row
    return con.execute("""SELECT a.doc_id,a.data_acordao,a.processo,a.sumario,e.questao_juridica,e.solucao,e.tipo,? AS tema_id
                          FROM tema_auj t JOIN extracoes e USING(doc_id) JOIN acordaos a USING(doc_id)
                          WHERE e.valido=1 AND e.tipo='merito' ORDER BY a.data_acordao""", (TEMA,)).fetchall()


def comparar(con, maximo):
    con.execute(cmp.SCHEMA)
    rs = lista(con)
    feitos = {(x[0], x[1]) for x in con.execute("SELECT a_doc,b_doc FROM comparacoes")}
    pares = [(x, y) for x, y in zip(rs, rs[1:]) if (x["doc_id"], y["doc_id"]) not in feitos][:maximo]
    print(f"{len(pares)} pares por comparar ({len(rs)} acórdãos de mérito no assunto)")
    for i, (x, y) in enumerate(pares, 1):
        res = cmp.julgar(x, y)
        con.execute("INSERT OR REPLACE INTO comparacoes VALUES (:a_doc,:b_doc,:tema_id,:resultado,:justificacao,:citacao_a,:citacao_b,:valido,:erro,:modelo,:comparado_em)", res)
        con.commit()
        print(f"  {i}/{len(pares)} {x['data_acordao']} -> {y['data_acordao']}: {res['resultado']} {'' if res['valido'] else '(inválido)'}")


def relatorio(con):
    con.row_factory = sqlite3.Row
    print("Comparações no assunto (tema 100), por data:")
    for r in con.execute("""SELECT a.data_acordao da,b.data_acordao db,c.resultado,c.valido,c.justificacao FROM comparacoes c
                            JOIN acordaos a ON a.doc_id=c.a_doc JOIN acordaos b ON b.doc_id=c.b_doc WHERE c.tema_id=? ORDER BY da""", (TEMA,)):
        marca = "<<AUJ>>" if r["da"] < DATA_AUJ <= r["db"] else ""
        print(f" {r['da']} -> {r['db']} {marca:8} {r['resultado']}{'' if r['valido'] else ' (inválido)'}\n     {r['justificacao']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["selecionar", "extrair", "comparar", "relatorio"])
    p.add_argument("--max", type=int, default=25)
    a = p.parse_args()
    con = sqlite3.connect(ext.DB)
    {"selecionar": lambda: selecionar(con), "extrair": lambda: extrair(con, a.max),
     "comparar": lambda: comparar(con, a.max), "relatorio": lambda: relatorio(con)}[a.cmd]()
