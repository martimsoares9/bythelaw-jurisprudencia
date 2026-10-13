# Nota de decisões

> Entregável do enunciado: *"uma nota curta sobre as decisões tomadas: subset escolhido, abordagem para agrupar por tema e para detetar divergências, e principais limitações"*.
> Estado a 2026-10-13: subset, temas e deteção de divergências estão feitos e medidos; a revisão manual de 25 classificações está feita (secção 3).

## 1. Subset escolhido — [FEITO]

**STJ, 4.ª Secção (direito do trabalho), 2010 a 2026.**

| Decisão | Critério |
|---|---|
| **Tribunal: STJ** | É onde a jurisprudência se consolida e onde as viragens de entendimento mais importam. Os acórdãos de uniformização de jurisprudência (AUJ) são prova externa de divergências reais, o que permite validar o sistema. |
| **Área: 4.ª Secção (trabalho)** | Casos do dia a dia (despedimento, férias, retribuição), vocabulário coerente, volume gerível (2204 acórdãos da 4.ª Secção recolhidos). |
| **Intervalo: 2010–2026** | Escolhido depois de contar o índice real (21 681 acórdãos, todas as secções, 2009–2026): cada ano tem pelo menos algumas dezenas de acórdãos laborais e 16 anos mostram bem as mudanças de entendimento. |

**Como se chegou a este subset.** Primeiro indexei toda a lista do STJ (barato: 219 páginas), contei por ano, e só depois escolhi o intervalo. Medi o peso da 4.ª Secção numa amostra aleatória de 150 acórdãos: 12 são da 4.ª Secção (~8%).

**Recolha responsável.** Pausa de 1,5 s mais variação aleatória entre pedidos, um pedido de cada vez, `User-Agent` com nome e email, cache local (nunca se pede a mesma página duas vezes), recuo em erros 429/5xx, leitura do `robots.txt` (o do DGSI devolve 404, ou seja, não existe e não declara restrições). Só se abrem os acórdãos candidatos, não o site todo.

## 2. Agrupar por tema — [FEITO]

1. **Ficha por acórdão (IA).** Um modelo lê o **sumário** (o resumo oficial do tribunal) e o excerto final da decisão e devolve JSON estrito: questão jurídica (sem nomes de partes), normas, solução em uma frase, tipo (mérito, admissibilidade, processual, outro) e uma **citação literal do sumário**. Um programa verifica que a citação existe mesmo no sumário; se não existir, pede uma correção e, se ainda falhar, guarda só o maior bloco literal (nunca texto inventado pelo modelo). Resultado: **370 fichas, todas com citação válida**, das quais 278 de mérito.
2. **Temas.** Agrupamento hierárquico (distância do cosseno) sobre TF-IDF da *questão jurídica* mais as normas citadas, só com acórdãos de mérito: **30 temas** (≥ 3 acórdãos) e 81 acórdãos sem tema. Os nomes legíveis foram escritos à mão a partir das questões de cada tema.
3. **Um tema curado à mão** para validar: *responsabilidade agravada do empregador em acidente de trabalho (art. 18.º da LAT)*, selecionado por expressão regular no sumário (47 acórdãos, 42 de mérito).

*Porquê assim:* o sumário é o campo mais denso e fiável; agrupar pela questão e não pelo texto todo evita juntar acórdãos só por partilharem factos. **Desvio do plano:** o plano era usar *embeddings* (sentence-transformers) e HDBSCAN, mas o HuggingFace está bloqueado no ambiente de trabalho; TF-IDF é mais simples, gratuito e deu temas legíveis. Revi à mão dois temas: "justa causa" está coerente; "subsídio de Natal e férias" mistura duas questões próximas.

## 3. Detetar divergências — [FEITO]

Princípio: **só se compara o que é comparável.** Duas decisões opostas sobre factos diferentes não são uma divergência.

- Um modelo faz de "juiz de pares": dados dois sumários (o mais antigo e o mais recente do mesmo tema), responde `mesma_solucao`, `solucao_oposta` ou `nao_comparavel`, com uma justificação e **uma citação literal de cada lado**, verificada por programa. `nao_comparavel` é uma resposta legítima e esperada.
- Para poupar pedidos compara-se cada acórdão com o seguinte, por data, dentro do tema.
- **Divergência** = soluções opostas que coexistem. **Viragem** = a orientação dominante muda de forma sustentada. **A viragem é calculada automaticamente** (`pipeline/viragens.py`): ligam-se acórdãos consecutivos por `mesma_solucao` (`nao_comparavel` corta a ligação); para cada par de soluções opostas contam-se os acórdãos ligados de cada lado e só se declara *viragem* se houver pelo menos 2 de cada lado (mínimo configurável); senão é *divergência isolada*. Resultado: a divergência de 2011 é **isolada** (2 acórdãos ligados do lado antigo, 1 do recente), por isso **não declaramos nenhuma viragem confirmada**; a amostra é pequena demais.

