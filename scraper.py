#!/usr/bin/env python3
"""
Scraper responsável do DGSI (STJ) -> SQLite.   Duas fases:

  FASE A  indexar   percorre a vista "Por Ano" (listas de acórdãos, ~100 por página)
                    e guarda numa tabela `lista`: data, processo, relator, descritores, URL.
                    É barato (poucas centenas de páginas) e permite DECIDIR o subset com números.
  FASE B  detalhes  só para os acórdãos que escolheres (anos / descritores), descarrega a
                    página do acórdão (sumário, secção, texto integral) para a tabela `acordaos`.

Boas práticas: respeita robots.txt, pausa entre pedidos, cache local do HTML (retoma),
User-Agent identificado (EDITA a constante CONTACTO), backoff em erros temporários.

Comandos:
  python scraper.py parse acordao_html.txt                  # testa o parser, sem rede
  python scraper.py doc "https://www.dgsi.pt/jstj.nsf/<id>/<id>?OpenDocument"
  python scraper.py indexar --ate-ano 2010 --max-paginas 3  # teste pequeno
  python scraper.py indexar --ate-ano 2010                  # indexação completa
  python scraper.py stats                                   # acórdãos por ano
  python scraper.py stats --descritores "DESPEDIMENTO|TRABALH"
  python scraper.py detalhes --ano-min 2015 --ano-max 2024 --limite 20
"""
import argparse
import hashlib
import random
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------- CONFIG
CONTACTO = "Martim Soares - martimsimoes.soares@gmail.com"  
USER_AGENT = f"ProjetoAcademicoJurisprudencia/0.1 ({CONTACTO})"
BASE = "https://www.dgsi.pt"
VISTA_INICIAL = f"{BASE}/jstj.nsf/Por%20Ano?OpenView&Start=1"
PAUSA_S = 1.5
CACHE_DIR = Path("cache")
DB_PATH = Path("data/acordaos.db")
MAX_TENTATIVAS = 3

RE_DOC = re.compile(r"/jstj\.nsf/[0-9a-fA-F]{32}/([0-9a-fA-F]{32})\?OpenDocument", re.I)

CAMPOS = {
    "Processo:": "processo", "Nº Convencional:": "secao", "Relator:": "relator",
    "Descritores:": "descritores", "Data do Acordão:": "data_raw", "Votação:": "votacao",
    "Meio Processual:": "meio_processual", "Decisão:": "decisao",
    "Sumário :": "sumario", "Sumário:": "sumario",
    "Decisão Texto Integral:": "texto_integral",
}


# ----------------------------------------------------------------- PARSERS
def decodificar(conteudo: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("utf-8", errors="replace")


def _limpar(texto: str) -> str:
    texto = texto.replace("\xa0", " ")
    linhas = [re.sub(r"[ \t]+", " ", l).strip() for l in texto.splitlines()]
    return "\n".join(l for l in linhas if l)


def _data_iso(txt: str | None) -> str | None:
    # O DGSI serve a data em dois formatos conforme a localização do pedido:
    # "dd-mm-aaaa" (páginas vistas em Portugal) e "mm/dd/aaaa" (observado em pedidos
    # de servidores no estrangeiro, p.ex. 06/30/2026). O separador distingue-os.
    t = (txt or "").strip()
    fmt = "%m/%d/%Y" if "/" in t else "%d-%m-%Y"
    try:
        return datetime.strptime(t, fmt).date().isoformat()
    except ValueError:
        return None


def parse_acordao(html: str) -> dict:
    """Página de um acórdão -> dicionário de campos."""
    soup = BeautifulSoup(html, "lxml")
    out = {v: None for v in set(CAMPOS.values())}
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) != 2:
            continue
        rotulo = re.sub(r"\s+", " ", tds[0].get_text(" ", strip=True))
        chave = CAMPOS.get(rotulo)
        if chave and out[chave] is None:
            out[chave] = _limpar(tds[1].get_text("\n"))
    if out["descritores"]:
        out["descritores"] = "; ".join(out["descritores"].splitlines())
    out["data_acordao"] = _data_iso(out["data_raw"])
    txt = (out["texto_integral"] or "")[:3000]
    meio = (out["meio_processual"] or "").upper()
    out["admissibilidade"] = int(
        "EXCEPCIONAL" in meio or "EXCECIONAL" in meio or "Formação prevista no artigo 672" in txt
    )
    return out


