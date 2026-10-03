# CLAUDE.md — Projeto: Divergências de Jurisprudência (desafio BytheLaw)

> Contexto para o Claude Code. Lê isto TODO antes de escrever código.
> Estado em 2026-10-03. O que está marcado **[DECIDIDO]** não se rediscute sem motivo; **[PROPOSTO]** é a melhor hipótese mas ainda não foi validada; **[ABERTO]** depende de dados que ainda não existem.

## 1. O desafio (resumo do enunciado)

> O texto original completo está em `ENUNCIADO.md`. Em caso de dúvida, prevalece o enunciado.

Construir, do zero, o protótipo de uma ferramenta que compita com a ByTheLaw mas centrada em **jurisprudência**: agrega acórdãos **por tema** e identifica **decisões divergentes ao longo do tempo** (onde e quando os tribunais mudaram de entendimento sobre a mesma questão).

- Fonte obrigatória: **dgsi.pt**. Subset à escolha (tribunal, área, intervalo), com critério explicado.
- Recolha **responsável**, sem sobrecarregar o site.
- IA usada de forma intensiva (engenharia agêntica, código, análise dos acórdãos). **Rapidez > polimento.**
- Entregáveis: (1) link da app em produção; (2) repositório com README que explique como correr; (3) nota curta de decisões (subset, agrupamento por tema, deteção de divergências, limitações); (4) descrição do uso de IA (ferramentas, fluxo, o que funcionou / não funcionou); (5) vídeo curto de demo com narração.
-**Prazo:** 12 dias a contar apartir de agora. Entregar antes do tempo dá pontos extra.

## 2. Quem é o utilizador

Gato, estudante de Engenharia e Ciência de Dados (FCT Coimbra), Windows, trabalha em português. **Não tem formação jurídica**: explica termos jurídicos em linguagem simples quando surgirem. Prefere **ficheiros completos e prontos a usar** a instruções soltas. Escreve README, comentários e UI em **português europeu**.

## 3. Decisões por tópico

### 3.1 Subset — [PROPOSTO, fecha-se com `stats`]
- **Tribunal:** STJ. Critério: é onde a jurisprudência se consolida e onde as viragens de entendimento são mais relevantes; os acórdãos de uniformização de jurisprudência (AUJ) são prova externa de divergências reais, o que permite validar.
- **Área:** secção social (direito do trabalho) = `Nº Convencional: 4.ª SECÇÃO`. Critério: situações do dia a dia (despedimento, férias, retribuição), vocabulário coerente, volume gerível.
- **Intervalo:** 2010–2024 como ponto de partida; os dados do DGSI chegam a set/2026, por isso pode estender-se. **Decidir depois de correr `indexar` + `stats`**, com base na contagem real por ano, e escrever o critério final no README.
- **Limitação a registar:** a lista do DGSI não traz a secção; o pré-filtro por descritores (regex laboral) poupa pedidos mas perde acórdãos laborais com outros descritores (recall < 100%).

### 3.2 O que se sabe do DGSI (observado em páginas reais)
- Vista de listas: `https://www.dgsi.pt/jstj.nsf/Por%20Ano?OpenView&Start=N`. Todo o STJ, todas as secções, **do mais recente para o mais antigo**. ~99 acórdãos na primeira página; o link "Seguinte" dá a página seguinte (ex.: `Start=124`). Colunas: SESSÃO (data dd-mm-aaaa), PROCESSO (link), RELATOR, DESCRITOR (várias linhas com `<br>`). Tem `<meta name="robots" content="noindex">` (é para motores de busca, não proíbe acesso, mas reforça ser discreto).
- Acórdão: `/jstj.nsf/954f0ce6ad9dd8b980256b5f003fa814/<doc_id de 32 hex>?OpenDocument`. Ignorar `&Highlight=...`. Tabela de 2 colunas "rótulo: valor" com: Processo, Nº Convencional (secção), Relator, Descritores, Data do Acordão, Votação, Texto Integral, Privacidade, Meio Processual, Decisão, Sumário, Decisão Texto Integral.
- **Sumário** (do próprio tribunal) é o campo mais valioso. Numeração romana interna é inconsistente: não depender dela.
- O **texto integral** pode ser enorme (centenas de linhas com notas): para o LLM usar sumário + excerto final da decisão, não tudo.
- **Nem todo o acórdão decide o mérito.** Exemplo real: um acórdão da "Formação" que admite uma revista excecional tem um sumário que é uma pergunta, não uma solução. Estes devem ser filtrados (`admissibilidade=1` no parser, e o LLM classifica `tipo`).
- Os URLs/ordem podem mudar durante a recolha (entram acórdãos novos no topo e deslocam o `Start`); duplicados são inofensivos porque `doc_id` é chave primária.
- `robots.txt`: **[ABERTO]** o utilizador ainda não reportou o conteúdo. O scraper lê-o e recusa o que for proibido; confirmar com ele antes da recolha completa.

