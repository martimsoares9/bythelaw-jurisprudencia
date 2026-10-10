#!/usr/bin/env python3
"""Etapa 3 — extrair: o LLM lê o sumário de cada acórdão e devolve JSON estrito.

Por acórdão extrai: questao_juridica, normas, solucao, tipo, trecho, confianca.
O `trecho` tem de ser uma citação literal do sumário; se não for, a resposta é
rejeitada (repete-se uma vez com o erro como pista; depois fica `valido=0`).
Isto apanha invenções do modelo.

Fornecedor, modelo e chave vêm do ambiente / `.env` (nada no código):
  LLM_API_KEY (ou OPENROUTER_API_KEY / ANTHROPIC_API_KEY)
  LLM_BASE_URL   (omissão: https://openrouter.ai/api/v1, API compatível com OpenAI)
  LLM_MODEL_EXTRACAO (omissão: anthropic/claude-haiku-5-5)

Idempotente: cada resposta fica em cache/llm/<hash>.json (hash do modelo + prompt
+ input); re-correr não repete chamadas pagas. A tabela `extracoes` é a saída.

Comandos:
  python pipeline/extrair.py ping                 # chamada mínima para testar a chave
  python pipeline/extrair.py correr --amostra 50  # amostra aleatória (semente 42)
  python pipeline/extrair.py correr               # todos os acórdãos de trabalho
  python pipeline/extrair.py exemplos [N]         # mostra N resultados
  python pipeline/extrair.py resumo               # contagens, custo, taxa de validação
"""
import argparse
import difflib
import hashlib
import json
import os
import random
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB = Path("data/acordaos.db")
CACHE = Path("cache/llm")
BASE_URL = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
MODELO = os.environ.get("LLM_MODEL_EXTRACAO", "anthropic/claude-haiku-5-5")
CHAVE = (os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
         or os.environ.get("ANTHROPIC_API_KEY") or "")
VERSAO_PROMPT = "v2"
SUMARIO_MAX = 6000   # caracteres do sumário enviados
EXCERTO_DECISAO = 1200  # caracteres do fim da decisão
TIPOS = {"merito", "admissibilidade", "processual", "outro"}

SYSTEM = """És um assistente que analisa acórdãos do Supremo Tribunal de Justiça (secção social, direito do trabalho) para uma ferramenta de comparação de jurisprudência. Responde SEMPRE com um único objeto JSON, sem texto à volta.

Campos:
- "questao_juridica": a questão de direito decidida, em 1 frase genérica (sem nomes de partes, empresas ou pessoas), formulada como pergunta ou tema. Dois acórdãos sobre a mesma questão devem ter formulações parecidas.
- "normas": lista (máx. 5) das normas-chave aplicadas, no formato "CT art. 366.º", "CPT art. 87.º", "CC art. 483.º". Lista vazia se o sumário não as indicar.
- "solucao": a solução dada pelo tribunal, numa frase, em português europeu, sem inventar nada que não esteja no sumário ou no excerto da decisão.
- "tipo" (escolhe o PRIMEIRO que se aplicar, por esta ordem):
  1. "admissibilidade": SÓ quando o acórdão decide se o próprio recurso (revista, revista excecional) pode ser admitido ou conhecido pelo STJ (ex.: dupla conforme, valor da alçada, falta de requisitos da revista excecional). Não uses este tipo só porque a palavra "admissível", "inepta" ou "permitido" aparece no sumário.
  2. "merito": o acórdão aplica ou interpreta uma regra de direito do trabalho ou de direito civil/administrativo sobre o fundo do litígio (despedimento, retribuição, férias, procedimento disciplinar, trabalho suplementar, justa causa, caducidade, indemnização, validade de cláusulas…), mesmo que a regra seja de forma ou de prova dentro desse tema.
  3. "processual": o acórdão decide apenas regras gerais de processo, sem relação com o tema laboral concreto (valor da causa, nulidades da sentença, ónus de impugnação da matéria de facto, poderes do STJ sobre a prova, custas).
  4. "outro": nos restantes casos.
- "trecho": uma citação LITERAL e curta (uma frase ou parte dela, máx. 300 caracteres) copiada do SUMÁRIO, que sustenta a solução. Copia exatamente, caracter a caracter, sem reticências nem alterações. Se o sumário não tiver solução citável, devolve "".
- "confianca": número entre 0 e 1 (quão seguro estás de ter percebido a questão e a solução).

Se o sumário for uma pergunta ou não disser qual foi a solução, usa tipo "admissibilidade" ou "outro" e confianca baixa."""


def _hash(*partes) -> str:
    return hashlib.sha256("\x1f".join(partes).encode()).hexdigest()


