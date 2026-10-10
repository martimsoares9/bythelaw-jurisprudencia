# Guia do projeto em linguagem simples

Este ficheiro é para **perceberes o que foi feito e o que vem a seguir**, sem teres de ler o código. Atualiza-se no fim de cada fase (secção 4). Para os detalhes técnicos: `README.md`, `NOTA_DECISOES.md`, `AI_USAGE.md` e `CLAUDE.md`.

## 1. A ideia em duas frases

Os tribunais portugueses publicam milhares de decisões (acórdãos). O projeto **junta as decisões que tratam do mesmo problema** (por exemplo, "pode a empresa despedir quem faltou X dias?") e **mostra quando e onde o tribunal mudou de opinião** sobre esse problema ao longo dos anos.

Escolhemos o **Supremo Tribunal de Justiça (STJ)**, a **4.ª Secção** (a que trata de direito do trabalho) e os anos **2010 a 2026**. O porquê está em `NOTA_DECISOES.md`.

## 2. O que já foi feito (e como)

**Passo 1 — Preparar o programa que lê o site (o scraper).**
É um programa que abre as páginas do DGSI (a base oficial de acórdãos) e copia os dados para um ficheiro no computador (`data/acordaos.db`). Faz isto com boas maneiras: espera 1,5 segundos entre pedidos, diz quem somos (o teu nome e email), e guarda cada página lida para nunca a pedir duas vezes. Assim não sobrecarrega o site, como o enunciado exige.

**Passo 2 — Fazer a lista de todos os acórdãos.**
Percorreu as 219 páginas de lista do STJ e guardou 21 681 acórdãos, mas só com a data, o número do processo, o juiz-relator e as palavras-chave. Ainda sem o texto.
- *Erro que apareceu:* o site devolvia as datas em formato americano (mês/dia) e o programa não as percebia, ficavam vazias. Corrigido.

**Passo 3 — Escolher o subset com números.**
Contámos os acórdãos por ano e propus o subset. Tu aprovaste. (Uma decisão tomada com dados, e não a olho.)

**Passo 4 — Medir se o meu filtro é bom.**
A lista não diz a que secção pertence cada acórdão; isso só se vê ao abrir o acórdão. Abrir os 21 681 levaria cerca de 15 horas de pedidos ao site, e a maioria nem é de trabalho. Por isso usei um atalho: só abro os acórdãos cujas palavras-chave parecem de trabalho ("despedimento", "trabalhador", "retribuição"…).
O atalho não é perfeito. Testei em 150 acórdãos ao acaso: dos 12 que eram da 4.ª Secção, o filtro encontrou 8; depois de o melhorar, 9. Ou seja, **falha cerca de 1 em cada 4**. Isto é uma limitação que vamos assumir e explicar na nota.

**Passo 5 — Abrir os acórdãos candidatos.**
Dos 21 681, o filtro escolheu 1775. O programa abre cada um e copia o sumário (o resumo oficial que o próprio tribunal escreve), a secção e o texto. Demora cerca de 1 hora e está a correr.
- *Erro que apareceu:* a meio, a ligação à internet do computador onde trabalho mudou e a recolha parou. Reiniciei; como o programa guarda o que já fez, continuou de onde estava.

**Passo 6 — Escrever o filtro final (`pipeline/filtrar.py`).**
Dos acórdãos recolhidos, fica só quem é da 4.ª Secção e **decidiu o fundo da questão**. Tira os acórdãos que só decidem se um recurso pode ou não ser aceite (não dizem quem tem razão) e os de sumário demasiado curto. Marca também os "acórdãos de uniformização", que são decisões em que o STJ resolve uma divergência entre os seus próprios acórdãos. Esses vão servir-nos de resposta certa para testar o sistema.

**Passo 7 — Documentar e guardar.**
README com o mapa dos 5 entregáveis do enunciado, `NOTA_DECISOES.md`, `AI_USAGE.md` (inclui as falhas), cópia da base de dados no repositório e o plano das fases no `CLAUDE.md`.

## 3. O que falta fazer, fase a fase

