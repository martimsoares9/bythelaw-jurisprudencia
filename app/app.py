"""Divergências de jurisprudência — STJ, 4.ª Secção (direito do trabalho).

A app só lê `dados.json` (já processado). Não chama a IA nem o DGSI.
Correr:  streamlit run app/app.py
"""
import json
import unicodedata
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Divergências de jurisprudência", page_icon="⚖️", layout="wide")

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


def expandir(termo):
    """Devolve o termo mais os sinónimos dos grupos em que ele aparece (por palavra inteira ou início de palavra)."""
    alts = {termo}
    if termo in GENERICAS:
        return alts
    for g in GRUPOS:
        for m in g:
            if termo == m or any(termo == w or (len(termo) >= 5 and w.startswith(termo[:5])) for w in m.split()):
                alts.update(g)
                break
    return alts


def corresponde(a, termos):
    texto = norm(" ".join([a["questao"], a["solucao"] or "", a.get("normas") or "", a["processo"]]))
    return all(any(alt in texto for alt in expandir(t)) for t in termos)


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
INICIO, EXPLORAR, DIVERGENCIA, SOBRE = "🏠 Início", "🔎 Explorar assuntos", "⚖️ Divergência encontrada", "ℹ️ Sobre o projeto"
PAGINAS = [INICIO, EXPLORAR, DIVERGENCIA, SOBRE]

# ---------- números globais (calculados dos dados, sem escrever à mão) ----------
pares = {}
for t in dados["temas"]:
    for c in t["comparacoes"]:
        pares[(c["a_doc"], c["b_doc"])] = c
n_pares = len(pares)
FP = lambda c: c.get("revisao") == "falso_positivo"  # par marcado como falso positivo na revisão (revisao/pares_revistos.csv)
n_opostas = sum(c["resultado"] == "solucao_oposta" and not FP(c) for c in pares.values())
n_falsos = sum(c["resultado"] == "solucao_oposta" and FP(c) for c in pares.values())
acordao_por_id = {a["doc_id"]: a for t in dados["temas"] for a in t["acordaos"]}


def ir(pagina, assunto=None, pesquisa=None):
    """Callback de botões: muda de página (e, se for caso disso, de assunto ou pesquisa)."""
    st.session_state["pagina"] = pagina
    if assunto is not None:
        st.session_state["assunto_pedido"] = assunto
    if pesquisa is not None:
        st.session_state["pesquisa"] = pesquisa


def busca_inicio():
    ir(EXPLORAR, pesquisa=st.session_state.get("busca_inicio", ""))


if "pagina" not in st.session_state:
    st.session_state["pagina"] = INICIO
st.sidebar.title("⚖️ Divergências STJ")
st.sidebar.radio("Navegar", PAGINAS, key="pagina")
st.sidebar.caption("STJ · 4.ª Secção · 2010–2026 · fonte: dgsi.pt")
st.sidebar.warning("Classificação automática por IA, pode conter erros.", icon="⚠️")
pagina = st.session_state["pagina"]

AVISO = ("**Classificação automática por IA, pode conter erros.** As citações são verificadas por programa (têm de existir "
         "no sumário do acórdão), mas a interpretação não foi validada por um jurista.")


def glossario():
    with st.expander("📖 Glossário: o que quer dizer cada palavra"):
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
            fig.add_trace(go.Scatter(x=[(d0 + timedelta(days=n * t)).isoformat() for t in ts],
                                     y=[h * math.sin(math.pi * t) for t in ts], mode="lines", showlegend=False, hoverinfo="skip",
                                     line=dict(color=COR[k], width=4 if k == "solucao_oposta" else 1.5,
                                               dash="solid" if k != "nao_comparavel" else "dot")))
    fig.add_trace(go.Scatter(x=xs, y=[0] * len(xs), mode="markers", name="Acórdão",
                             marker=dict(size=10, color="#333333", line=dict(width=1, color="white")),
                             text=[f'{a["data"]} · {a["processo"]}<br>{a["questao"][:140]}…' for a in tema["acordaos"]],
                             hovertemplate="%{text}<extra></extra>"))
    for k in NOME:  # legenda manual
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=NOME[k], line=dict(color=COR[k], width=3)))
    if tema.get("data_auj"):
        fig.add_vline(x=tema["data_auj"], line_dash="dash", line_color="#444444",
                      annotation_text="AUJ n.º 6/2024", annotation_position="top")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), yaxis=dict(visible=False, range=[-0.15, 1.1]),
                      xaxis_title="Data do acórdão", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")


