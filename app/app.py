"""Divergências de jurisprudência — STJ, 4.ª Secção (direito do trabalho).

A app só lê `dados.json` (já processado). Não chama a IA nem o DGSI.
Correr:  streamlit run app/app.py
"""
import json
import unicodedata
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Divergências de jurisprudência", page_icon="⚖️", layout="centered", initial_sidebar_state="collapsed")

# Paleta segura para daltónicos (Okabe-Ito): oposta = laranja, igual = azul, não comparável = cinzento
COR = {"solucao_oposta": "#D55E00", "mesma_solucao": "#0072B2", "nao_comparavel": "#9A9A9A"}
NOME = {"solucao_oposta": "Solução oposta", "mesma_solucao": "Mesma solução", "nao_comparavel": "Não comparável"}
EXPLICA = {
    "solucao_oposta": "Os dois acórdãos respondem à mesma questão de formas opostas: é uma divergência.",
    "mesma_solucao": "Os dois acórdãos respondem à mesma questão da mesma forma: o tribunal manteve a orientação.",
    "nao_comparavel": "Casos ou perguntas diferentes. É um resultado normal e não conta como divergência: o sistema prefere dizê-lo a forçar uma divergência.",
}


def norm(x):
    """Minúsculas e sem acentos, para a pesquisa não depender de acentos."""
    return unicodedata.normalize("NFKD", (x or "").lower()).encode("ascii", "ignore").decode()


# Pesquisa por palavras com sinónimos jurídicos (app/sinonimos.json). Não usa IA: é uma lista escrita à mão.
GRUPOS = [[norm(m) for m in g] for g in json.loads((Path(__file__).parent / "sinonimos.json").read_text())]
GENERICAS = {"contrato", "trabalho", "trabalhador", "tribunal", "acordao", "recurso", "acao", "direito"}  # não ativam sinónimos


def radical(t):
    """Início da palavra usado para apanhar variantes (despedir/despedimento, faltou/faltas)."""
    return t[:5] if len(t) >= 7 else t[:4] if len(t) == 6 else t


def expandir(termo):
    """Devolve o termo mais os sinónimos dos grupos em que ele aparece (por palavra inteira ou início de palavra)."""
    alts = {termo}
    if termo in GENERICAS:
        return alts
    for g in GRUPOS:
        for m in g:
            if termo == m or any(termo == w or (len(termo) >= 6 and w.startswith(radical(termo))) for w in m.split()):
                alts.update(g)
                break
    return alts


def corresponde(a, termos):
    texto = norm(" ".join([a["questao"], a["solucao"] or "", a.get("normas") or "", a["processo"]]))
    return all(any(alt in texto for alt in expandir(t)) for t in termos)


STOP_PT = set("""a o os as um uma uns umas de do da dos das em no na nos nas por para com sem sobre ao aos as entre ate ou e que se
e é são ser foi era pode podem poder posso deve devem quando qual quais como quem onde quanto quantos mesmo mesma meu minha seu sua
pelo pela pelos pelas ha ter tem tinha vez muito mais menos tambem so ja nao sim""".split())


def tokens(q):
    import re
    return [t for t in re.findall(r"[a-z0-9]+", norm(q)) if t not in STOP_PT and len(t) >= 3]


@st.cache_resource
def corpus():
    """Um registo por acórdão (campos já sem acentos) e o primeiro assunto onde aparece."""
    docs, vistos = [], set()
    for t in dados["temas"]:
        for a in t["acordaos"]:
            if a["doc_id"] in vistos:
                continue
            vistos.add(a["doc_id"])
            docs.append({"a": a, "tema": t["id"],
                         "campos": [(3, norm(a["questao"])), (2, norm(a["solucao"])), (2, norm(a.get("normas") or "")), (1, norm(a.get("trecho") or ""))]})
    return docs


