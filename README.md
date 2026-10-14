# Divergências de Jurisprudência (STJ, direito do trabalho)

Protótipo que agrega acórdãos do STJ **por tema** e procura **decisões divergentes ao longo do tempo** (onde e quando o tribunal mudou de entendimento). Desafio ByTheLaw; fonte: [dgsi.pt](https://www.dgsi.pt). Subset: STJ, 4.ª Secção, 2010–2026.

> **Estado (2026-10-13):** recolha (1820 acórdãos de trabalho), fichas por IA (400), temas (30), comparação de pares e app feitos. Falta o vídeo.

## Entregáveis do enunciado e onde estão

| # | O enunciado pede | Onde está | Estado |
|---|---|---|---|
| 1 | Link da aplicação em produção | [https://divergencias-stj.streamlit.app/](https://divergencias-stj.streamlit.app/) | Feito (Streamlit Community Cloud; se estiver a dormir, clicar em "Yes, get this app back up!") |
| 2 | Repositório com README que explique como correr | Este ficheiro, secção "Como correr" | Feito |
| 3 | Nota curta de decisões | [`NOTA_DECISOES.md`](NOTA_DECISOES.md) | Subset, temas, divergências, revisão manual (acerto 78%) e limitações escritos |
| 4 | Descrição do uso de IA | [`AI_USAGE.md`](AI_USAGE.md) | Em curso |
| 5 | Vídeo de demonstração com narração | *(link a acrescentar aqui)* | Por fazer |

## Mapa de ficheiros (o que cada um contém)

| Ficheiro | O que contém |
|---|---|
| `README.md` | Este mapa, os entregáveis e como correr o projeto |
| `NOTA_DECISOES.md` | **Porquê** de cada decisão: subset, recolha responsável, método de temas e de divergências, limitações |
| `PROCESSO.md` | **Todos os passos do trabalho, por ordem, e a orquestração das peças** (o único ficheiro extra) |
| `AI_USAGE.md` | Como se usou a IA: ferramentas, fluxo, diário, o que funcionou e o que falhou, validação |
| `scraper.py` | Programa que lê o DGSI e guarda numa base SQLite (`indexar`, `detalhes`, `stats`) |
| `filtro_laboral.txt` | Palavras-chave laborais usadas para escolher que acórdãos abrir (lido pelo scraper) |
| `relatores_4secao.txt` | Relatores que julgam quase só na 4.ª Secção, usados na 2.ª etapa da recolha |
| `pipeline/filtrar.py` | Etapa 2: fica só com a 4.ª Secção e decisões de mérito |
| `pipeline/extrair.py` | Etapa 3: o LLM lê o sumário e escreve a ficha (questão, normas, solução, citação verificada) |
| `pipeline/agrupar.py` | Etapa 4a: agrupa os acórdãos em temas (TF-IDF, sem custos) |
| `pipeline/comparar.py` | Etapa 4b: o LLM compara pares do mesmo tema (mesma solução, oposta, não comparável) |
| `pipeline/validar_auj.py` | Etapa 5: validação com o AUJ n.º 6/2024 (seleciona, extrai e compara o tema) |
| `pipeline/viragens.py` | Etapa 5b: distingue divergência isolada de viragem (mínimo de acórdãos ligados de cada lado) |
| `pipeline/exportar.py`, `pipeline/nomes_temas.json` | Etapa 6: gera `app/dados.json` com nomes legíveis dos temas |
| `pipeline/guardar_ia.py` | Guarda/restaura as tabelas da IA em `dados/ia_tabelas.json.gz` |
| `app/app.py`, `app/dados.json`, `app/sinonimos.json` | A aplicação Streamlit, os dados só-leitura que ela lê e a lista de sinónimos da pesquisa |
| `requirements.txt`, `app/requirements.txt` | Dependências do pipeline e da app |
| `dados/acordaos.db.gz` | Cópia comprimida da base de dados recolhida (antes das fichas da IA) |
| `dados/ia_tabelas.json.gz` | Fichas da IA, temas e comparações (pequeno) |
| `data/`, `cache/` | Base de dados e páginas descarregadas; locais, **não** vão para o git |

## Como correr

Requer Python 3.11+. Antes de recolher, edita a constante `CONTACTO` no topo de `scraper.py` com o teu nome e email.

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install requests beautifulsoup4 lxml

# 1) Indexar a lista (219 páginas, ~10 min). Testar primeiro com --max-paginas 3
python scraper.py indexar --ate-ano 2010
python scraper.py stats --descritores @filtro_laboral.txt     # contagens por ano

# 2) Abrir os acórdãos candidatos (~1 h, retomável)
python scraper.py detalhes --ano-min 2010 --ano-max 2026 --descritores @filtro_laboral.txt --limite 100000

# 2b) Acórdãos dos relatores da 4.ª Secção que o filtro perdeu (~45 min, retomável)
python scraper.py detalhes --ano-min 2010 --ano-max 2026 --relatores relatores_4secao.txt --limite 100000

# 3) Filtrar: 4.ª Secção + mérito
python pipeline/filtrar.py            # contagens
python pipeline/filtrar.py exemplos   # 5 exemplos
python pipeline/filtrar.py relatores  # relatores da 4.ª Secção
```

**Atalho: usar a base já recolhida** (sem repetir os passos 1 e 2):

```bash
mkdir -p data && python -c "import gzip,shutil;shutil.copyfileobj(gzip.open('dados/acordaos.db.gz'),open('data/acordaos.db','wb'))"
```

## Correr a aplicação

```bash
pip install -r app/requirements.txt
streamlit run app/app.py
```

A app só lê `app/dados.json`. Para a publicar: Streamlit Community Cloud, ficheiro principal `app/app.py`.

**O que tem a app** (um átrio de entrada e 4 páginas, sem barra lateral): **Início** (pesquisa, 3 atalhos e números), **Explorar assuntos** (31 assuntos, pesquisa por relevância com sinónimos, linha do tempo com arcos em que se vê que acórdãos cada arco liga: passa o rato por um losango ou escolhe um par para o realçar e ler os dois acórdãos com as citações e o link para o DGSI; fichas de cada acórdão), **Divergência encontrada** (o caso candidato lado a lado, com ressalvas), **Perguntar à IA** (opcional, ver abaixo) e **Sobre o projeto** (método e limites). O glossário é um botão no topo e o aviso de IA está no Início e no rodapé. Não usa o DGSI em tempo real.

**IA em tempo real (opcional e protegida).** A página «Perguntar à IA» só funciona se existir a chave `OPENROUTER_API_KEY` nos segredos da app (Streamlit Cloud: *Manage app → Settings → Secrets*, uma linha `OPENROUTER_API_KEY = "..."`); sem chave aparece desligada e o resto da app funciona. Lê os 5 acórdãos mais relevantes e responde só com base neles; cada citação tem de existir literalmente no sumário, senão não mostra resposta. Limites: 5 perguntas por visita e 40 por dia no total (a chave gratuita dá 50), com cache; se a quota acabar, mostra os acórdãos mais relevantes.

## Repetir o pipeline com IA (opcional)

Precisa de uma chave de um fornecedor de LLM no ficheiro `.env` (nunca vai para o git): `OPENROUTER_API_KEY=...`. Modelo e fornecedor leem-se do ambiente (`LLM_MODEL_EXTRACAO`, `LLM_MODEL_JUIZ`, `LLM_BASE_URL`). As respostas ficam em cache (`cache/llm/`), por isso repetir não gasta de novo.

```bash
pip install -r requirements.txt
python pipeline/guardar_ia.py restaurar            # recupera as fichas/temas/comparações já feitas
python pipeline/extrair.py ping                    # testa a chave
python pipeline/extrair.py correr --amostra 50     # fichas (retomável; pára ao atingir o limite diário gratuito)
python pipeline/agrupar.py                         # temas (cuidado: pode mudar os números dos temas)
python pipeline/validar_auj.py selecionar && python pipeline/validar_auj.py extrair && python pipeline/validar_auj.py comparar
python pipeline/viragens.py                        # divergência isolada ou viragem
python pipeline/exportar.py                        # atualiza app/dados.json
```
