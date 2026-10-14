# Processo e orquestração do trabalho

Este ficheiro explica **todos os passos do trabalho, por ordem, e como as peças se encaixam**. Para o *porquê* das decisões ver [`NOTA_DECISOES.md`](NOTA_DECISOES.md); para o uso de IA ver [`AI_USAGE.md`](AI_USAGE.md); para correr o projeto ver o [`README.md`](README.md).

## 1. Visão geral

```
dgsi.pt ──scraper.py──▶ base SQLite (data/acordaos.db)
                              │
   pipeline/filtrar.py        ▼   só 4.ª Secção + decisões de mérito (1820 acórdãos)
   pipeline/extrair.py   ──IA──▶  ficha por acórdão: questão, normas, solução, tipo, citação verificada
   pipeline/agrupar.py        ▼   temas (TF-IDF)            ┐
   pipeline/atribuir_temas.py ▼   fichas novas -> temas     │ sem IA
   pipeline/comparar.py  ──IA──▶  pares: mesma solução / oposta / não comparável (+ citações)
   pipeline/validar_auj.py    ▼   validação com o AUJ n.º 6/2024
   pipeline/viragens.py       ▼   divergência isolada ou viragem   ┘
   pipeline/exportar.py       ▼   app/dados.json (só leitura)
                              │
                         app/app.py (Streamlit; IA só na página opcional «Perguntar à IA») ──▶ https://divergencias-stj.streamlit.app/
```

**Princípio de desenho:** a IA trabalha *antes*, em lote, e deixa resultados guardados; a app lê um ficheiro, por isso é rápida, gratuita e dá sempre os mesmos resultados. Exceção opcional: a página «Perguntar à IA» chama a IA em tempo real, com chave nos segredos, limites diários, cache e citações verificadas; sem quota ou sem chave, o resto da app funciona na mesma.

## 2. Os passos, por ordem

| # | Passo | Comando / ficheiro | Entrada → saída | IA? |
|---|---|---|---|---|
| 1 | Indexar a lista do STJ | `python scraper.py indexar` | DGSI → tabela `lista` (21 681 acórdãos) | não |
| 2 | Escolher o subset com números | `python scraper.py stats` | contagens por ano → STJ, 4.ª Secção, 2010–2026 | não |
| 3 | Abrir os acórdãos candidatos | `python scraper.py detalhes ...` | `lista` → tabela `acordaos` (sumário, texto…) | não |
| 4 | Apanhar o que o filtro perdeu | `scraper.py detalhes --relatores ...` | relatores da 4.ª Secção → mais 1059 acórdãos | não |
| 5 | Filtrar | `python pipeline/filtrar.py` | `acordaos` → `filtrados`: **1820** de mérito da 4.ª Secção | não |
| 6 | Ficha por acórdão | `python pipeline/extrair.py correr` | sumário → tabela `extracoes` (**400** fichas, 100% com citação válida) | **sim** |
| 7 | Agrupar por tema | `python pipeline/agrupar.py` | questões → tabela `temas` (**30** temas) | não |
| 8 | Fichas novas → temas | `python pipeline/atribuir_temas.py` | `extracoes` sem tema → `temas` (limiar 0,40) | não |
| 9 | Comparar pares | `python pipeline/comparar.py correr --temas 100,1,2,4` | pares mais parecidos do mesmo tema (modo `vizinhos`; `consecutivos` foi o dos primeiros 69) → tabela `comparacoes` | **sim** |
| 10 | Validar com um AUJ | `python pipeline/validar_auj.py selecionar/extrair/comparar` | 47 acórdãos do tema do AUJ n.º 6/2024 → comparações | **sim** |
| 11 | Viragem | `python pipeline/viragens.py` | `comparacoes` → tabela `viragens` (viragem, coexistente, isolada ou inconsistente) | não |
| 12 | Revisão manual | `revisao/CASOS.md`, `revisao/respostas.csv`, `revisao/pares_revistos.csv` | 25 veredictos revistos: **18 certos em 23** (78%) | revisor humano |
| 13 | Exportar para a app | `python pipeline/exportar.py` | tabelas → `app/dados.json` | não |
| 14 | App e publicação | `streamlit run app/app.py` | `dados.json` → app online | não |