def pesquisar(q, limite=20):
    """Ordena os acórdãos por relevância (BM25 simplificado). Não é IA nem pesquisa por sentido: é pesquisa por palavras,
    mas por ordem de relevância e aceita frases. As palavras escritas valem mais do que os sinónimos (peso 0,5), cada palavra
    conta uma só vez (o melhor dos seus sinónimos) e os acórdãos que cobrem mais palavras da pergunta sobem."""
    import math
    termos = tokens(q)
    if not termos:
        return [], []
    docs = corpus()
    N = len(docs)
    comprimentos = [sum(len(c) for _, c in d["campos"]) for d in docs]
    media = sum(comprimentos) / max(N, 1)
    pontos = [0.0] * N
    cobertos = [0] * N
    usados = set()
    cache_df = {}

    def df_de(alt):
        if alt not in cache_df:
            cache_df[alt] = sum(any(alt in c for _, c in d["campos"]) for d in docs)
        return cache_df[alt]

    def bm25(d, i, alt):
        df = df_de(alt)
        if not df:
            return 0.0
        tf = sum(peso * c.count(alt) for peso, c in d["campos"])
        if not tf:
            return 0.0
        idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
        return idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * comprimentos[i] / media))

    for t in termos:
        proprias = {t} | ({radical(t)} if len(t) >= 6 and t not in GENERICAS else set())
        sinonimos = expandir(t) - proprias
        usados |= expandir(t) - {t}
        for i, d in enumerate(docs):
            a = max((bm25(d, i, alt) for alt in proprias), default=0.0)
            b = 0.5 * max((bm25(d, i, alt) for alt in sinonimos), default=0.0)
            m = max(a, b)
            if m > 0:
                pontos[i] += m
                cobertos[i] += 1
    for i in range(N):
        pontos[i] *= 1 + 0.6 * cobertos[i] / len(termos)  # bónus por cobrir mais palavras da pergunta
    ordem = sorted(range(N), key=lambda i: -pontos[i])
    topo_p = pontos[ordem[0]] if ordem else 0
    achados = [(pontos[i], docs[i]) for i in ordem if pontos[i] > 0 and pontos[i] >= 0.4 * topo_p][:limite]
    return achados, sorted(usados)


@st.cache_data
def carregar():
    return json.loads((Path(__file__).parent / "dados.json").read_text())


dados = carregar()
temas = {t["id"]: t for t in dados["temas"]}

# Pede ao browser para não oferecer tradução: o tradutor do Chrome/Edge parte o Streamlit
# ("NotFoundError: removeChild") e troca o texto. A página está em português europeu.
try:
    st.components.v1.html("""<script>
    const d = window.parent.document;
    d.documentElement.setAttribute("lang", "pt-PT");
    d.documentElement.setAttribute("translate", "no");
    if (!d.querySelector('meta[name="google"]')) {
      const m = d.createElement("meta"); m.name = "google"; m.content = "notranslate"; d.head.appendChild(m);
    }
    </script>""", height=0)
except Exception:  # versão do Streamlit sem este método: a app funciona na mesma
    pass

REPO = "https://github.com/martimsoares9/bythelaw-jurisprudencia"
REVISAO = {"certos": 18, "com_opiniao": 23, "total": 25}  # revisão manual de 25 veredictos (revisao/respostas.csv)
HALL, EXPLORAR, DIVERGENCIA, SOBRE = "hall", "explorar", "divergencia", "sobre"
MANTER = object()  # "não mudar o assunto escolhido"

# ---------- números globais (calculados dos dados, sem escrever à mão) ----------
FP = lambda c: c.get("revisao") == "falso_positivo"  # par marcado como falso positivo na revisão (revisao/pares_revistos.csv)
pares = {}
for t in dados["temas"]:
    for c in t["comparacoes"]:
        pares[(c["a_doc"], c["b_doc"])] = c
n_pares = len(pares)
n_opostas = sum(c["resultado"] == "solucao_oposta" and not FP(c) for c in pares.values())
n_falsos = sum(c["resultado"] == "solucao_oposta" and FP(c) for c in pares.values())
acordao_por_id = {a["doc_id"]: a for t in dados["temas"] for a in t["acordaos"]}


