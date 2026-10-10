# Nota de decisões

> Entregável do enunciado: *"uma nota curta sobre as decisões tomadas: subset escolhido, abordagem para agrupar por tema e para detetar divergências, e principais limitações"*.
> Estado: as secções 1 e 4 (parcial) estão escritas com dados reais. As secções 2 e 3 descrevem o método **planeado** e serão confirmadas com resultados quando as etapas estiverem feitas; o que ainda não foi feito está marcado com **[POR FAZER]**.

## 1. Subset escolhido — [FEITO]

**STJ, 4.ª Secção (direito do trabalho), 2010 a 2026.**

| Decisão | Critério |
|---|---|
| **Tribunal: STJ** | É onde a jurisprudência se consolida e onde as viragens de entendimento mais importam. Os acórdãos de uniformização de jurisprudência (AUJ) são prova externa de divergências reais, o que permite validar o sistema. |
| **Área: 4.ª Secção (trabalho)** | Casos do dia a dia (despedimento, férias, retribuição), vocabulário coerente, volume gerível (~1700 acórdãos estimados). |
| **Intervalo: 2010–2026** | Escolhido depois de contar o índice real (21 681 acórdãos, todas as secções, 2009–2026): cada ano tem pelo menos algumas dezenas de acórdãos laborais e 16 anos mostram bem as mudanças de entendimento. |

**Como se chegou a este subset.** Primeiro indexei toda a lista do STJ (barato: 219 páginas), contei por ano, e só depois escolhi o intervalo. Medi o peso da 4.ª Secção numa amostra aleatória de 150 acórdãos: 12 são da 4.ª Secção (~8%).

**Recolha responsável.** Pausa de 1,5 s mais variação aleatória entre pedidos, um pedido de cada vez, `User-Agent` com nome e email, cache local (nunca se pede a mesma página duas vezes), recuo em erros 429/5xx, leitura do `robots.txt` (o do DGSI devolve 404, ou seja, não existe e não declara restrições). Só se abrem os acórdãos candidatos, não o site todo.

## 2. Agrupar por tema — [POR FAZER]

Método planeado (detalhe em `CLAUDE.md`, secção 3.5):

1. Um modelo de IA lê o **sumário** de cada acórdão (o resumo oficial do tribunal) e extrai: a questão jurídica (sem nomes de partes), as normas citadas, a solução em uma frase e uma citação literal do sumário que a sustenta. A citação tem de existir mesmo no sumário; senão a resposta é rejeitada.
2. Agrupam-se as **questões jurídicas** (não o texto todo) por semelhança, com *embeddings* e HDBSCAN, juntando a referência às normas.
3. Cada tema recebe um nome gerado pelo modelo e 3–5 temas são verificados à mão.

*Porquê assim:* o sumário é o campo mais denso e fiável; agrupar pela questão e não pelo texto evita juntar acórdãos só porque partilham factos ou nomes.

## 3. Detetar divergências — [POR FAZER]

Princípio: **só se compara o que é comparável.** Duas decisões opostas sobre factos diferentes não são uma divergência.

- Dentro de cada tema, só se comparam pares com a questão muito próxima.
- Um modelo mais forte atua como "juiz de pares": dados dois sumários (o mais antigo e o mais recente), responde `mesma_solucao`, `solucao_oposta` ou `nao_comparavel`, com uma citação de cada lado (também verificada). `nao_comparavel` é uma resposta legítima e esperada.
- **Divergência** = soluções opostas que coexistem. **Viragem** = a orientação dominante muda de forma sustentada; marca-se quando, ordenando por data, a maioria das soluções antes e depois de uma data difere, com um mínimo de acórdãos de cada lado.
- **Validação:** (a) ver se o sistema deteta as divergências que motivaram os AUJ da 4.ª Secção; (b) rever à mão 25 classificações e reportar a taxa de acerto e exemplos de erros. **[resultados: POR FAZER]**

## 4. Limitações

**4.1 O filtro por descritores perde acórdãos laborais — [MEDIDO, parcial]**
A lista do DGSI não mostra a secção; só se vê abrindo cada acórdão. Abrir os 21 681 seria cerca de 15 horas de pedidos contínuos (estimativa: ~2,5 s por pedido) só para descobrir que ~92% não interessam, o que contraria o "recolha responsável" do enunciado e não cabe no prazo. Por isso pré-filtro pelos descritores (palavras-chave laborais).
- Na amostra de 150, o filtro inicial apanhava 8 dos 12 acórdãos da 4.ª Secção (~67%); alargado, 9 em 12 (75%). A amostra é pequena, o valor real é incerto.
- Falha em acórdãos com descritores genéricos ("revista excecional") ou laborais que não previ ("descanso semanal").
- Melhoria planeada: recolher também os acórdãos dos **relatores** que julgam quase só na 4.ª Secção. Sobe o recall, mas não chega a 100%. **[recall final: POR MEDIR]**
- *Consequência:* o sistema vê uma boa amostra da jurisprudência laboral, não toda; uma viragem pode ficar por detetar e os números não são contagens oficiais.

**4.2 Outras limitações**
- Um só tribunal e uma só área.
- Os modelos de IA erram: por isso as citações são verificadas por automático e uma amostra é revista à mão.
- Diferenças de factos podem parecer divergências.
- O índice do DGSI muda enquanto se recolhe (entram acórdãos novos no topo); duplicados são inofensivos porque cada acórdão tem um identificador único.
- Sumários de qualidade desigual; nem todos os acórdãos decidem o mérito (os de admissibilidade são excluídos).
- A classificação é automática e pode conter erros; a app terá um aviso visível.
