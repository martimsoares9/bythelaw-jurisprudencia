# Divergências de Jurisprudência (STJ, direito do trabalho)

Protótipo que agrega acórdãos do STJ **por tema** e procura **decisões divergentes ao longo do tempo**, isto é, onde e quando o tribunal mudou de entendimento sobre a mesma questão. Desafio ByTheLaw; fonte: [dgsi.pt](https://www.dgsi.pt). O enunciado completo está em `ENUNCIADO.md` e o contexto de trabalho em `CLAUDE.md`.

> **Estado:** em desenvolvimento. Feitas: recolha (em curso) e filtro. Por fazer: extração por IA, temas, comparação de pares, validação, app e deploy. A secção "Como correr" será completada à medida que as etapas ficarem prontas.

## Pequeno glossário (sem formação jurídica)

- **Jurisprudência:** o conjunto das decisões dos tribunais.
- **Acórdão:** decisão tomada por vários juízes. **Sumário:** o resumo oficial que o próprio tribunal escreve.
- **STJ (Supremo Tribunal de Justiça):** o tribunal mais alto em matérias civis, criminais e laborais. Está dividido em secções; a **4.ª Secção** (secção social) julga direito do trabalho.
- **Descritores:** palavras-chave que o tribunal atribui a cada acórdão.
- **Divergência:** dois acórdãos decidem a mesma questão de formas opostas. **Viragem:** o tribunal passa a decidir de forma diferente de modo duradouro.
- **AUJ (acórdão de uniformização de jurisprudência):** decisão do STJ que fixa uma orientação única para resolver uma divergência. Serve-nos de "prova externa" para validar o sistema.
- **Revista excecional / Formação:** fase em que o tribunal decide só se o recurso é admitido, não o mérito. Estes acórdãos são excluídos.

## Subset escolhido

**STJ, 4.ª Secção (direito do trabalho), 2010 a 2026.**

- **Tribunal:** o STJ é onde a jurisprudência se consolida e as viragens de entendimento mais importam; os AUJ dão prova externa de divergências reais, o que permite validar.
- **Área:** direito do trabalho (despedimento, férias, retribuição, acidentes de trabalho): casos do dia a dia, vocabulário coerente, volume gerível (~1700 acórdãos estimados no período).
- **Intervalo:** 2010–2026. Cada ano tem pelo menos algumas dezenas de acórdãos laborais e 16 anos mostram bem as mudanças de entendimento. Os dados do DGSI chegam a setembro de 2026.

Contagem real do índice (todas as secções do STJ): 21 681 acórdãos de 2009 a 2026. Cerca de 8% (12 em 150, numa amostra aleatória) são da 4.ª Secção.

## O que foi feito até agora

1. **Scraper (`scraper.py`).** Lê o DGSI e guarda numa base SQLite (`data/acordaos.db`). Duas fases:
   - `indexar`: percorre a vista "Por Ano" (219 páginas) e guarda, para cada acórdão, data, processo, relator e descritores (tabela `lista`).
   - `detalhes`: abre só os acórdãos escolhidos e guarda secção, sumário e texto (tabela `acordaos`).
2. **Decisão do subset com números.** Contagem por ano com `python scraper.py stats`.
3. **Medição do filtro (amostra de recall).** `detalhes --amostra 150` recolhe 150 acórdãos aleatórios (semente fixa, reprodutível) para ver quantos são da 4.ª Secção e quantos o filtro apanha.
4. **Recolha dos candidatos.** Filtro por descritores laborais (`filtro_laboral.txt`): 1775 candidatos em 2010–2026.
5. **Filtro (`pipeline/filtrar.py`).** Fica com acórdãos da 4.ª Secção que decidem o mérito; exclui os de admissibilidade e os de sumário curto (menos de 200 caracteres); marca os AUJ.

## Recolha responsável

- Lê o `robots.txt` (o do DGSI devolve 404, ou seja, não existe e não declara restrições) e recusa o que for proibido.
- Pausa de 1,5 s mais variação aleatória entre pedidos, um pedido de cada vez.
- `User-Agent` identificado com o nome e o email do autor, para o site nos poder contactar.
- Cache local do HTML (`cache/`): nunca se pede a mesma página duas vezes; retoma de onde parou.
- Recuo (espera crescente) em erros 429/5xx.
- Só se abrem os acórdãos que interessam (ver limitação abaixo), em vez de copiar o site todo.

## Limitação principal: o filtro por descritores perde acórdãos laborais

**O problema.** A lista do DGSI mostra data, processo, relator e descritores, mas **não diz a secção**. A secção só aparece dentro de cada acórdão. Para saber quais são da 4.ª Secção temos de os abrir, ou adivinhar pela lista.

**O que fizemos.** Adivinhamos pelos descritores: só abrimos os acórdãos cujos descritores têm palavras laborais ("despedimento", "trabalhador", "retribuição"…). Isto poupa pedidos mas tem dois defeitos:

- **Falsos negativos (perde acórdãos laborais).** Alguns acórdãos da 4.ª Secção têm descritores genéricos ("revista excecional", "interpretação das sentenças") ou laborais que não previmos. Na amostra de 150 acórdãos, o filtro inicial apanhava 8 dos 12 da 4.ª Secção (~67%). Depois de o alargar, 9 em 12 (75%). A amostra é pequena, por isso o valor real é incerto.
- **Falsos positivos (apanha o que não interessa).** Alguns acórdãos de outras secções também têm palavras laborais; são descartados depois, quando se vê a secção no acórdão.

**Porque não o resolvemos por completo.**

- A solução "perfeita" seria abrir todos os 21 681 acórdãos e ver a secção de cada um. Com uma pausa de 1,5 s mais o tempo de resposta (~2,5 s por pedido) seriam cerca de **15 horas de pedidos contínuos** ao DGSI, só para descobrir que cerca de 92% não interessam. Isso contraria o requisito do enunciado de recolher "de forma responsável, sem sobrecarregar o site", e não cabe no prazo de 12 dias.
- A lista não tem outro campo que identifique a secção, por isso qualquer pré-filtro é uma aproximação.
- Há ainda o risco de "polir demais": o enunciado valoriza rapidez e um protótipo funcional, e o filtro apanha a maioria do que interessa.

**O que ainda vamos fazer para melhorar (planeado, ainda não feito).** Depois de recolhidos os candidatos, usar os **relatores**: cada juiz do STJ pertence a uma secção, por isso quem escreve quase só na 4.ª Secção revela os acórdãos laborais que o filtro por descritores perdeu. Recolhe-se então os restantes acórdãos desses relatores (poucas centenas de pedidos). Isto sobe o recall sem abrir tudo, mas **continua a não chegar a 100%**, e o recall final será medido e escrito aqui.

**Consequência para os resultados.** O sistema vê uma amostra de bom tamanho da jurisprudência laboral, não toda. Uma "viragem" pode ficar por detetar, ou aparecer com menos acórdãos do que existem, porque faltam alguns. Os números do sistema não devem ser lidos como contagens oficiais.

## Outras limitações (a detalhar na nota de decisões)

Um só tribunal e uma só área; erros do modelo de IA (por isso as citações serão verificadas e uma amostra revista à mão); diferenças de factos podem parecer divergências; o índice do DGSI muda enquanto se recolhe (entram acórdãos novos no topo); sumários de qualidade desigual.

## Como correr (recolha e filtro)

Requer Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install requests beautifulsoup4 lxml

# 1) Indexar a lista (219 páginas, ~10 min). Testar primeiro com --max-paginas 3
python scraper.py indexar --ate-ano 2010
python scraper.py stats --descritores @filtro_laboral.txt     # contagens por ano

# 2) Abrir os acórdãos candidatos (~1 h, retomável)
python scraper.py detalhes --ano-min 2010 --ano-max 2026 --descritores @filtro_laboral.txt --limite 100000

# 3) Filtrar: 4.ª Secção + mérito
python pipeline/filtrar.py            # contagens
python pipeline/filtrar.py exemplos   # 5 exemplos
python pipeline/filtrar.py relatores  # relatores da 4.ª Secção
```

Antes de recolher, edita a constante `CONTACTO` no topo de `scraper.py` com o teu nome e email.

## Uso de IA

Ver `AI_USAGE.md`.
