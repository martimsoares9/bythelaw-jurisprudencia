#!/usr/bin/env python3
"""Etapa 2 — filtrar: 4.ª Secção (direito do trabalho) + decisões de mérito.

Lê `acordaos` e (re)constrói a tabela `filtrados` (idempotente, é barato):
  doc_id, ano, secao4, merito, auj, motivo_exclusao   (motivo vazio = fica)

Uma decisão "de mérito" é a que resolve a questão de direito. Excluímos:
  - admissibilidade: a Formação decide só se a revista excecional é admitida;
  - sumário em falta ou demasiado curto para dizer qual foi a solução.

Comandos:
  python pipeline/filtrar.py            # reconstrói `filtrados` e mostra contagens
  python pipeline/filtrar.py exemplos   # mostra 5 acórdãos que ficaram
  python pipeline/filtrar.py relatores  # relatores da 4.ª Secção (para a etapa 2 da recolha)
"""
import re
import sqlite3
import sys
from pathlib import Path

DB = Path("data/acordaos.db")
SUMARIO_MIN = 200  # caracteres; abaixo disto o sumário não chega para extrair a solução
RE_4A = re.compile(r"^\s*4\s*\.?\s*[ªa]?\s*SEC", re.I)  # "4.ª SECÇÃO", "4ª SECÇÃO", "4.ª SECÇAO"
# Acórdão de uniformização de jurisprudência (AUJ): o STJ fixa uma orientação única para
# resolver uma divergência entre acórdãos. É a nossa "verdade-terreno" para validar.
RE_AUJ = re.compile(r"uniformiza[çc][aã]o de jurisprud|ac[óo]rd[aã]o uniformizador|jurisprud[êe]ncia uniformizada", re.I)

SCHEMA = """
DROP TABLE IF EXISTS filtrados;
CREATE TABLE filtrados (
    doc_id TEXT PRIMARY KEY, ano INTEGER, secao4 INTEGER, merito INTEGER, auj INTEGER,
    motivo_exclusao TEXT
);
"""


def classificar(r: dict) -> tuple[int, int, int, str]:
    secao4 = int(bool(RE_4A.match(r["secao"] or "")))
    sumario = r["sumario"] or ""
    # AUJ: procurar só no sumário/meio processual/início do texto (não no texto todo,
    # onde qualquer acórdão cita AUJs anteriores).
    auj = int(bool(RE_AUJ.search(f'{sumario} {r["meio_processual"] or ""} {(r["texto_integral"] or "")[:1500]}')))
    if not secao4:
        return secao4, 0, auj, "outra_secao"
    if r["admissibilidade"]:
        return secao4, 0, auj, "admissibilidade"
    if len(sumario) < SUMARIO_MIN:
        return secao4, 0, auj, "sumario_curto"
    return secao4, 1, auj, ""


def filtrar(con) -> dict:
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    rows = con.execute("SELECT doc_id,data_acordao,secao,sumario,meio_processual,texto_integral,"
                       "admissibilidade FROM acordaos").fetchall()
    for r in rows:
        s4, m, auj, motivo = classificar(dict(r))
        ano = int(r["data_acordao"][:4]) if r["data_acordao"] else None
        con.execute("INSERT INTO filtrados VALUES (?,?,?,?,?,?)", (r["doc_id"], ano, s4, m, auj, motivo))
    con.commit()
    return {k: v for k, v in con.execute(
        "SELECT motivo_exclusao, COUNT(*) FROM filtrados GROUP BY 1").fetchall()}


def main():
    con = sqlite3.connect(DB)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "filtrar"
    if cmd == "filtrar":
        res = filtrar(con)
        total = sum(res.values())
        print(f"{total} acórdãos recolhidos. Resultado do filtro:")
        for motivo, n in sorted(res.items(), key=lambda x: -x[1]):
            print(f"  {motivo or 'FICA (4.ª Secção + mérito)':32} {n}")
        print("\nFicam por ano:")
        for ano, n, auj in con.execute("SELECT ano, COUNT(*), SUM(auj) FROM filtrados "
                                       "WHERE motivo_exclusao='' GROUP BY ano ORDER BY ano"):
            print(f"  {ano}: {n:4}  (AUJ: {auj})")
    elif cmd == "exemplos":
        con.row_factory = sqlite3.Row
        # 5 acórdãos espalhados no tempo (determinístico): um em cada quinto da lista por data
        todos = con.execute("""SELECT a.processo,a.data_acordao,a.relator,a.descritores,a.sumario,a.url
                FROM acordaos a JOIN filtrados f USING(doc_id) WHERE f.motivo_exclusao=''
                ORDER BY a.data_acordao""").fetchall()
        for r in [todos[(2 * i + 1) * len(todos) // 10] for i in range(5)]:
            print(f"\n=== {r['processo']} | {r['data_acordao']} | {r['relator']}\n"
                  f"Descritores: {r['descritores']}\nSumário: {r['sumario'][:600]}…\n{r['url']}")
    elif cmd == "relatores":
        print("relator | acórdãos recolhidos | % da 4.ª Secção")
        for rel, n, p4 in con.execute("""SELECT a.relator, COUNT(*), ROUND(100.0*SUM(f.secao4)/COUNT(*))
                FROM acordaos a JOIN filtrados f USING(doc_id) GROUP BY a.relator
                HAVING COUNT(*)>=3 ORDER BY 3 DESC, 2 DESC"""):
            print(f"{rel[:40]:40} {n:4} {p4:4.0f}%")


if __name__ == "__main__":
    main()