def parse_lista(html: str, url_base: str) -> tuple[list[dict], str | None]:
    """Página da vista 'Por Ano' -> (linhas, URL da página 'Seguinte')."""
    soup = BeautifulSoup(html, "lxml")
    linhas, vistos = [], set()
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) != 4:
            continue
        a = tds[1].find("a", href=True)
        m = RE_DOC.search(a["href"]) if a else None
        if not m:
            continue
        doc_id = m.group(1).lower()
        if doc_id in vistos:
            continue
        vistos.add(doc_id)
        linhas.append({
            "doc_id": doc_id,
            "url": urljoin(url_base, a["href"]).split("&")[0],
            "data_acordao": _data_iso(tds[0].get_text(strip=True)),
            "processo": a.get_text(strip=True),
            "relator": tds[2].get_text(strip=True),
            "descritores": "; ".join(_limpar(tds[3].get_text("\n")).splitlines()),
        })
    seguinte = None
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True).lower() == "seguinte":
            seguinte = urljoin(url_base, a["href"])
            break
    return linhas, seguinte


# ----------------------------------------------------------------- BASE DE DADOS
SCHEMA = """
CREATE TABLE IF NOT EXISTS lista (
    doc_id TEXT PRIMARY KEY, url TEXT NOT NULL, data_acordao TEXT,
    processo TEXT, relator TEXT, descritores TEXT, indexado_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_lista_data ON lista(data_acordao);
CREATE TABLE IF NOT EXISTS acordaos (
    doc_id TEXT PRIMARY KEY, url TEXT NOT NULL, processo TEXT, secao TEXT, relator TEXT,
    descritores TEXT, data_acordao TEXT, votacao TEXT, meio_processual TEXT, decisao TEXT,
    sumario TEXT, texto_integral TEXT, admissibilidade INTEGER, recolhido_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_acordaos_data ON acordaos(data_acordao);
"""


def abrir_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    return con


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def gravar_lista(con, linhas: list[dict]) -> int:
    n = 0
    for l in linhas:
        cur = con.execute(
            "INSERT OR IGNORE INTO lista VALUES (?,?,?,?,?,?,?)",
            (l["doc_id"], l["url"], l["data_acordao"], l["processo"], l["relator"],
             l["descritores"], agora()))
        n += cur.rowcount
    con.commit()
    return n


def gravar_acordao(con, doc_id: str, url: str, d: dict) -> None:
    con.execute(
        "INSERT OR REPLACE INTO acordaos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (doc_id, url, d["processo"], d["secao"], d["relator"], d["descritores"],
         d["data_acordao"], d["votacao"], d["meio_processual"], d["decisao"],
         d["sumario"], d["texto_integral"], d["admissibilidade"], agora()))
    con.commit()


# ----------------------------------------------------------------- REDE
class Cliente:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": USER_AGENT})
        self.ultimo = 0.0
        self.robots = RobotFileParser()
        try:
            r = self.s.get(f"{BASE}/robots.txt", timeout=30)
            if r.status_code == 200:
                self.robots.parse(r.text.splitlines())
                print("robots.txt lido.")
            else:
                self.robots.parse([])
                print(f"robots.txt não encontrado (HTTP {r.status_code}).")
        except requests.RequestException as e:
            print(f"Aviso: não consegui ler o robots.txt ({e}).")
            self.robots.parse([])

    def obter(self, url: str) -> str | None:
        CACHE_DIR.mkdir(exist_ok=True)
        ficheiro = CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".html")
        if ficheiro.exists():
            return decodificar(ficheiro.read_bytes())
        if not self.robots.can_fetch(USER_AGENT, url):
            print(f"  [robots.txt proíbe] {url}")
            return None
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            espera = PAUSA_S + random.uniform(0, 0.7) - (time.time() - self.ultimo)
            if espera > 0:
                time.sleep(espera)
            try:
                r = self.s.get(url, timeout=60)
                self.ultimo = time.time()
            except requests.RequestException as e:
                print(f"  erro de rede ({e}); tentativa {tentativa}/{MAX_TENTATIVAS}")
                time.sleep(5 * tentativa)
                continue
            if r.status_code == 200:
                ficheiro.write_bytes(r.content)
                return decodificar(r.content)
            if r.status_code in (429, 500, 502, 503, 504):
                print(f"  HTTP {r.status_code}; a esperar... ({tentativa}/{MAX_TENTATIVAS})")
                time.sleep(15 * tentativa)
                continue
            print(f"  HTTP {r.status_code} em {url}")
            return None
        return None


