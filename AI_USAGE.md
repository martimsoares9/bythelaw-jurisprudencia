Sempre que usares a IA para algo relevante, acrescentas uma linha à tabela do diário, com cinco coisas:
a data;
a fase (setup, scraper, temas, divergências, interface...);
o que pediste;
se funcionou;
o que tiveste de corrigir ou o que aprendeste.

# Como usei IA neste projeto

## Ferramentas

- **Claude (claude.ai):** planeamento, explicação do domínio jurídico, geração de código, resolução de erros.
- _(acrescentar aqui outras: GitHub Copilot, Cursor, Claude Code, modelos de embeddings, API do Claude no pipeline, etc.)_

## Fluxo de trabalho (resumo)

_(Preencher no fim, em 4 a 6 linhas: como organizaste o trabalho com a IA. Exemplo: "Usei o Claude para planear e gerar o código de cada fase, testava localmente, colava os erros de volta e iterava. Dentro do pipeline, usei a API do Claude para extrair a questão jurídica e classificar divergências.")_

## Diário (uma linha por pedido relevante)

| Data | Fase | O que pedi | Funcionou? | O que corrigi / aprendi |
|---|---|---|---|---|
| 2026-09-30 | Planeamento | Plano por fases para o desafio e escolha de subset | Sim | Decidi o subset (STJ, secção social) com o critério explicado no README |
| 2026-09-30 | Domínio | Explicação de jurisprudência, acórdão, sumário, descritores (não tenho formação jurídica) | Sim | Percebi que o sumário e os descritores são os campos mais úteis para agrupar por tema |
| 2026-09-30 | Setup | Erro ao ativar o ambiente virtual no PowerShell | Sim | A pasta `.venv` ainda não tinha sido criada; faltava correr `python -m venv .venv` |
| 2026-09-30 | Setup | Configuração do repositório no GitHub | Sim | Deixar README, .gitignore e licença desligados para evitar conflitos no primeiro push |
| 2026-10-09 | Scraper | Correr o indexar contra o DGSI (Claude Code) | Parcial | As datas vinham vazias: o servidor devolve mm/dd/aaaa a pedidos de fora de Portugal e o parser só aceitava dd-mm-aaaa. Percebi-o ao ver que as datas "não estavam por ordem" |
| 2026-10-09 | Setup | Commit da base de dados e cache | Não | O `.gitignore` não acabava em newline e a linha acrescentada colou-se a `cache/`; a base entrou no git por engano. Corrigido e removido do controlo de versões |
| 2026-10-09 | Subset | Medir o recall do filtro por descritores (amostra de 150) | Sim | O filtro inicial apanhava 8 de 12 acórdãos da 4.ª Secção; alargado passa a 9 de 12. Amostra pequena, valor incerto |
| 2026-10-10 | Scraper | Recolha dos 1775 candidatos em segundo plano | Parcial | A meio, o proxy do ambiente mudou de porta e a recolha parou com erros de rede; reiniciada (é retomável por causa da cache) |

## O que funcionou bem

- _(preencher ao longo do projeto)_

## O que não funcionou / limitações da IA

- _(preencher ao longo do projeto: erros do LLM, alucinações, código que teve de ser reescrito, custos, etc.)_

## Validação do que a IA produziu

- _(preencher na fase das divergências: quantos casos revi à mão, taxa de acerto, exemplos de erros)_