**Validação com um acórdão de uniformização (AUJ).** O AUJ n.º 6/2024 fixou o nexo de imputação da responsabilidade agravada do empregador. Comparei 33 pares válidos desse tema (2010–2026): **1 solução oposta, 7 mesma solução, 25 não comparáveis**. A divergência (2011-05-18 contra 2011-10-26) é sobre se é preciso provar a culpa do empregador quando se invoca a inobservância de regras de segurança, que é a questão que o AUJ veio resolver; depois do AUJ os acórdãos seguintes concordam. Nos 22 pares válidos de outros temas não houve nenhuma divergência (3 iguais, 19 não comparáveis).

**Honestidade sobre o resultado:** uma divergência em 55 pares válidos é pouco. Em 44 dos 55 a IA respondeu "não comparável" porque o tema é largo e junta subquestões; isso mostra que o cuidado de não forçar divergências funciona, mas também que a cobertura é baixa. Um método melhor compararia cada acórdão com os mais parecidos (não só o seguinte) e usaria temas mais estreitos; ficou por falta de pedidos (ver 4.3).

**Revisão manual de 25 veredictos do juiz de pares** (`revisao/CASOS.md`, respostas em `revisao/respostas.csv`). Escolheram-se ao acaso (semente fixa) 1 par de solução oposta, 8 de mesma solução e 16 de não comparável. O revisor (o autor, sem formação jurídica, apoiado por resumos em linguagem simples) respondeu *concordo*, *discordo* ou *não sei*:

| Veredicto da IA | Casos | Concordo | Discordo | Não sei |
|---|---|---|---|---|
| Solução oposta | 1 | 1 | 0 | 0 |
| Mesma solução | 8 | 7 | 0 | 1 |
| Não comparável | 16 | 10 | 5 | 1 |
| **Total** | **25** | **18** | **5** | **2** |

**Taxa de acerto: 18 de 23 (78%)** nos casos em que houve opinião (intervalo de confiança a 95% entre 58% e 90%, amplo porque são só 23 casos).

**Padrão de erro.** Os 5 desacordos são todos "não comparável" que o revisor considera comparáveis, por haver a mesma questão e a mesma conclusão (casos 5, 17, 18, 20 e 21). Exemplo (caso 18): os dois acórdãos de 2026 concluem que o empregador responde de forma agravada, mas a IA diz "não comparável" porque só um cita o AUJ n.º 6/2024. Não houve nenhum "mesma solução" nem "solução oposta" contestado. Em suma, **a IA é conservadora: perde divergências e igualdades (menor cobertura) em vez de inventar divergências (falsos positivos)**, o que é coerente com termos encontrado apenas uma divergência.

**Cautelas.** Só há 1 caso de solução oposta, por isso a fiabilidade desse veredicto, o mais importante, não se mede aqui; a revisão tem um só revisor, sem jurista; e o revisor viu a leitura do assistente, o que pode ter enviesado algumas respostas.

## 4. Limitações

**4.1 O filtro por descritores perde acórdãos laborais — [MEDIDO]**
A lista do DGSI não mostra a secção; só se vê abrindo cada acórdão. Abrir os 21 681 seria cerca de 15 horas de pedidos contínuos (estimativa: ~2,5 s por pedido) só para descobrir que ~92% não interessam, o que contraria o "recolha responsável" do enunciado e não cabe no prazo. Por isso a recolha foi em duas etapas:
1. **Pré-filtro por descritores** (palavras-chave laborais, `filtro_laboral.txt`): 1775 candidatos.
2. **Recolha por relatores:** cada juiz pertence a uma secção, por isso os 26 relatores com ≥ 4 acórdãos recolhidos e ≥ 85% deles na 4.ª Secção revelam acórdãos laborais com descritores genéricos. Recolheram-se mais 1059 acórdãos desses relatores (`relatores_4secao.txt`).

**Resultado:** 2972 acórdãos recolhidos (inclui uma amostra aleatória de 150). Pertencem à 4.ª Secção 2204; destes, **1820 decidem o mérito e são o conjunto de trabalho** (322 são de admissibilidade e 62 têm sumário curto). Há 17 anos com pelo menos 39 acórdãos cada (o mais baixo é 2016, com 39; 2020 passou de 18 para 52 depois dos relatores).