def chamar(messages: list[dict], max_tokens: int = 1000) -> dict:
    """Chamada ao LLM com cache em disco, backoff e contagem de tokens/custo."""
    corpo = {"model": MODELO, "messages": messages, "max_tokens": max_tokens, "temperature": 0,
             # Sem "raciocínio": com ele o modelo gastava os tokens todos a pensar e devolvia vazio.
             "reasoning": {"enabled": False}}
    chave_cache = _hash(BASE_URL, json.dumps(corpo, sort_keys=True, ensure_ascii=False))
    f = CACHE / f"{chave_cache}.json"
    if f.exists():
        return {**json.loads(f.read_text()), "cache": True}
    for tentativa in range(5):
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", json=corpo, timeout=120,
                              headers={"Authorization": f"Bearer {CHAVE}"})
            if r.status_code in (429, 500, 502, 503, 529):
                time.sleep(2 ** tentativa + random.random())
                continue
            r.raise_for_status()
            d = r.json()
            u = d.get("usage", {})
            res = {"texto": d["choices"][0]["message"]["content"] or "",
                   "tokens_in": u.get("prompt_tokens", 0), "tokens_out": u.get("completion_tokens", 0),
                   "custo": u.get("cost", 0) or 0, "modelo": d.get("model", MODELO)}
            CACHE.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(res, ensure_ascii=False))
            return {**res, "cache": False}
        except requests.RequestException as e:
            if tentativa == 4:
                raise
            time.sleep(2 ** tentativa)
    raise RuntimeError("sem resposta do LLM")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def excerto_decisao(texto: str) -> str:
    """Fim da decisão: a partir da última fórmula de decisão, antes das notas de rodapé."""
    texto = texto or ""
    ms = list(re.finditer(r"(Pelo exposto|Nestes termos|Termos em que|Em face do exposto|III\s*[-–.]?\s*DECIS[ÃA]O|DECIS[ÃA]O\s*:)", texto))
    if not ms:
        return ""
    ini = ms[-1].start()
    return _norm(texto[ini:ini + EXCERTO_DECISAO * 2])[:EXCERTO_DECISAO]


def montar_input(r: sqlite3.Row) -> str:
    partes = [f"Data: {r['data_acordao']}", f"Processo: {r['processo']}",
              f"Descritores: {r['descritores']}", f"Meio processual / decisão: {r['meio_processual']} / {r['decisao']}",
              "SUMÁRIO:\n" + (r["sumario"] or "")[:SUMARIO_MAX]]
    ex = excerto_decisao(r["texto_integral"])
    if ex:
        partes.append("EXCERTO DO FIM DA DECISÃO:\n" + ex)
    return "\n".join(partes)


def parse_json(txt: str) -> dict:
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt.strip())
    ini, fim = txt.find("{"), txt.rfind("}")
    return json.loads(txt[ini:fim + 1])


def validar(d: dict, sumario: str) -> str:
    """Devolve '' se válido, senão o motivo da rejeição."""
    for k in ("questao_juridica", "normas", "solucao", "tipo", "trecho", "confianca"):
        if k not in d:
            return f"falta o campo {k}"
    if d["tipo"] not in TIPOS:
        return f"tipo inválido: {d['tipo']}"
    if not isinstance(d["normas"], list):
        return "normas não é lista"
    try:
        if not 0 <= float(d["confianca"]) <= 1:
            return "confianca fora de [0,1]"
    except (TypeError, ValueError):
        return "confianca não numérica"
    if d["tipo"] == "merito":
        if not str(d["solucao"]).strip() or not str(d["questao_juridica"]).strip():
            return "mérito sem questão ou solução"
        if not d["trecho"] or _norm(d["trecho"]) not in _norm(sumario):
            return "trecho não é citação literal do sumário"
    return ""


def aproveitar_citacao(d: dict, sumario: str, minimo: int = 60) -> bool:
    """Se o modelo colou uma frase inventada a uma parte verdadeira do sumário, fica só com
    o maior bloco literal (texto copiado do sumário, nunca texto do modelo). Devolve True se salvou."""
    s, t = _norm(sumario), _norm(d.get("trecho") or "")
    if not t:
        return False
    m = difflib.SequenceMatcher(None, s, t, autojunk=False).find_longest_match(0, len(s), 0, len(t))
    if m.size < minimo:
        return False
    d["trecho"] = s[m.a:m.a + m.size].strip()
    return True


