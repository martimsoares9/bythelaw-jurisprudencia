"""Divergências de jurisprudência — STJ, 4.ª Secção (direito do trabalho).

A app só lê `dados.json` (já processado). Não chama a IA nem o DGSI.
Correr:  streamlit run app/app.py
"""
import json
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
    "nao_comparavel": "Tratam de questões ou factos diferentes. Não conta como divergência.",
}


@st.cache_data
def carregar():
    return json.loads((Path(__file__).parent / "dados.json").read_text())


dados = carregar()
temas = {t["id"]: t for t in dados["temas"]}

st.title("⚖️ Onde e quando o tribunal mudou de opinião")
st.caption("Supremo Tribunal de Justiça · 4.ª Secção (direito do trabalho) · 2010–2026 · fonte: dgsi.pt")
st.warning("**Classificação automática por IA, pode conter erros.** As citações são verificadas por programa (têm de existir "
           "no sumário do acórdão), mas a interpretação não foi validada por um jurista. Amostra de 358 acórdãos de um "
           "conjunto de 1820; ver as limitações na nota de decisões.", icon="⚠️")

ordem = sorted(temas, key=lambda i: (i != 100, -len(temas[i]["comparacoes"]), -len(temas[i]["acordaos"])))
tid = st.sidebar.selectbox("Escolhe um assunto", ordem, format_func=lambda i: f'{temas[i]["nome"]} ({len(temas[i]["acordaos"])} acórdãos)')
tema = temas[tid]
ac = {a["doc_id"]: a for a in tema["acordaos"]}
comps = sorted(tema["comparacoes"], key=lambda c: ac[c["a_doc"]]["data"])
contagem = {k: sum(c["resultado"] == k for c in comps) for k in NOME}

st.sidebar.markdown("**Como ler**")
for k in NOME:
    st.sidebar.markdown(f'<span style="color:{COR[k]}">●</span> **{NOME[k]}**: {EXPLICA[k]}', unsafe_allow_html=True)
st.sidebar.caption("Um **acórdão** é a decisão de vários juízes; o **sumário** é o seu resumo oficial.")

st.subheader(tema["nome"])
c1, c2, c3, c4 = st.columns(4)
c1.metric("Acórdãos", len(ac))
c2.metric("Soluções opostas", contagem["solucao_oposta"])
c3.metric("Mesma solução", contagem["mesma_solucao"])
c4.metric("Não comparáveis", contagem["nao_comparavel"])
if tema.get("data_auj"):
    st.info("Neste assunto o STJ fixou depois uma orientação única no **Acórdão de Uniformização de Jurisprudência n.º 6/2024** "
            f"(primeira citação nos nossos dados: {tema['data_auj']}). É a nossa referência para validar.", icon="📌")

aba1, aba2, aba3 = st.tabs(["Linha do tempo", "Divergências (lado a lado)", "Todos os acórdãos"])

with aba1:
    import math
    from datetime import date, timedelta

    def dia(x):
        return date.fromisoformat(x)

    xs = [a["data"] for a in tema["acordaos"]]
    fig = go.Figure()
    for k in NOME:  # primeiro os cinzentos, por baixo; os laranjas ficam por cima
        for c in comps:
            if c["resultado"] != k:
                continue
            d0, d1 = dia(ac[c["a_doc"]]["data"]), dia(ac[c["b_doc"]]["data"])
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
    st.plotly_chart(fig, width='stretch')
    st.caption("Cada ponto é um acórdão. Os arcos ligam acórdãos consecutivos que a IA comparou; "
               "o arco laranja grosso é uma divergência.")

with aba2:
    div = [c for c in comps if c["resultado"] == "solucao_oposta"]
    if not div:
        st.info("A IA não encontrou soluções opostas neste assunto com os pares comparados. "
                "Isso não prova que não existam: só se compararam acórdãos consecutivos e só uma parte da amostra.")
    for c in div:
        a, b = ac[c["a_doc"]], ac[c["b_doc"]]
        st.markdown(f'### 🟠 {a["data"]}  ↔  {b["data"]}')
        st.markdown(f'**Porquê a IA diz que são opostos:** {c["justificacao"]}')
        ca, cb = st.columns(2)
        for col, x, cit, lado in ((ca, a, c["citacao_a"], "Mais antigo"), (cb, b, c["citacao_b"], "Mais recente")):
            with col:
                st.markdown(f'**{lado}** · {x["data"]} · proc. {x["processo"]}')
                st.markdown(f'*Questão:* {x["questao"]}')
                st.markdown(f'*Solução:* {x["solucao"]}')
                st.markdown(f'> {cit}')
                st.markdown(f'[Ver o acórdão original no DGSI]({x["url"]})')
        st.divider()
    st.markdown("#### Outros pares comparados")
    for c in comps:
        if c["resultado"] == "solucao_oposta":
            continue
        a, b = ac[c["a_doc"]], ac[c["b_doc"]]
        with st.expander(f'{NOME[c["resultado"]]} · {a["data"]} → {b["data"]}'):
            st.write(c["justificacao"])

with aba3:
    for a in tema["acordaos"]:
        with st.expander(f'{a["data"]} · proc. {a["processo"]} · {a["questao"][:110]}'):
            st.markdown(f'**Questão:** {a["questao"]}')
            st.markdown(f'**Solução:** {a["solucao"]}')
            if a.get("trecho"):
                st.markdown(f'> {a["trecho"]}')
            st.caption(f'Relator: {a["relator"]} · ficha feita por {a["modelo"]} (confiança {a["confianca"]})')
            st.markdown(f'[Ver o acórdão original no DGSI]({a["url"]})')
