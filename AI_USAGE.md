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

## O que funcionou bem

- **Decidir com números:** indexar tudo (barato) e contar por ano antes de fixar o intervalo; medir o filtro com uma amostra aleatória em vez de supor que funcionava.
- **Testar o parser com HTML real** (`testsexemplos/`) antes de ir à rede.
- **Recolha retomável** (cache + chave primária por acórdão): quando a ligação falhou, bastou reiniciar sem repetir pedidos.
- **Trabalho por fases com paragem para aprovação**, o que apanhou o problema do recall antes de gastar uma hora a recolher o filtro errado.

## O que não funcionou / limitações da IA

- **Datas vazias:** o scraper "testado offline" falhou na rede real. O DGSI devolve as datas em `mm/dd/aaaa` a pedidos de fora de Portugal; o parser só aceitava `dd-mm-aaaa`. O teste offline com HTML copiado de um browser em Portugal não revelou isto. Detetei-o porque as datas apareciam desordenadas. Lição: testar sempre contra a rede real e olhar para os dados, não só para "correu sem erros".
- **Ambiente sem acesso ao DGSI:** a cloud começou por bloquear `dgsi.pt` (403), depois deu timeout durante dias (o site também esteve em baixo, como confirmaste), e só depois respondeu. Perdi tempo; a IA não consegue contornar uma política de rede e deve dizê-lo em vez de insistir.
- **`.gitignore` partido:** o ficheiro original não terminava com newline, a linha que acrescentei colou-se a `cache/` e a base de dados foi parar ao git. Detetado por um hook de verificação; corrigido e removida do controlo de versões (continua no histórico, é pequena).
- **Recolha interrompida:** a meio, o proxy do ambiente mudou de porta e o processo em segundo plano ficou a falhar com erros de rede; reiniciei. Ao reiniciar, um `pkill` apanhou o meu próprio shell (erro meu), tive de relançar.
- **Instruções contraditórias:** o `CLAUDE.md` mandava trabalhar no `main` mas a sessão estava ligada a outro branch; só fiz push para o `main` depois de o confirmares explicitamente.
- **Filtro de descritores com recall baixo (~67–75% na amostra):** a IA propôs um filtro razoável, mas só a medição mostrou que perdia 1 em cada 4 acórdãos laborais. É uma limitação assumida (ver `NOTA_DECISOES.md`, 4.1).
- **Estimativas, não medições:** os ~15 h de recolha completa e os ~1700 acórdãos da 4.ª Secção são contas minhas a partir de amostras pequenas.

## Validação do que a IA produziu

- **Já feito:** amostra aleatória de 150 acórdãos para medir o recall do filtro (resultado acima).
- **[POR FAZER]** Extração por IA: % de respostas com citação válida, 50 acórdãos revistos.
- **[POR FAZER]** Juiz de pares: teste com AUJ como verdade-terreno e 25 casos revistos à mão, com taxa de acerto e exemplos de erros.