def mostrar_divergencia(c, a, b, vir=None, tema=None):
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
                    f'são precisos pelo menos {v["min_lado"]} de cada lado para falarmos de viragem. Com mais acórdãos na amostra poderia confirmar-se.')
    st.markdown(f'**Porquê a IA diz que são opostos:** {c["justificacao"]}')
    ca, cb = st.columns(2)
    for col, x, cit, lado in ((ca, a, c["citacao_a"], "Mais antigo"), (cb, b, c["citacao_b"], "Mais recente")):
        with col:
            with st.container(border=True):
                st.markdown(f'**{lado}** · {x["data"]} · proc. {x["processo"]}')
                st.markdown(f'*Questão:* {x["questao"]}')
                st.markdown(f'*Solução:* {x["solucao"]}')
                st.markdown(f'> {cit}')
                st.markdown(f'[Ver o acórdão original no DGSI]({x["url"]})')


# ====================================================================== INÍCIO
if pagina == INICIO:
    st.title("⚖️ Onde e quando o tribunal mudou de opinião")
    st.markdown("Os tribunais publicam milhares de decisões. Esta ferramenta **junta as que tratam do mesmo problema** e "
                "mostra, ao longo dos anos, **se o tribunal respondeu sempre da mesma forma ou se mudou de opinião**. "
                "Usa acórdãos do Supremo Tribunal de Justiça sobre direito do trabalho (2010–2026).")
    st.warning(AVISO, icon="⚠️")

    st.subheader("Como usar, em 3 passos")
    p1, p2, p3 = st.columns(3)
    for col, n, tit, txt in ((p1, "1", "Escolhe um assunto", "Por exemplo, despedimento por justa causa, férias ou acidentes de trabalho. Podes também pesquisar por palavras."),
                             (p2, "2", "Vê a linha do tempo", "Cada ponto é um acórdão e os arcos ligam acórdãos que a IA comparou (a legenda das cores está na barra lateral, em «Explorar assuntos»)."),
                             (p3, "3", "Abre a divergência", "Lê os dois acórdãos lado a lado, com a citação que justifica e o link para o original no DGSI.")):
        with col:
            with st.container(border=True):
                st.markdown(f"**{n}. {tit}**")
                st.write(txt)

    st.subheader("Em números")
    m = st.columns(5)
    m[0].metric("Acórdãos analisados", dados["fichas"],
                help=f'Amostra de {dados["fichas"]} acórdãos ({dados["fichas_merito"]} de mérito) de um conjunto de {dados["total_trabalho"]} recolhidos.')
    m[1].metric("Assuntos", len(temas))
    m[2].metric("Pares comparados", n_pares)
    m[3].metric("Divergências", n_opostas)
    m[4].metric("Acerto na revisão", f'{round(100 * REVISAO["certos"] / REVISAO["com_opiniao"])}%',
                help=f'{REVISAO["certos"]} certos em {REVISAO["com_opiniao"]} veredictos com opinião, de {REVISAO["total"]} revistos à mão.')

    st.subheader("Caso em destaque")
    opostas = sorted((c for c in pares.values() if c["resultado"] == "solucao_oposta" and not FP(c)), key=lambda c: acordao_por_id[c["a_doc"]]["data"])
    if opostas:
        c = opostas[0]
        a, b = acordao_por_id[c["a_doc"]], acordao_por_id[c["b_doc"]]
        with st.container(border=True):
            st.markdown(f'**Duas decisões do mesmo tribunal, em {a["data"][:4]}, sobre a mesma pergunta:** '
                        f'*{a["questao"]}*')
            st.markdown(f'As duas decisões ({a["data"]} e {b["data"]}) deram respostas opostas. Podes lê-las lado a lado, com as citações.')
            st.caption("Anos depois, o STJ fixou uma orientação única sobre esta matéria (Acórdão de Uniformização n.º 6/2024). "
                       "É uma questão muito próxima da que o sistema encontrou em aberto em 2011 (a relação exata deve ser confirmada por um jurista).")
            st.button("Ver o caso completo →", on_click=ir, args=(DIVERGENCIA,), key="b_caso")

    st.subheader("Começa por aqui")
    b1, b2 = st.columns([2, 3])
    with b1:
        st.text_input("🔎 Pesquisar um tema por palavras", key="busca_inicio", on_change=busca_inicio,
                      placeholder="ex.: despedir, férias, assédio (Enter)")
    with b2:
        st.markdown("**Assuntos já comparados:**")
        com_comp = sorted((t for t in temas.values() if t["comparacoes"]), key=lambda t: (t["id"] != 100, -len(t["comparacoes"])))
        cols = st.columns(2)
        for i, t in enumerate(com_comp[:4]):
            cols[i % 2].button(f'{t["nome"][:42]}…' if len(t["nome"]) > 42 else t["nome"], key=f'at{t["id"]}',
                               on_click=ir, args=(EXPLORAR, t["id"]))
    st.button("Explorar todos os assuntos →", on_click=ir, args=(EXPLORAR,), key="b_expl")