def ir(pagina, assunto=MANTER, pesquisa=None):
    """Callback de botões: muda de página (e, se for caso disso, de assunto ou de pesquisa)."""
    st.session_state["pagina"] = pagina
    if assunto is not MANTER:
        st.session_state["assunto"] = assunto
    if pesquisa is not None:
        st.session_state["pesquisa"] = st.session_state["ultima_pesquisa"] = pesquisa


def pesquisa_do_hall():
    ir(EXPLORAR, assunto=None, pesquisa=st.session_state.get("busca_hall", ""))


st.session_state.setdefault("pagina", HALL)
st.session_state.setdefault("assunto", None)
pagina = st.session_state["pagina"]


def glossario():
    st.markdown(
        "- **Acórdão:** decisão tomada por vários juízes.\n"
        "- **Sumário:** o resumo oficial que o próprio tribunal escreve de cada acórdão.\n"
        "- **Ficha:** o resumo que a IA faz do sumário (questão, solução e uma citação literal).\n"
        "- **Mérito:** o acórdão resolve a questão de fundo (quem tem razão), e não só se o recurso pode ser aceite.\n"
        "- **Divergência:** dois acórdãos respondem à mesma questão de formas opostas.\n"
        "- **Viragem:** o tribunal muda de opinião de forma duradoura (vários acórdãos de cada lado).\n"
        "- **AUJ:** acórdão de uniformização de jurisprudência; o STJ fixa uma orientação única para acabar com uma divergência.\n"
        "- **LAT:** Lei dos Acidentes de Trabalho. **CT:** Código do Trabalho.\n"
        "- **Responsabilidade agravada:** quando o empregador teve culpa ou não cumpriu regras de segurança, paga mais.")


def topo():
    """Linha de topo igual em todas as páginas: voltar ao átrio e glossário (um só)."""
    c1, c2, _ = st.columns([1.2, 1.4, 3])
    if pagina != HALL:
        c1.button("← Início", on_click=ir, args=(HALL,), key="voltar_hall")
    with (c2 if pagina != HALL else c1):
        with st.popover("📖 Glossário"):
            glossario()


def legenda():
    for k in NOME:
        st.markdown(f'<span style="color:{COR[k]}">●</span> **{NOME[k]}**: {EXPLICA[k]}', unsafe_allow_html=True)


def linha_do_tempo(tema, ac, comps):
    import math
    from datetime import date, timedelta
    xs = [a["data"] for a in tema["acordaos"]]
    fig = go.Figure()
    for k in NOME:  # primeiro os cinzentos, por baixo; os laranjas ficam por cima
        for c in comps:
            if c["resultado"] != k:
                continue
            d0, d1 = date.fromisoformat(ac[c["a_doc"]]["data"]), date.fromisoformat(ac[c["b_doc"]]["data"])
            n = max((d1 - d0).days, 1)
            h = 0.15 + min(n / 3650, 1) * 0.8  # arcos mais altos para pares mais afastados no tempo
            ts = [i / 20 for i in range(21)]
            falso = FP(c)  # falso positivo da revisão: tracejado fino, não conta como divergência
            fig.add_trace(go.Scatter(x=[(d0 + timedelta(days=n * t)).isoformat() for t in ts],
                                     y=[h * math.sin(math.pi * t) for t in ts], mode="lines", showlegend=False, hoverinfo="skip",
                                     line=dict(color=COR[k], width=1.5 if falso else 4 if k == "solucao_oposta" else 1.5,
                                               dash="dash" if falso else "solid" if k != "nao_comparavel" else "dot")))
    fig.add_trace(go.Scatter(x=xs, y=[0] * len(xs), mode="markers", name="Acórdão",
                             marker=dict(size=10, color="#333333", line=dict(width=1, color="white")),
                             text=[f'{a["data"]} · {a["processo"]}<br>{a["questao"][:140]}…' for a in tema["acordaos"]],
                             hovertemplate="%{text}<extra></extra>"))
    for k in NOME:  # legenda manual
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=NOME[k], line=dict(color=COR[k], width=3)))
    if any(FP(c) for c in comps):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="Falso positivo (revisão)", line=dict(color=COR["solucao_oposta"], width=1.5, dash="dash")))
    if tema.get("data_auj"):
        fig.add_vline(x=tema["data_auj"], line_dash="dash", line_color="#444444",
                      annotation_text="AUJ n.º 6/2024", annotation_position="top")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10), yaxis=dict(visible=False, range=[-0.15, 1.1]),
                      xaxis_title="Data do acórdão", legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, width="stretch")