# ----------------------------------------------------------------- COMANDOS
def exigir_contacto():
    if "O_TEU_NOME" in CONTACTO:
        sys.exit("Edita a constante CONTACTO no topo do ficheiro com o teu nome e email.")


def cmd_parse(a):
    html = decodificar(Path(a.ficheiro).read_bytes())
    if "OpenView" in html and "<th" in html and "PROCESSO" in html:
        linhas, seg = parse_lista(html, VISTA_INICIAL)
        print(f"Página de LISTA: {len(linhas)} acórdãos; seguinte: {seg}")
        for l in linhas[:5]:
            print(" ", l["data_acordao"], l["processo"], "|", l["relator"], "|", l["descritores"][:60])
        return
    for k, v in parse_acordao(html).items():
        t = str(v).replace("\n", " ") if v is not None else None
        print(f"{k:16}: {(t[:110] + '...') if t and len(t) > 110 else t}")


def recolher_doc(cli, con, doc_id, url) -> bool:
    if con.execute("SELECT 1 FROM acordaos WHERE doc_id=?", (doc_id,)).fetchone():
        return False
    html = cli.obter(url)
    if not html:
        return False
    d = parse_acordao(html)
    if not d["processo"] or not d["sumario"]:
        print(f"  aviso: campos em falta em {url}")
    gravar_acordao(con, doc_id, url, d)
    print(f"  gravado: {d['processo']} | {d['data_acordao']} | {d['secao']} | {d['relator']}")
    return True


def cmd_doc(a):
    exigir_contacto()
    m = RE_DOC.search(a.url)
    if not m:
        sys.exit("URL não parece ser de um acórdão (…/jstj.nsf/<id>/<id>?OpenDocument).")
    recolher_doc(Cliente(), abrir_db(), m.group(1).lower(), a.url.split("&")[0])


def cmd_indexar(a):
    exigir_contacto()
    con, cli = abrir_db(), Cliente()
    url, vistas, novas_total = a.inicio, set(), 0
    for pag in range(1, a.max_paginas + 1):
        if not url or url in vistas:
            break
        vistas.add(url)
        html = cli.obter(url)
        if not html:
            break
        linhas, seguinte = parse_lista(html, url)
        if not linhas:
            print("Página sem acórdãos; a parar.")
            break
        novas = gravar_lista(con, linhas)
        novas_total += novas
        datas = [l["data_acordao"] for l in linhas if l["data_acordao"]]
        print(f"pág {pag}: {len(linhas)} linhas ({novas} novas) | {max(datas, default='?')} -> {min(datas, default='?')}")
        if a.ate_ano and datas and int(min(datas)[:4]) < a.ate_ano:
            print(f"Chegámos a anos anteriores a {a.ate_ano}; a parar.")
            break
        url = seguinte
    total = con.execute("SELECT COUNT(*) FROM lista").fetchone()[0]
    print(f"Feito. Novas: {novas_total}. Total na tabela lista: {total}.")


def _regex_desc(txt):
    """Aceita a regex diretamente ou '@ficheiro' (regex numa só linha)."""
    if txt and txt.startswith("@"):
        txt = Path(txt[1:]).read_text(encoding="utf-8").strip()
    return re.compile(txt, re.I) if txt else None