### 3.3 Scraper — [DECIDIDO e escrito, ainda NÃO testado contra a rede]
Ficheiro `scraper.py` (já existe, ver raiz do repo). Parser de acórdão e de lista **testados offline** com HTML real. Duas fases:
- **Fase A `indexar`:** segue "Seguinte" desde `Start=1`, grava na tabela `lista` (doc_id, url, data, processo, relator, descritores). Pára ao passar de `--ate-ano`.
- **Fase B `detalhes`:** só para os anos/descritores escolhidos, grava na tabela `acordaos` (secção, sumário, texto…).
- Responsável: respeita robots.txt, pausa 1,5 s + jitter, cache HTML em `cache/`, retoma (PK por `doc_id`), backoff em 429/5xx, User-Agent identificado (**constante `CONTACTO` tem de ser editada pelo utilizador**).
- Próximo passo imediato: o utilizador corre `python scraper.py indexar --max-paginas 3` e cola o output.

### 3.4 Arquitetura — [PROPOSTO]
```
dgsi.pt ──scraper──▶ SQLite (lista, acordaos)
                         │
        pipeline/ (cada etapa lê/escreve tabelas, idempotente, com cache de chamadas LLM)
          1 filtrar     secção 4.ª + só decisões de mérito
          2 extrair     LLM por acórdão: questão jurídica, norma-chave, solução, tipo
          3 agrupar     temas (embeddings + referência normativa)
          4 comparar    pares dentro do tema, por ordem cronológica (LLM juiz)
          5 viragens    agregação temporal → data da viragem
          6 exportar    SQLite/JSON pequeno só-leitura para a app
                         │
                         ▼
        app/ (Streamlit, só lê o ficheiro exportado; NÃO chama LLM nem DGSI em produção)
```
Stack: Python 3.11+, SQLite, `sentence-transformers` (embeddings multilingues, local e gratuitos), HDBSCAN, API da Anthropic para extração/juízo, Streamlit + Plotly, deploy em Streamlit Community Cloud ou Hugging Face Spaces. Estrutura sugerida: `scraper/`, `pipeline/`, `app/`, `data/`, `README.md`, `AI_USAGE.md`, `.env` (não versionado), `.gitignore` (já ignora `.venv`, `cache/`, `.env`).

### 3.5 Lógica de deteção de divergências — [PROPOSTO, é o coração do trabalho]
Princípio: **só se compara o que é comparável.** Duas decisões "opostas" sobre factos diferentes não são uma divergência.
1. **Extração por acórdão (LLM, só sumário + excerto da decisão), saída JSON estrita:**
   `questao_juridica` (genérica, sem nomes de partes), `normas` (ex.: "CT art. 366.º"), `solucao` (1 frase), `tipo` ∈ {merito, admissibilidade, processual, outro}, `trecho` (citação literal curta do sumário que suporta a solução), `confianca`.
   Validação automática: `trecho` tem de ser substring do sumário; senão rejeitar/repetir.