def mostrar_divergencia(c, a, b, vir=None):
    st.markdown(f'### 🟠 {a["data"]}  ↔  {b["data"]}')
    v = (vir or {}).get(c["a_doc"])
    if FP(c):
        st.warning("**Revisão: provável falso positivo.** " + (c.get("revisao_nota") or "") +
                   " (avaliação feita à mão, a confirmar por um jurista.) Não conta como divergência.", icon="🔎")
    elif v:
        if v["estado"] == "inconsistente":
            st.warning("**O sistema contradiz-se neste caso:** o juiz de pares diz que estes dois acórdãos são opostos, mas outros pares ligam-nos "
                       "como «mesma solução». É um sinal de que a classificação automática é pouco fiável aqui e de que o caso precisa de leitura humana.", icon="⚠️")
        elif v["estado"] == "viragem":
            st.success(f'**Viragem de entendimento em {v["data"]}:** {v["antes"]} acórdãos ligados antes e {v["depois"]} depois (mínimo {v["min_lado"]}).')
        elif v["estado"] == "divergencia_coexistente":
            st.info(f'**Divergência que coexiste:** há {v["antes"]} acórdãos de uma orientação e {v["depois"]} da outra, em épocas que se sobrepõem. '
                    'As duas orientações existiram ao mesmo tempo; não é uma viragem.')
        else:
            st.info(f'**Divergência isolada, ainda não é viragem:** {v["antes"]} acórdão(s) ligado(s) do lado antigo e {v["depois"]} do lado recente; '
                    f'são precisos pelo menos {v["min_lado"]} de cada lado para falarmos de viragem.')
    st.markdown(f'**Porquê a IA diz que são opostos:** {c["justificacao"]}')
    for x, cit, lado in ((a, c["citacao_a"], "Mais antigo"), (b, c["citacao_b"], "Mais recente")):
        with st.container(border=True):
            st.markdown(f'**{lado}** · {x["data"]} · proc. {x["processo"]}')
            st.markdown(f'*Questão:* {x["questao"]}')
            st.markdown(f'*Solução:* {x["solucao"]}')
            st.markdown(f'> {cit}')
            st.markdown(f'[Ver o acórdão original no DGSI]({x["url"]})')


topo()

# ====================================================================== ÁTRIO
if pagina == HALL:
    st.title("⚖️ Onde e quando o tribunal mudou de opinião")
    st.markdown("Junta as decisões do Supremo Tribunal de Justiça que tratam do **mesmo problema** e mostra se o tribunal "
                "respondeu sempre da mesma forma ou se mudou de opinião. Direito do trabalho, 2010–2026.")
    st.text_input("🔎 Procura um tema", key="busca_hall", on_change=pesquisa_do_hall,
                  placeholder="uma palavra ou uma pergunta: despedir, férias, acidente a caminho do trabalho  (Enter)")
    st.markdown("##### Ou escolhe o que queres fazer")
    for emoji, titulo, texto, pag, chave in (
            ("🗂️", "Explorar por assunto", "Escolhe um assunto e vê os acórdãos numa linha do tempo.", EXPLORAR, "c_expl"),
            ("⚖️", "A divergência encontrada", "Duas decisões opostas, lado a lado, com as citações.", DIVERGENCIA, "c_div"),
            ("ℹ️", "Como funciona", "Como foi feito, o que vale e quais são os limites.", SOBRE, "c_sobre")):
        with st.container(border=True):
            col_t, col_b = st.columns([4, 1], vertical_alignment="center")
            col_t.markdown(f"**{emoji} {titulo}**  \n{texto}")
            col_b.button("Abrir →", on_click=ir, args=(pag, None, "") if pag == EXPLORAR else (pag,), key=chave)
    m = st.columns(4)
    m[0].metric("Acórdãos", dados["fichas"], help=f'Amostra de {dados["fichas"]} acórdãos ({dados["fichas_merito"]} de mérito) de {dados["total_trabalho"]} recolhidos.')
    m[1].metric("Assuntos", len(temas))
    m[2].metric("Pares comparados", n_pares)
    m[3].metric("Divergências", n_opostas)
    st.warning("**Classificação automática por IA, pode conter erros.** As citações são verificadas por programa "
               "(têm de existir no sumário do acórdão), mas a interpretação não foi validada por um jurista.", icon="⚠️")