## 3. Orquestração: o que faz tudo funcionar em conjunto
- **Cada etapa lê e escreve na mesma base SQLite**, por isso podem correr em separado e pela ordem acima.
- **Idempotente e retomável:** `scraper.py` (chave `doc_id`), `extrair.py` (ignora o que já tem ficha) e `comparar.py` (ignora pares feitos) não repetem trabalho.
- **Cache das respostas da IA** em `cache/llm/`, por hash do pedido: repetir não gasta de novo.
- **Verificação automática das citações:** toda a citação que a IA devolve tem de ser texto literal do sumário; senão é recusada ou reduzida ao maior bloco literal. É o que evita invenções.
- **Limites de custo:** a chave não tinha crédito; o modelo pago (`claude-haiku-5-5`) serviu para 264 fichas e depois usou-se um modelo gratuito (`nvidia/nemotron-3-super-120b-a12b:free`, 50 pedidos por dia). As etapas **param sozinhas** ao atingir o limite diário e retomam no dia seguinte (pedidos agendados com o Claude Code).
- **Segurança do trabalho:** `pipeline/guardar_ia.py` guarda fichas, temas e comparações em `dados/ia_tabelas.json.gz` (restaura-se com `guardar_ia.py restaurar`). A chave fica só em `.env`, fora do git.
- **Fornecedor de IA configurável:** modelo, fornecedor e chave lidos do ambiente (`LLM_MODEL_EXTRACAO`, `LLM_MODEL_JUIZ`, `LLM_BASE_URL`, `OPENROUTER_API_KEY`).

## 4. Como se trabalhou com o Claude Code (resumo)
1. **Plano e regras escritos antes do código:** um ficheiro de contexto (instruções para a IA) com o desafio, as decisões e as regras: fases pequenas e testáveis, mostrar resultados antes de avançar, nada de recolha em massa sem confirmar o contacto, chaves só em `.env`, commits pequenos.
2. **Fases com confirmação:** 1 recolha, 2 filtro, 3 fichas, 4 temas e pares, 5 validação, 6 app e publicação, 7 documentação.
3. **Em cada fase:** correr numa amostra pequena, mostrar exemplos, só depois escalar (por exemplo, 50 fichas antes das restantes).
4. **O que correu mal e se corrigiu:** respostas vazias do modelo (raciocínio desligado), prompt que confundia "admissibilidade" com mérito, marcador de AUJ demasiado largo (53 marcados, só 2 verdadeiros), embeddings bloqueados (trocados por TF-IDF), limite diário de pedidos. Ver `AI_USAGE.md`.
5. **Validação:** citações verificadas por programa, caso do AUJ n.º 6/2024, e revisão manual de 25 veredictos.

## 5. Números finais (2026-10-14)
- 21 681 acórdãos indexados · 2972 recolhidos · **1820** de mérito da 4.ª Secção.
- **400** fichas da IA (299 de mérito; 264 com Haiku, 136 com Nemotron gratuito) · **30** temas · **89** comparações (71 válidas): 2 soluções opostas, 19 mesma solução, 50 não comparáveis.
- Pares escolhidos por semelhança (os últimos 20): 16 válidos, 10 comparáveis (62%), contra 20% nos pares consecutivos.
- Divergência candidata: 2011-05-18 contra 2011-10-26, sobre se é preciso provar a culpa do empregador (questão próxima da que o AUJ n.º 6/2024 veio resolver). O sistema marca-a como **inconsistente** (cadeias de «mesma solução» ligam os dois lados). Um segundo caso (2012 contra 2026) foi marcado como **falso positivo** (diferença de factos). **Nenhuma viragem confirmada.**
- Revisão manual (feita antes dos pares por semelhança): 18 certos, 5 errados, 2 sem opinião; todos os erros são "não comparável" a mais.

## 6. Limitações principais
Só 20% dos acórdãos têm ficha; um só tribunal e uma só área; dois modelos de IA diferentes; juiz de pares gratuito e mais fraco do que o previsto; amostra de fichas não aleatória (o tema do AUJ foi escolhido à mão); revisão por uma só pessoa sem formação jurídica; pesquisa da app por palavras e sinónimos, não por sentido. Detalhes na `NOTA_DECISOES.md`.