**Recall medido** numa amostra aleatória de 150 acórdãos (12 da 4.ª Secção): só descritores, 9/12 (75%); descritores mais relatores, 12/12.
- **Cautela:** 12 casos é muito pouco. Com 12 em 12, o limite inferior de um intervalo de confiança a 95% é cerca de 74%, ou seja, o recall real pode ser bem menor que 100%. Além disso, a lista de relatores foi construída com os dados recolhidos, incluindo essa amostra, pelo que o valor é ligeiramente otimista.
- O recall ficou acima do esperado, mas o número de acórdãos da 4.ª Secção (2204) é maior que a estimativa inicial de ~1700, que vinha de uma amostra de 12 casos.
- Ainda podem faltar acórdãos de relatores que julgam em várias secções, ou que apareceram poucas vezes nos dados.

*Consequência:* o sistema vê uma boa amostra da jurisprudência laboral, não toda; uma viragem pode ficar por detetar e os números não são contagens oficiais.

**4.2 Outras limitações**
- Um só tribunal e uma só área.
- Os modelos de IA erram: por isso as citações são verificadas por automático e uma amostra é revista à mão.
- Diferenças de factos podem parecer divergências.
- O índice do DGSI muda enquanto se recolhe (entram acórdãos novos no topo); duplicados são inofensivos porque cada acórdão tem um identificador único.
- Sumários de qualidade desigual; nem todos os acórdãos decidem o mérito (os de admissibilidade são excluídos).
- A classificação é automática e pode conter erros; a app terá um aviso visível.

**4.3 Custos e limites da IA**
- A extração e o juiz usaram a conta gratuita do OpenRouter, sem crédito: o `claude-haiku-5-5` serviu para 264 fichas (cerca de 0,11 USD no total) até a conta recusar (erro 402), e depois usou-se um modelo gratuito (`nvidia/nemotron-3-super-120b-a12b:free`, 106 fichas e todas as comparações), limitado a **50 pedidos por dia**. Por isso só **370 de 1820** acórdãos têm ficha (20%).
- Dois modelos diferentes fizeram as fichas. Numa amostra de 50 comparados, o tipo da decisão coincidiu em 46/50 e as citações foram 100% válidas nos dois.
- O agrupamento por TF-IDF é menos fino que os *embeddings* planeados.
- O marcador de AUJ do filtro (`auj=1`) apanha 53 acórdãos, mas só 2 são AUJ a sério; os restantes citam ou discutem uniformização. A validação usa os acórdãos que citam o AUJ n.º 6/2024.

**4.4 O que os resultados não permitem concluir**
- **A amostra de fichas não é aleatória.** Cerca de 316 foram escolhidas ao acaso, mas 42 foram escolhidas de propósito (o tema do AUJ n.º 6/2024, por expressão regular) e 12 vieram depois ao acaso. Por isso o tema do AUJ tem muito mais acórdãos do que os outros, e os números de divergências **não são uma taxa do tribunal inteiro**.
- **A validação assenta num só AUJ.** Encontrar a divergência que um AUJ resolveu é um bom sinal, mas é um caso; não permite falar de taxa de deteção.
- **O juiz de pares foi um modelo gratuito** (`nvidia/nemotron-3-super-120b-a12b:free`) e não o modelo mais forte previsto no plano (sem crédito). Pode errar mais; as citações verificadas limitam as invenções, não os erros de interpretação.
- **Sem jurista.** As classificações foram revistas por quem fez o projeto, que não tem formação jurídica, com ajuda da IA; não substitui a revisão de um jurista. A taxa de acerto da revisão está na secção 3.
- **"Mesma solução" por transitividade:** a viragem assume que acórdãos ligados em cadeia por "mesma solução" têm a mesma orientação; é uma aproximação.

**4.5 Melhorias futuras**
- Agrupar com *embeddings* multilingues (sentence-transformers) e HDBSCAN em vez de TF-IDF; requer acesso ao HuggingFace, bloqueado no ambiente de trabalho. Mudaria os temas, por isso obrigaria a refazer os nomes e as comparações.
- Fichas para os 1820 acórdãos (hoje 370) e comparar cada acórdão com os mais parecidos, não só com o seguinte; requer um modelo com crédito ou vários dias de quota gratuita.
- Usar um modelo mais forte como juiz de pares e rever uma amostra maior com um jurista.

