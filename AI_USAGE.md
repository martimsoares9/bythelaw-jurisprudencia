Sempre que usares a IA para algo relevante, acrescentas uma linha à tabela do diário, com cinco coisas:
a data;
a fase (setup, scraper, temas, divergências, interface...);
o que pediste;
se funcionou;
o que tiveste de corrigir ou o que aprendeste.

# Como usei IA neste projeto

## Ferramentas

- **Claude (claude.ai):** planeamento, explicação do domínio jurídico (acórdão, sumário, descritores), geração do scraper inicial, resolução de erros.
- **Claude Code (agente na cloud, sobre este repositório):** corre o scraper contra o DGSI, corrige bugs, escreve o pipeline, faz commits e push. Os commits levam `Co-Authored-By: Claude`.
- **Previstos (por usar):** API da Anthropic no pipeline (modelo barato para extração, modelo mais forte para o juiz de pares), `sentence-transformers` e HDBSCAN para os temas. **[POR FAZER — atualizar com os modelos realmente usados]**

## Fluxo de trabalho (resumo)

Planeei o projeto com o Claude (claude.ai) e deixei tudo escrito no `CLAUDE.md`, que serve de contexto para o Claude Code, com o que está **decidido**, **proposto** e **em aberto**. Depois trabalho por fases pequenas e testáveis: o Claude Code corre o passo (recolher, contar, filtrar), mostra-me números e exemplos, e **eu decido** antes de avançar (por exemplo, aprovei eu o subset depois de ver as contagens por ano). No fim de cada fase atualiza-se o `CLAUDE.md`, faz-se commit e push. Dentro do pipeline, a API do Claude será usada para extrair a questão jurídica e classificar divergências, sempre com citações verificadas por automático. **[completar no fim com o fluxo da extração e do juiz]**

## Diário (uma linha por pedido relevante)

| Data | Fase | O que pedi | Funcionou? | O que corrigi / aprendi |
|---|---|---|---|---|
| 2026-09-30 | Planeamento | Plano por fases para o desafio e escolha de subset | Sim | Decidi o subset (STJ, secção social) com o critério explicado no README |
| 2026-09-30 | Domínio | Explicação de jurisprudência, acórdão, sumário, descritores (não tenho formação jurídica) | Sim | Percebi que o sumário e os descritores são os campos mais úteis para agrupar por tema |
| 2026-09-30 | Setup | Erro ao ativar o ambiente virtual no PowerShell | Sim | A pasta `.venv` ainda não tinha sido criada; faltava correr `python -m venv .venv` |
| 2026-09-30 | Setup | Configuração do repositório no GitHub | Sim | Deixar README, .gitignore e licença desligados para evitar conflitos no primeiro push |
| 2026-10-09 | Scraper | Correr o indexar contra o DGSI (Claude Code) | Parcial | Datas vazias; ver "O que não funcionou" |
| 2026-10-09 | Setup | Commit da base de dados e cache | Não | `.gitignore` partido; ver "O que não funcionou" |
| 2026-10-09 | Subset | Medir o recall do filtro por descritores (amostra de 150) | Sim | Recall 8/12, depois 9/12; ver `NOTA_DECISOES.md` 4.1 |
| 2026-10-10 | Scraper | Recolha dos 1775 candidatos em segundo plano | Parcial | Parou por mudança de proxy; reiniciada; ver "O que não funcionou" |
| 2026-10-10 | Subset | Recolher também por relatores da 4.ª Secção (Claude Code) | Sim | Recall na amostra 9/12 -> 12/12 (amostra pequena); ver `NOTA_DECISOES.md` 4.1 |
| 2026-10-10 | Extração | Trocar a chave do OpenRouter e repetir o `ping` + amostra de 50 (Claude Code) | Não | A chave nova não chegou ao contentor (nenhuma variável `OPENROUTER_*`/`LLM_*` definida, sem `.env`); `ping` parou com "Sem chave". Não gastei nada. Ver "O que não funcionou" |

## O que funcionou bem

- **Decidir com números:** indexar tudo (barato) e contar por ano antes de fixar o intervalo; medir o filtro com uma amostra aleatória em vez de supor que funcionava.
- **Testar o parser com HTML real** (`testsexemplos/`) antes de ir à rede.
- **Recolha retomável** (cache + chave primária por acórdão): quando a ligação falhou, bastou reiniciar sem repetir pedidos.
- **Trabalho por fases com paragem para aprovação**, o que apanhou o problema do recall antes de gastar uma hora a recolher o filtro errado.

- **Usar os relatores como sinal da secção** subiu o recall na amostra de 9/12 para 12/12, uma ideia que o filtro de descritores sozinho não tinha.

## O que não funcionou / limitações da IA