# ====================================================================== EXPLORAR
elif pagina == EXPLORAR:
    st.title("🔎 Explorar assuntos")
    pesquisa = st.sidebar.text_input("🔎 Pesquisar por palavra", key="pesquisa", placeholder="ex.: férias, justa causa, art. 18.º")
    termos = [norm(t) for t in pesquisa.split() if t.strip()]
    acertos = {i: [a for a in t["acordaos"] if corresponde(a, termos)] for i, t in temas.items()} if termos else {i: t["acordaos"] for i, t in temas.items()}
    ordem = sorted((i for i in temas if acertos[i]), key=lambda i: (i != 100, not temas[i]["comparacoes"], -len(temas[i]["comparacoes"]), -len(temas[i]["acordaos"])))
    if not ordem:
        st.error("Nenhum acórdão com essas palavras. Tenta outra palavra ou apaga a pesquisa.")
        st.stop()
    if termos:
        ext = sorted({a for t in termos for a in expandir(t)} - set(termos))
        if ext:
            st.sidebar.caption("Também procurei: " + ", ".join(ext[:12]) + ("…" if len(ext) > 12 else ""))
        st.sidebar.success(f"{sum(len(acertos[i]) for i in ordem)} acórdãos em {len(ordem)} assuntos")

    def rotulo(i):
        t = temas[i]
        marca = "✔ comparado" if t["comparacoes"] else "sem comparações ainda"
        return f'{t["nome"]} · {len(acertos[i])} acórdãos · {marca}'

    pedido = st.session_state.get("assunto_pedido")
    idx = ordem.index(pedido) if pedido in ordem else 0
    tid = st.sidebar.selectbox("Escolhe um assunto", ordem, index=idx, format_func=rotulo)
    st.session_state["assunto_pedido"] = tid
    st.sidebar.markdown("**Como ler as cores**")
    with st.sidebar:
        legenda()

    tema = temas[tid]
    ac = {a["doc_id"]: a for a in tema["acordaos"]}
    comps = sorted(tema["comparacoes"], key=lambda c: ac[c["a_doc"]]["data"])
    contagem = {k: sum(c["resultado"] == k and not FP(c) for c in comps) for k in NOME}

    st.subheader(tema["nome"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Acórdãos", len(ac))
    c2.metric("Soluções opostas", contagem["solucao_oposta"], help="Mesma pergunta, respostas contrárias.")
    c3.metric("Mesma solução", contagem["mesma_solucao"], help="Mesma pergunta, mesma resposta.")
    c4.metric("Não comparáveis", contagem["nao_comparavel"], help="Ver a legenda na barra lateral.")
    if not comps:
        st.info("**Este assunto ainda não tem pares comparados.** A IA só pôde comparar os assuntos maiores (há um limite diário de pedidos). "
                "Podes ler a ficha de cada acórdão no separador «Todos os acórdãos».", icon="ℹ️")
    if tema.get("data_auj"):
        st.info("Neste assunto o STJ fixou depois uma orientação única no **Acórdão de Uniformização de Jurisprudência n.º 6/2024** "
                f"(primeira citação nos nossos dados: {tema['data_auj']}). É a nossa referência para validar.", icon="📌")

    aba1, aba2, aba3 = st.tabs(["Linha do tempo", "Divergências (lado a lado)", "Todos os acórdãos"])
    with aba1:
        if comps:
            linha_do_tempo(tema, ac, comps)
            st.caption("Passa o rato por cima de um ponto para ver a pergunta desse acórdão.")
        else:
            xs = [a["data"] for a in tema["acordaos"]]
            st.write(f'{len(xs)} acórdãos entre {min(xs)[:4]} e {max(xs)[:4]}, ainda sem comparações para desenhar arcos.')
    with aba2:
        div = sorted((c for c in comps if c["resultado"] == "solucao_oposta"), key=FP)  # confirmadas primeiro
        if not div:
            st.info("A IA não encontrou soluções opostas neste assunto com os pares comparados. "
                    "Isso não prova que não existam: só se compararam acórdãos consecutivos e só uma parte da amostra.")
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
            st.markdown("#### Outros pares comparados")
        for c in outros:
            a, b = ac[c["a_doc"]], ac[c["b_doc"]]
            with st.expander(f'{NOME[c["resultado"]]} · {a["data"]} → {b["data"]}'):
                st.write(c["justificacao"])
    with aba3:
        if termos:
            st.caption(f'A mostrar só os acórdãos que contêm "{pesquisa}" ({len(acertos[tid])} de {len(tema["acordaos"])}).')
        for a in acertos[tid]:
            with st.expander(f'{a["data"]} · proc. {a["processo"]} · {a["questao"][:110]}'):
                st.markdown(f'**Questão:** {a["questao"]}')
                st.markdown(f'**Solução:** {a["solucao"]}')
                if a.get("trecho"):
                    st.markdown(f'> {a["trecho"]}')
                st.caption(f'Relator: {a["relator"]} · ficha feita por {a["modelo"]} (confiança {a["confianca"]})')
                st.markdown(f'[Ver o acórdão original no DGSI]({a["url"]})')

# ====================================================================== DIVERGÊNCIA
elif pagina == DIVERGENCIA:
    st.title("⚖️ A divergência que o sistema encontrou")
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
                mostrar_divergencia(c, ac_t[c["a_doc"]], ac_t[c["b_doc"]], vir_t, t)
                if FP(c):
                    st.divider()
                    continue
                st.markdown("**Em simples:** num acórdão, o empregador só responde mais se se provar que teve **culpa**; no outro, "
                            "quando não cumpriu regras de segurança, **a culpa não é necessária**. O AUJ n.º 6/2024 veio fixar o que se exige "
                            "para esta responsabilidade (interpretação a confirmar por um jurista).")
    st.markdown("#### Porque é só uma?")
    st.markdown("- A IA é **cautelosa**: na revisão manual, errou sempre por dizer «não comparável» a mais, e nunca inventou divergências.\n"
                f"- Só {dados['fichas']} de {dados['total_trabalho']} acórdãos têm ficha, e só se compararam acórdãos consecutivos.\n"
                "- Com mais fichas e mais pares é provável que apareçam mais casos.")
    st.button("Explorar o assunto desta divergência →", on_click=ir, args=(EXPLORAR, 100), key="b_ex100")

# ====================================================================== SOBRE
else:
    st.title("ℹ️ Sobre o projeto")
    st.markdown("Protótipo feito para o desafio da ByTheLaw: agregar acórdãos **por tema** e identificar **decisões divergentes ao longo do tempo**. "
                f"Todo o código, a nota de decisões e a descrição do uso de IA estão no [repositório]({REPO}).")
    st.subheader("Como foi feito")
    st.markdown(
        "1. **Recolha responsável do DGSI** (pausas, cache, identificação): 21 681 acórdãos indexados, 1820 de mérito da 4.ª Secção.\n"
        "2. **Ficha por acórdão (IA):** lê o sumário e escreve a questão, as normas, a solução e uma citação literal, que um programa verifica.\n"
        "3. **Temas:** as fichas agrupam-se por semelhança de palavras (30 temas).\n"
        "4. **Comparação de pares (IA):** «mesma solução», «solução oposta» ou «não comparável», com citações de cada lado.\n"
        "5. **Viragem:** distingue divergência isolada de mudança duradoura de entendimento.\n"
        "6. **Validação:** com o AUJ n.º 6/2024 e com 25 veredictos revistos à mão.")
    st.subheader("Limites")
    st.markdown("- Só uma parte dos acórdãos tem ficha (ver «Em números», no Início); um só tribunal e uma só área.\n"
                "- Dois modelos de IA (um gratuito, mais fraco); a revisão manual foi feita por uma só pessoa sem formação jurídica.\n"
                "- A IA é cautelosa: errou na revisão por dizer «não comparável» a mais, mas já houve um falso positivo (assinalado na página da divergência).\n"
                "- A pesquisa é por palavras com sinónimos, e não por sentido; a app não usa IA em tempo real.")
    st.info("Esta ferramenta ajuda a **encontrar** possíveis divergências. Não substitui a leitura nem a opinião de um jurista.", icon="⚠️")

# Glossário: uma só vez, na barra lateral, em todas as páginas
with st.sidebar:
    glossario()