2. **Agrupar por tema:** embeddings de `questao_juridica` (não do texto todo) + chave dura de normas citadas. Clusters HDBSCAN com nome gerado pelo LLM a partir de uma amostra. Verificar manualmente 3–5 clusters.
3. **Pares candidatos:** dentro de cada tema, só pares com questão muito próxima (vizinhos mais próximos, não todos contra todos) para controlar custo.
4. **Juiz de pares (LLM):** dados dois sumários (A mais antigo, B mais recente) devolve `mesma_solucao | solucao_oposta | nao_comparavel`, justificação curta e **uma citação de cada lado** (também verificada por substring). `nao_comparavel` é uma resposta legítima e esperada (factos diferentes).
5. **Viragem vs. divergência:** *divergência* = soluções opostas que coexistem; *viragem* = a orientação dominante muda de forma sustentada no tempo. Marcar viragem quando, ordenando por data, a maioria das soluções antes e depois de uma data difere, com mínimo de N acórdãos de cada lado (N pequeno, configurável, ex. 3). Registar também se um **AUJ** (regex: "uniformização de jurisprudência", "Acórdão Uniformizador") fecha a questão.
6. **Validação (obrigatória para a nota):** (a) usar AUJs da secção social como verdade-terreno: o sistema deteta a divergência que motivou o AUJ? (b) rever à mão 20–30 classificações e reportar a taxa de acerto e exemplos de erros.
7. **Custos:** cache de todas as respostas LLM por hash do input; modelo barato para extração (ex.: `claude-haiku-4-5-20251001`), modelo mais forte para o juiz de pares (ex.: `claude-sonnet-5-5`). Confirmar nomes de modelos e limites em https://docs.claude.com antes de usar.

### 3.6 Interface — [PROPOSTO]
Streamlit: escolher/pesquisar tema → lista de acórdãos → **linha do tempo** (Plotly) com a viragem assinalada → dois acórdãos lado a lado com a citação que justifica → link para o original no DGSI. Aviso visível: "classificação automática por IA, pode conter erros".

### 3.7 Deploy e entregáveis
Deploy cedo (dia ~5), não no fim. A app lê um ficheiro de dados já processado. README com: como correr, subset + critério, como foi feita a recolha responsável, limitações. `AI_USAGE.md` já existe (tabela de diário); **continuar a preencher** a cada passo relevante, incluindo falhas.

## 4. Limitações a assumir na nota
Um só tribunal e uma só área; recall do pré-filtro por descritores; erros do LLM (por isso as citações verificadas e a amostra revista à mão); diferenças factuais podem parecer divergências; índice do DGSI muda enquanto se recolhe; sumários de qualidade desigual.

## 5. Regras de trabalho para o Claude Code
- Trabalhar por fases pequenas e **testáveis**; mostrar o resultado de cada fase (contagens, 3 exemplos) antes de avançar.
- Nada de recolha em massa sem o utilizador ter confirmado `CONTACTO` e o `robots.txt`. Começar sempre com `--limite`/`--max-paginas` pequenos.
- Chaves de API só em `.env` (nunca no repositório).
- Commits pequenos e frequentes; mensagens em português.
- Pipeline idempotente: re-correr não duplica nem repete chamadas pagas.
- Explicar decisões não óbvias num comentário curto e registar no `AI_USAGE.md` o que correu mal.


Trabalha sempre no branch main. No fim de cada tarefa, faz commit com uma mensagem clara e push para o main

## Fluxo de trabalho
- O projeto divide-se em 4 fases: (1) scraper do DGSI, (2) agrupamento por temas e deteção de divergências, (3) interface, (4) deploy, README e nota de decisões.
- Trabalha sempre no branch `main`.
- Quando terminares uma fase:
  1. Confirma que o código corre sem erros.
  2. Atualiza este CLAUDE.md com o que foi feito, as decisões tomadas e o que falta.
  3. Faz commit e push para o `main`.
  4. Avisa-me claramente: "Fase X concluída — abre uma sessão nova para a fase seguinte."