| Fase | O que acontece, em simples | O que vês no fim | O que preciso de ti |
|---|---|---|---|
| **2. Fechar a recolha** | Acaba de abrir os candidatos. Depois procuro os juízes que quase só escrevem na 4.ª Secção e abro também os acórdãos deles que o filtro perdeu. Guardo a base final. | 5 exemplos de acórdãos e o número final de acórdãos | Esperar |
| **3. A IA lê os sumários** | Para cada acórdão, o Claude lê o sumário e extrai: *qual é a questão*, *que lei se aplica* e *qual foi a decisão* (uma frase), mais uma citação do sumário que prova isso. Eu confirmo por programa que a citação existe mesmo no texto; se não existir, a resposta é recusada (assim apanho invenções da IA). Começa com 50 acórdãos. | Os resultados desses 50, para decidirmos se a qualidade chega antes de gastar mais | A chave da API da Anthropic num ficheiro `.env`; rever os resultados |
| **4. Temas e comparação** | Agrupo os acórdãos que tratam da mesma questão (tema). Dentro de cada tema, o Claude compara pares de acórdãos de datas diferentes e responde: *mesma solução*, *solução oposta* ou *não comparável* (factos diferentes). "Não comparável" é uma resposta normal e importante: duas decisões opostas sobre casos diferentes **não** são uma divergência. Daí sai a "viragem": quando a maioria das decisões antes de uma data difere da maioria depois dela. | 3 temas e 3 pares classificados, incluindo um "não comparável" | Verificar se os temas fazem sentido |
| **5. Validar** | Teste de verdade: (a) o sistema encontra as divergências que os acórdãos de uniformização já confirmam? (b) tu e eu revemos à mão 25 classificações e contamos quantas estão certas. | A taxa de acerto e exemplos de erros | Rever os 25 casos (os termos jurídicos explico-te eu) |
| **6. A aplicação** | Uma página web: escolhes um tema, vês os acórdãos numa linha do tempo com a viragem assinalada, dois acórdãos lado a lado com a citação, e o link para o original. Tem um aviso visível de que a classificação é automática e pode ter erros. A página não chama a IA nem o DGSI; lê só um ficheiro já preparado. Publica-se cedo, não no fim. | O link da aplicação | Criar a conta no serviço de alojamento (Streamlit Community Cloud ou Hugging Face) |
| **7. Entrega** | Fechar o README ("como correr"), a nota de decisões, a descrição do uso de IA e o vídeo de demonstração com a tua narração. | Os 5 entregáveis completos | Gravar o vídeo |

## 4. Calendário (6 dias de trabalho a partir de 2026-10-10)

> Confirma a data limite exata de entrega: o enunciado diz "12 dias a contar de agora" e o email original tem a data.

| Dia | Foco |
|---|---|
| 1 (10-10) | Fase 2: fechar a recolha |
| 2 | Fase 3: extração por IA (50, depois todos) |
| 3 | Fase 4: temas e comparação de pares |
| 4 | Fase 5: validação; começar a app |
| 5 | Fase 6: app e deploy |
| 6 | Fase 7: README, nota, uso de IA, vídeo |

Se um dia derrapar, o que se corta primeiro é o polimento da app, **nunca** a validação nem a documentação, porque o enunciado pede que fundamentes as decisões.

## 5. Diário do guia (atualizar no fim de cada fase)

| Fase | Fechada em | O que mudou desde a anterior | Surpresas / erros |
|---|---|---|---|
| 1 | 2026-10-10 | Índice completo e subset aprovado | Datas em formato americano |
| 2 | *em curso* | | A recolha parou uma vez por mudança de ligação à internet; reiniciada |

## 6. Palavras que vão aparecer

- **Acórdão:** decisão tomada por vários juízes. **Sumário:** o seu resumo oficial.
- **Relator:** o juiz que escreve o acórdão.
- **Descritores:** palavras-chave de cada acórdão.
- **Divergência:** dois acórdãos decidem a mesma questão de formas opostas.
- **Viragem:** o tribunal muda de opinião de forma duradoura.
- **AUJ (acórdão de uniformização de jurisprudência):** o STJ fixa uma orientação única para acabar com uma divergência.
- **Revista excecional:** recurso especial; a decisão sobre se é aceite não decide quem tem razão.
- **Recall:** de todos os acórdãos que interessavam, que percentagem o filtro encontrou (aqui, ~75%).
- **Cache:** cópia guardada para não repetir um pedido, seja ao site ou à IA (poupa tempo e dinheiro).
- **Embedding:** forma de transformar um texto em números para saber que textos se parecem.