- **Datas vazias:** o scraper "testado offline" falhou na rede real. O DGSI devolve as datas em `mm/dd/aaaa` a pedidos de fora de Portugal; o parser só aceitava `dd-mm-aaaa`. O teste offline com HTML copiado de um browser em Portugal não revelou isto. Detetei-o porque as datas apareciam desordenadas. Lição: testar sempre contra a rede real e olhar para os dados, não só para "correu sem erros".
- **Ambiente sem acesso ao DGSI:** a cloud começou por bloquear `dgsi.pt` (403), depois deu timeout durante dias (o site também esteve em baixo, como confirmaste), e só depois respondeu. Perdi tempo; a IA não consegue contornar uma política de rede e deve dizê-lo em vez de insistir.
- **`.gitignore` partido:** o ficheiro original não terminava com newline, a linha que acrescentei colou-se a `cache/` e a base de dados foi parar ao git. Detetado por um hook de verificação; corrigido e removida do controlo de versões (continua no histórico, é pequena).
- **Recolha interrompida:** a meio, o proxy do ambiente mudou de porta e o processo em segundo plano ficou a falhar com erros de rede; reiniciei. Ao reiniciar, um `pkill` apanhou o meu próprio shell (erro meu), tive de relançar.
- **Instruções contraditórias:** o `CLAUDE.md` mandava trabalhar no `main` mas a sessão estava ligada a outro branch; só fiz push para o `main` depois de o confirmares explicitamente.
- **Filtro de descritores com recall baixo (~67–75% na amostra):** a IA propôs um filtro razoável, mas só a medição mostrou que perdia 1 em cada 4 acórdãos laborais. É uma limitação assumida (ver `NOTA_DECISOES.md`, 4.1).
- **Estimativas, não medições:** os ~15 h de recolha completa e os ~1700 acórdãos da 4.ª Secção são contas minhas a partir de amostras pequenas.
- **Extração devolvia vazio (Fase 3):** na primeira corrida de 50, 43 respostas vieram vazias ("JSON inválido"). O modelo `claude-haiku-5-5` (via OpenRouter) gastava os 700 tokens de saída a "raciocinar" antes de escrever. Custou ~0,05 USD de chamadas inúteis. Corrigi desligando o raciocínio (`reasoning: {enabled: false}`) e subindo o limite para 1000 tokens: ficou mais barato e mais rápido (0,018 USD, 34 s para 50 acórdãos).
- **Chave não chegou à sessão (2026-10-10):** depois de trocares a `OPENROUTER_API_KEY` no ambiente, o contentor desta sessão continuou sem a variável (as variáveis do ambiente só são lidas quando a sessão começa, por isso uma sessão já aberta não as vê). Em vez de inventar resultados, parei: não foi possível confirmar o plano, os limites nem se o `claude-haiku-5-5` responde.
- **Chave ausente outra vez (2026-10-10, 2.ª tentativa):** o contentor continua sem `OPENROUTER_API_KEY`/`LLM_*` e sem `.env` (verificado só pelos nomes das variáveis, sem imprimir valores). `ping` e a amostra de 50 não correram, gastei 0 USD. Também não consigo identificar os 2 acórdãos mal classificados: a tabela `extracoes` e a cache `cache/llm/` da corrida anterior não foram guardadas (a base em `dados/acordaos.db.gz` só tem `lista`, `acordaos`, `filtrados`). Lição: a variável tem de estar definida no ambiente *antes* de a sessão começar.
- **"Válido" não quer dizer "correto":** a validação automática só prova que a citação (`trecho`) existe no sumário. Na amostra de 50, 100% passaram, mas ao ler os resultados vi 2 acórdãos de mérito classificados como `admissibilidade` (2017-11-09 e 2021-04-28). A taxa de acerto real só se mede com revisão manual (Fase 5).
- **Limites da chave gratuita (Fase 3):** o `claude-haiku-5-5` funcionou até a conta chegar a ~0,21 USD de uso e depois devolveu 402 (sem crédito). Os modelos gratuitos têm um limite de **50 pedidos por dia** (1000 só com 10 USD de crédito). Resultado: **316 de 1820 acórdãos extraídos** (264 com o Haiku, 52 com `nvidia/nemotron-3-super-120b-a12b:free`; 100% com citação válida). Nenhuma cobrança ao utilizador. Perdi bastante tempo a perceber que a chave só chega a uma sessão nova e que o `.env` do computador não chega ao contentor.
- **Embeddings bloqueados:** o plano era `sentence-transformers`, mas o HuggingFace dá 403 no ambiente. Troquei por TF-IDF sobre a questão jurídica + normas (scikit-learn), que é gratuito. Revi 2 temas à mão: o de "justa causa de despedimento" (12 acórdãos) está coerente; o de "subsídio de Natal/férias" mistura duas questões próximas.

## Validação do que a IA produziu

- **Já feito:** amostra aleatória de 150 acórdãos para medir o recall do filtro (resultado acima).
- **Extração por IA, amostra de 50 (2026-10-10):** 50/50 com citação literal válida; 38 mérito, 9 processual, 3 admissibilidade; confiança média 0,86; 10 sem normas; custo 0,00036 USD/acórdão (≈ 0,66 USD para os 1820). **[POR FAZER]** revisão manual dos 50 para medir o acerto real.
- **[POR FAZER]** Juiz de pares: teste com AUJ como verdade-terreno e 25 casos revistos à mão, com taxa de acerto e exemplos de erros.
