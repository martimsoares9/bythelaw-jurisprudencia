# Divergências de Jurisprudência (STJ, direito do trabalho)

Protótipo que agrega acórdãos do STJ **por tema** e procura **decisões divergentes ao longo do tempo** (onde e quando o tribunal mudou de entendimento). Desafio ByTheLaw; fonte: [dgsi.pt](https://www.dgsi.pt). Subset: STJ, 4.ª Secção, 2010–2026.

> **Estado:** em desenvolvimento (recolha e filtro feitos, 1820 acórdãos de trabalho; faltam extração por IA, temas, comparação, validação, app e deploy).

## Entregáveis do enunciado e onde estão

| # | O enunciado pede | Onde está | Estado |
|---|---|---|---|
| 1 | Link da aplicação em produção | *(link a acrescentar aqui)* | Por fazer |
| 2 | Repositório com README que explique como correr | Este ficheiro, secção "Como correr" | Parcial (recolha e filtro) |
| 3 | Nota curta de decisões | [`NOTA_DECISOES.md`](NOTA_DECISOES.md) | Subset e limitações escritos; temas e divergências por fazer |
| 4 | Descrição do uso de IA | [`AI_USAGE.md`](AI_USAGE.md) | Em curso |
| 5 | Vídeo de demonstração com narração | *(link a acrescentar aqui)* | Por fazer |

## Mapa de ficheiros (o que cada um contém)

| Ficheiro | O que contém |
|---|---|
| `README.md` | Este mapa, os entregáveis e como correr o projeto |
| `NOTA_DECISOES.md` | **Porquê** de cada decisão: subset, recolha responsável, método de temas e de divergências, limitações |
| `AI_USAGE.md` | Como se usou a IA: ferramentas, fluxo, diário, o que funcionou e o que falhou, validação |
| `GUIA.md` | Guia em linguagem simples: o que foi feito, o que falta, calendário, glossário (para o autor perceber o trabalho) |
| `CLAUDE.md` | Instruções e contexto técnico para o assistente de IA (Claude Code); regras de trabalho e estado das fases |
| `ENUNCIADO.md` | O enunciado original do desafio |
| `scraper.py` | Programa que lê o DGSI e guarda numa base SQLite (`indexar`, `detalhes`, `stats`) |
| `filtro_laboral.txt` | Palavras-chave laborais usadas para escolher que acórdãos abrir (lido pelo scraper) |
| `relatores_4secao.txt` | Relatores que julgam quase só na 4.ª Secção, usados na 2.ª etapa da recolha |
| `pipeline/filtrar.py` | Etapa 2: fica só com a 4.ª Secção e decisões de mérito; marca os AUJ |
| `testsexemplos/` | HTML de exemplo (um acórdão e uma lista) para testar o parser sem rede |
| `dados/acordaos.db.gz` | Cópia comprimida da base de dados recolhida |
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