# ====================================================================== EXPLORAR
elif pagina == EXPLORAR:
    tid = st.session_state.get("assunto")
    if tid in temas:
        # ------------------------------------------------------------ um assunto
        tema = temas[tid]
        ac = {a["doc_id"]: a for a in tema["acordaos"]}
        comps = sorted(tema["comparacoes"], key=lambda c: ac[c["a_doc"]]["data"])
        contagem = {k: sum(c["resultado"] == k and not FP(c) for c in comps) for k in NOME}
        st.button("← Voltar aos assuntos", on_click=ir, args=(EXPLORAR, None), key="voltar_assuntos")
        st.subheader(tema["nome"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Acórdãos", len(ac))
        c2.metric("Opostas", contagem["solucao_oposta"], help="Mesma pergunta, respostas contrárias.")
        c3.metric("Iguais", contagem["mesma_solucao"], help="Mesma pergunta, mesma resposta.")
        c4.metric("Não comparáveis", contagem["nao_comparavel"], help="Casos ou perguntas diferentes: um resultado normal, e não um erro.")
        if tema.get("data_auj"):
            st.info("O STJ fixou depois uma orientação única neste assunto: **AUJ n.º 6/2024** (primeira citação nos nossos dados: "
                    f"{tema['data_auj']}). É a nossa referência para validar.", icon="📌")
        if not comps:
            st.info("**Este assunto ainda não tem pares comparados.** A IA só pôde comparar os assuntos maiores (há um limite diário de pedidos). "
                    "Podes ler a ficha de cada acórdão em «Acórdãos».", icon="ℹ️")
        aba1, aba2, aba3 = st.tabs(["Linha do tempo", "Divergências", "Acórdãos"])
        with aba1:
            if comps:
                linha_do_tempo(tema, ac, comps)
                st.caption("Passa o rato por cima de um ponto para ver a pergunta desse acórdão.")
                with st.expander("O que significam as cores?"):
                    legenda()
            else:
                xs = [a["data"] for a in tema["acordaos"]]
                st.write(f'{len(xs)} acórdãos entre {min(xs)[:4]} e {max(xs)[:4]}, ainda sem comparações para desenhar.')
        with aba2:
            div = sorted((c for c in comps if c["resultado"] == "solucao_oposta"), key=FP)  # confirmadas primeiro
            if not div:
                st.info("Não foram encontradas soluções opostas neste assunto com os pares comparados. "
                        "Isso não prova que não existam: só se compararam alguns pares.")
            vir = {v["a_doc"]: v for v in tema.get("viragens", [])}
            for i, c in enumerate(div):
                a, b = ac[c["a_doc"]], ac[c["b_doc"]]
                v = vir.get(c["a_doc"], {})
                etiqueta = ("revisão: provável falso positivo" if FP(c)
                            else "o sistema contradiz-se neste caso" if v.get("estado") == "inconsistente"
                            else "divergência isolada" if v.get("estado") == "divergencia_isolada"
                            else "viragem" if v.get("estado") == "viragem" else "divergência")
                with st.container(border=True):
                    st.markdown(f'🟠 **{a["data"]} ↔ {b["data"]}** · {etiqueta}')
                    st.write(c["justificacao"])
                    st.button("Ver os dois acórdãos lado a lado →", on_click=ir, args=(DIVERGENCIA,), key=f"vd{tid}_{i}")
            outros = [c for c in comps if c["resultado"] != "solucao_oposta"]
            if outros:
                with st.expander(f"Outros pares comparados ({len(outros)})"):
                    for c in outros:
                        a, b = ac[c["a_doc"]], ac[c["b_doc"]]
                        st.markdown(f'**{NOME[c["resultado"]]}** · {a["data"]} → {b["data"]}')
                        st.caption(c["justificacao"])
        with aba3:
            for a in tema["acordaos"]:
                with st.expander(f'{a["data"]} · {a["questao"][:100]}'):
                    st.markdown(f'**Questão:** {a["questao"]}')
                    st.markdown(f'**Solução:** {a["solucao"]}')
                    if a.get("trecho"):
                        st.markdown(f'> {a["trecho"]}')
                    st.caption(f'Proc. {a["processo"]} · relator {a["relator"]}')
                    st.markdown(f'[Ver o acórdão original no DGSI]({a["url"]})')
    else:
        # ------------------------------------------------------------ lista de assuntos
        st.title("🗂️ Assuntos")
        # O Streamlit apaga o estado de um campo que não aparece num ecrã; guardamos a pesquisa à parte
        # para que, ao voltar de um assunto, a lista de resultados continue lá.
        st.session_state.setdefault("pesquisa", st.session_state.get("ultima_pesquisa", ""))
        pesquisa = st.text_input("🔎 Procura por palavras ou escreve uma pergunta", key="pesquisa",
                                 placeholder="por exemplo: despedir, férias, acidente a caminho do trabalho")
        st.session_state["ultima_pesquisa"] = pesquisa
        if pesquisa.strip():
            achados, ext = pesquisar(pesquisa)
            if not achados:
                st.error("Nenhum acórdão com essas palavras. Tenta outras palavras ou apaga a pesquisa.")
            else:
                st.caption(f"{len(achados)} acórdãos mais relevantes, por ordem de relevância"
                           + (" · também procurei: " + ", ".join(ext[:8]) + ("…" if len(ext) > 8 else "") if ext else ""))
                for k, (_, d) in enumerate(achados):
                    a, t = d["a"], temas[d["tema"]]
                    with st.container(border=True):
                        st.markdown(f'**{a["questao"]}**')
                        st.write(a["solucao"] if len(a["solucao"] or "") <= 260 else a["solucao"][:257] + "…")
                        st.caption(f'{a["data"]} · {t["nome"]}')
                        b1, b2 = st.columns([1, 1])
                        b1.button("Ver o assunto →", on_click=ir, args=(EXPLORAR, t["id"]), key=f"rs{k}")
                        b2.markdown(f'[Acórdão original no DGSI]({a["url"]})')
        else:
            def cartoes(ids, chave):
                for i in ids:
                    t = temas[i]
                    with st.container(border=True):
                        col_t, col_b = st.columns([4, 1], vertical_alignment="center")
                        col_t.markdown(f'**{t["nome"]}**  \n{len(t["acordaos"])} acórdãos' + (f' · {len(t["comparacoes"])} pares comparados' if t["comparacoes"] else ""))
                        col_b.button("Abrir →", on_click=ir, args=(EXPLORAR, i), key=f"{chave}{i}")

            ordem = sorted(temas, key=lambda i: (i != 100, not temas[i]["comparacoes"], -len(temas[i]["comparacoes"]), -len(temas[i]["acordaos"])))
            com = [i for i in ordem if temas[i]["comparacoes"]]
            sem = [i for i in ordem if not temas[i]["comparacoes"]]
            st.markdown("##### Já comparados")
            cartoes(com, "ac")
            with st.expander(f"Outros {len(sem)} assuntos (ainda sem comparações)"):
                cartoes(sem, "as")

# ====================================================================== DIVERGÊNCIA
elif pagina == DIVERGENCIA:
    st.title("⚖️ A divergência encontrada")
    st.markdown(f"Em {n_pares} pares de acórdãos comparados pela IA, **encontrou-se {n_opostas} divergência** e {n_falsos} caso que a revisão marcou como "
                "falso positivo. Uma divergência é um par de decisões do mesmo tribunal que respondem de forma oposta à mesma pergunta; "
                "é o tipo de caso que, mais tarde, o STJ resolve com um Acórdão de Uniformização de Jurisprudência (AUJ).")
    ja = set()
    for t in dados["temas"]:
        ac_t = {a["doc_id"]: a for a in t["acordaos"]}
        vir_t = {v["a_doc"]: v for v in t.get("viragens", [])}
        for c in sorted(t["comparacoes"], key=lambda c: (FP(c), ac_t[c["a_doc"]]["data"])):
            if c["resultado"] == "solucao_oposta" and (c["a_doc"], c["b_doc"]) not in ja:
                ja.add((c["a_doc"], c["b_doc"]))
                mostrar_divergencia(c, ac_t[c["a_doc"]], ac_t[c["b_doc"]], vir_t)
                if FP(c):
                    continue
                st.markdown("**Em simples:** num acórdão, o empregador só responde mais se se provar que teve **culpa**; no outro, "
                            "quando não cumpriu regras de segurança, **a culpa não é necessária**. O AUJ n.º 6/2024 veio fixar o que se exige "
                            "para esta responsabilidade (interpretação a confirmar por um jurista).")
    with st.expander("Porque é só uma?"):
        st.markdown("- A IA é **cautelosa**: na revisão manual, errou por dizer «não comparável» a mais.\n"
                    f"- Só {dados['fichas']} de {dados['total_trabalho']} acórdãos têm ficha.\n"
                    "- Com mais fichas e mais pares é provável que apareçam mais casos.")
    st.button("Explorar o assunto desta divergência →", on_click=ir, args=(EXPLORAR, 100), key="b_ex100")

# ====================================================================== SOBRE
else:
    st.title("ℹ️ Como funciona")
    st.markdown("Protótipo feito para o desafio da ByTheLaw: agregar acórdãos **por tema** e identificar **decisões divergentes ao longo do tempo**. "
                f"O código, a nota de decisões e a descrição do uso de IA estão no [repositório]({REPO}).")
    st.subheader("Como foi feito")
    st.markdown(
        "1. **Recolha responsável do DGSI** (pausas, cache, identificação).\n"
        "2. **Ficha por acórdão (IA):** lê o sumário e escreve a questão, as normas, a solução e uma citação literal, que um programa verifica.\n"
        "3. **Temas:** as fichas agrupam-se por semelhança de palavras.\n"
        "4. **Comparação de pares (IA):** «mesma solução», «solução oposta» ou «não comparável», com citações de cada lado.\n"
        "5. **Viragem:** distingue divergência isolada de mudança duradoura de entendimento.\n"
        f"6. **Validação:** com o AUJ n.º 6/2024 e com {REVISAO['total']} veredictos revistos à mão: em {REVISAO['com_opiniao']} houve opinião e a IA acertou em "
        f"{REVISAO['certos']} ({round(100 * REVISAO['certos'] / REVISAO['com_opiniao'])}%); os erros foram sempre «não comparável» a mais.")
    st.subheader("Limites")
    st.markdown("- Só uma parte dos acórdãos tem ficha; um só tribunal e uma só área.\n"
                "- Dois modelos de IA (um gratuito, mais fraco); revisão feita por uma só pessoa sem formação jurídica.\n"
                "- Já houve um falso positivo (assinalado na página da divergência).\n"
                "- A pesquisa é por relevância das palavras (e sinónimos), e não por sentido; a app não usa IA em tempo real.")
    st.info("Esta ferramenta ajuda a **encontrar** possíveis divergências. Não substitui a leitura nem a opinião de um jurista.", icon="⚠️")

# Rodapé comum às páginas interiores (o átrio já tem o aviso completo)
if pagina != HALL:
    st.caption("⚠️ Classificação automática por IA, pode conter erros · STJ, 4.ª Secção, 2010–2026 · fonte: dgsi.pt")