def extrair_um(r: sqlite3.Row) -> dict:
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": montar_input(r)}]
    tin = tout = 0
    custo = 0.0
    erro, d, resp = "", {}, {}
    for tentativa in range(2):  # 1 repetição com o erro como pista
        resp = chamar(msgs)
        tin += resp["tokens_in"]; tout += resp["tokens_out"]; custo += resp["custo"]
        try:
            d = parse_json(resp["texto"])
            erro = validar(d, r["sumario"] or "")
        except (ValueError, KeyError) as e:
            d, erro = {}, f"JSON inválido: {e}"
        if not erro:
            break
        msgs = msgs[:2] + [{"role": "assistant", "content": resp["texto"]},
                           {"role": "user", "content": f"Rejeitado: {erro}. Corrige e devolve só o JSON. "
                            "O trecho tem de ser copiado literalmente do SUMÁRIO."}]
    if erro == "trecho não é citação literal do sumário" and aproveitar_citacao(d, r["sumario"] or ""):
        erro = validar(d, r["sumario"] or "")  # tem de passar na mesma validação
    return {"doc_id": r["doc_id"], "questao_juridica": d.get("questao_juridica"),
            "normas": json.dumps(d.get("normas", []), ensure_ascii=False), "solucao": d.get("solucao"),
            "tipo": d.get("tipo"), "trecho": d.get("trecho"), "confianca": d.get("confianca"),
            "valido": int(not erro), "erro": erro, "modelo": resp.get("modelo", MODELO),
            "tokens_in": tin, "tokens_out": tout, "custo": custo,
            "extraido_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}


SCHEMA = """CREATE TABLE IF NOT EXISTS extracoes (
    doc_id TEXT PRIMARY KEY, questao_juridica TEXT, normas TEXT, solucao TEXT, tipo TEXT,
    trecho TEXT, confianca REAL, valido INTEGER, erro TEXT, modelo TEXT,
    tokens_in INTEGER, tokens_out INTEGER, custo REAL, extraido_em TEXT)"""


def cmd_ping(_):
    if not CHAVE:
        sys.exit("Sem chave: define OPENROUTER_API_KEY (ou LLM_API_KEY / ANTHROPIC_API_KEY) no .env")
    r = requests.post(f"{BASE_URL}/chat/completions", timeout=60, headers={"Authorization": f"Bearer {CHAVE}"},
                      json={"model": MODELO, "max_tokens": 10, "messages": [{"role": "user", "content": "Responde só: ok"}]})
    print(r.status_code, r.text[:500])
    sys.exit(0 if r.ok else 1)


def cmd_correr(a):
    if not CHAVE:
        sys.exit("Sem chave de API (ver cabeçalho do ficheiro).")
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    con.execute(SCHEMA)
    rows = con.execute("SELECT a.* FROM acordaos a JOIN filtrados f USING(doc_id) "
                       "WHERE f.motivo_exclusao='' ORDER BY a.doc_id").fetchall()
    if a.amostra:
        random.Random(42).shuffle(rows)  # semente fixa: a amostra é reproduzível
        rows = rows[:a.amostra]
    feitos = {x[0] for x in con.execute("SELECT doc_id FROM extracoes")}
    rows = [r for r in rows if r["doc_id"] not in feitos]
    print(f"{len(rows)} por extrair com {MODELO} ({len(feitos)} já feitos)")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.paralelo) as ex:
        for i, res in enumerate(ex.map(extrair_um, rows), 1):
            con.execute("INSERT OR REPLACE INTO extracoes VALUES (:doc_id,:questao_juridica,:normas,:solucao,:tipo,"
                        ":trecho,:confianca,:valido,:erro,:modelo,:tokens_in,:tokens_out,:custo,:extraido_em)", res)
            con.commit()
            if i % 10 == 0 or i == len(rows):
                print(f"  {i}/{len(rows)}  ({time.time() - t0:.0f}s)")
    cmd_resumo(a)


def cmd_resumo(_):
    con = sqlite3.connect(DB)
    n, v, c, ti, to = con.execute("SELECT count(*),sum(valido),sum(custo),sum(tokens_in),sum(tokens_out) "
                                  "FROM extracoes").fetchone()
    print(f"extrações: {n} | válidas: {v} ({100 * (v or 0) / max(n, 1):.0f}%) | custo: {c or 0:.4f} USD | "
          f"tokens: {ti} in / {to} out | custo médio: {(c or 0) / max(n, 1):.5f} USD/acórdão")
    for t, k in con.execute("SELECT tipo,count(*) FROM extracoes GROUP BY tipo"):
        print(f"  tipo={t}: {k}")
    for e, k in con.execute("SELECT erro,count(*) FROM extracoes WHERE valido=0 GROUP BY erro"):
        print(f"  rejeitado ({k}): {e}")


def cmd_exemplos(a):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    for r in con.execute("SELECT e.*,a.processo,a.data_acordao FROM extracoes e JOIN acordaos a USING(doc_id) "
                         "ORDER BY a.data_acordao LIMIT ?", (a.n,)):
        print(f"\n[{r['data_acordao']}] {r['processo']}  tipo={r['tipo']} conf={r['confianca']} válido={r['valido']}")
        print(f"  Questão: {r['questao_juridica']}\n  Normas:  {r['normas']}\n  Solução: {r['solucao']}\n  Trecho:  {r['trecho']}")
        if r["erro"]:
            print(f"  ERRO: {r['erro']}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping").set_defaults(f=cmd_ping)
    c = sub.add_parser("correr"); c.set_defaults(f=cmd_correr)
    c.add_argument("--amostra", type=int, default=0); c.add_argument("--paralelo", type=int, default=4)
    e = sub.add_parser("exemplos"); e.set_defaults(f=cmd_exemplos); e.add_argument("n", type=int, nargs="?", default=50)
    sub.add_parser("resumo").set_defaults(f=cmd_resumo)
    a = p.parse_args()
    a.f(a)