def cmd_stats(a):
    con = abrir_db()
    rows = con.execute(
        "SELECT substr(data_acordao,1,4) ano, descritores FROM lista WHERE data_acordao IS NOT NULL").fetchall()
    if not rows:
        sys.exit("A tabela `lista` está vazia. Corre primeiro: python scraper.py indexar")
    rx = _regex_desc(a.descritores)
    por_ano, filtrados = {}, {}
    for ano, desc in rows:
        por_ano[ano] = por_ano.get(ano, 0) + 1
        if rx and rx.search(desc or ""):
            filtrados[ano] = filtrados.get(ano, 0) + 1
    print("ano   total" + ("   com_filtro" if rx else ""))
    for ano in sorted(por_ano):
        print(f"{ano}  {por_ano[ano]:6}" + (f"   {filtrados.get(ano, 0):6}" if rx else ""))
    print(f"TOTAL {sum(por_ano.values())}" + (f"   {sum(filtrados.values())}" if rx else ""))


def cmd_detalhes(a):
    exigir_contacto()
    con, cli = abrir_db(), Cliente()
    rx = _regex_desc(a.descritores)
    cand = con.execute(
        """SELECT doc_id,url,descritores,relator FROM lista
           WHERE data_acordao BETWEEN ? AND ?
             AND doc_id NOT IN (SELECT doc_id FROM acordaos)
           ORDER BY data_acordao DESC""",
        (f"{a.ano_min}-01-01", f"{a.ano_max}-12-31")).fetchall()
    if rx:
        cand = [c for c in cand if rx.search(c[2] or "")]
    if a.relatores:  # 2.ª etapa: relatores que julgam quase só na 4.ª Secção (um por linha)
        rels = set(Path(a.relatores).read_text(encoding="utf-8").splitlines())
        cand = [c for c in cand if c[3] in rels]
    if a.amostra:  # amostra aleatória reprodutível (para medir o recall do filtro)
        random.Random(42).shuffle(cand)
        a.limite = a.amostra
    print(f"{len(cand)} acórdãos por recolher no filtro; a recolher até {a.limite}.")
    novos = 0
    for doc_id, url, _, _ in cand:
        if novos >= a.limite:
            break
        if recolher_doc(cli, con, doc_id, url):
            novos += 1
    total = con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0]
    print(f"Feito. Novos: {novos}. Total em `acordaos`: {total}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("parse", help="testa o parser com HTML guardado (sem rede)")
    p.add_argument("ficheiro"); p.set_defaults(f=cmd_parse)
    p = sp.add_parser("doc", help="recolhe um acórdão pelo URL")
    p.add_argument("url"); p.set_defaults(f=cmd_doc)
    p = sp.add_parser("indexar", help="FASE A: percorre as listas e guarda-as na tabela `lista`")
    p.add_argument("--inicio", default=VISTA_INICIAL)
    p.add_argument("--ate-ano", type=int, default=2010, help="pára ao chegar a anos anteriores")
    p.add_argument("--max-paginas", type=int, default=2000); p.set_defaults(f=cmd_indexar)
    p = sp.add_parser("stats", help="contagens por ano da tabela `lista`")
    p.add_argument("--descritores", help="regex a aplicar aos descritores"); p.set_defaults(f=cmd_stats)
    p = sp.add_parser("detalhes", help="FASE B: recolhe as páginas dos acórdãos escolhidos")
    p.add_argument("--ano-min", type=int, default=2010)
    p.add_argument("--ano-max", type=int, default=2026)
    p.add_argument("--descritores", help="regex a aplicar aos descritores (pré-filtro)")
    p.add_argument("--amostra", type=int, help="recolhe N acórdãos aleatórios (semente 42)")
    p.add_argument("--relatores", help="ficheiro com relatores (um por linha): recolhe só os acórdãos destes")
    p.add_argument("--limite", type=int, default=20); p.set_defaults(f=cmd_detalhes)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
