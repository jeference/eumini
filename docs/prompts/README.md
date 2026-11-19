# Teste dos prompts por categoria

| | |
|---|---|
| **Data** | 19/11/2026 |
| **Objetivo** | Escrever o prompt de cada categoria (RN-30, RN-35) no estilo único, o antigo "Pixar", e ver se a imagem gerada mantém a categoria da foto e fica imprimível |
| **Resultado** | Com o bloco de categoria, as 18 imagens mantiveram a categoria (classificadas pelo Jev). O prompt atual, sem o bloco, manteve 11 de 18: perdeu a segunda figura em 7 dos 8 casais e pessoas com pet |

## Como foi feito

- **Casos:** 18 fotos em [`casos.json`](casos.json). São 6 de pessoa, 3 de pet, 4 de casal e 5 de pessoa com pet.
  - Parte delas vem de [`../classificador/imagens`](../classificador/imagens), e as novas estão em [`imagens/`](imagens), todas do Wikimedia Commons, com crédito.
  - Nenhuma é de pessoa privada.
- **Geração:**
  - Feita na Runware, como o worker faz: GPT Image 2 e, se ele falhar, Nano Banana Pro.
  - Uma imagem por caso, a partir da foto, sem pedido do cliente.
- **Classificação:** cada imagem gerada passa pelo Jev, com as perguntas de versão do [teste do classificador](../classificador/README.md).
- **Para rodar de novo:** `apps/backend/.venv/Scripts/python.exe -I docs/prompts/teste_prompts.py <rodada> [id ...]`. A comparação sai de `docs/prompts/comparar.py`.

## Rodadas

| Rodada | Prompt | Categoria mantida | Custo |
|---|---|---|---|
| r0 | O prompt Pixar atual, igual para todas as categorias | 11 de 18 | US$ 0,29 |
| r1 | Estilo + bloco da categoria + regras de impressão, sem base | 18 de 18 | US$ 0,41 |
| r2 | Igual à r1, com base redonda | 18 de 18 | US$ 0,31 |
| **r3** | **Igual à r1, com plano de cores por categoria e base na cor escura da figura** | **18 de 18** | **US$ 0,43** |

As imagens de cada rodada estão em `resultados/<rodada>/` (com `folha.jpg`). A comparação lado a lado, com foto, r0, r1, r2 e r3, está em [`resultados/comparativo.jpg`](resultados/comparativo.jpg).

O texto das camadas está em [`teste_prompts.py`](teste_prompts.py):
- **Estilo:** `ESTILO`, a partir de `_PIXAR_LOOK`.
- **Categoria:** `CATEGORIA`.
- **Impressão:** `IMPRESSAO`.
- **Plano de cores:** `CORES`.
- **Base:** `BASE_ESCURA`.

## O que o teste mostrou

- **O bloco de categoria é necessário.** O prompt atual diz "o assunto principal", e o modelo escolhe uma pessoa só: os casais viram uma pessoa e o cachorro some. Com o bloco que pede uma peça só, com as figuras encostadas, todos os casais saíram abraçados ou de braço dado, e todos os pets ficaram no colo ou encostados na pessoa. O cavalo saiu em escala reduzida, ao lado da pessoa.
- **As regras de impressão engrossaram as figuras.** Braços e pernas ficaram mais grossos que na r0, e as mãos ficaram simples, junto ao corpo. As proporções ficaram em cerca de 4 a 4,5 cabeças, sem a cabeça grande do chibi.
- **A base tem dois efeitos.**
  - Ela dá apoio para a peça em pé. É o que segura juntos o casal e a pessoa com pet.
  - Em cor livre (r2), ela às vezes acrescenta uma cor. Na cor escura da figura (r3), ela não soma cor.
- **As cores melhoraram, mas o limite de 4 não é garantido.** Pela contagem a olho, aproximada e nas miniaturas:
  - Na r3, cerca de 10 das 18 imagens ficaram em 4 cores.
  - Os casos de duas figuras são os que mais passam, com 5 cores. A causa é sempre uma calça de cor própria, a língua do cachorro ou os talos verdes de um buquê.
  - Vale conferir em tamanho real antes de decidir.
- **O Nano Banana Pro, como reserva, não respeitou o fundo branco.** Isso aconteceu em 1 caso da r3, o poodle, que saiu com fundo cinza. O preparo de impressão depende do fundo branco.
- **A Runware recusou chamadas por saldo.** Ela reserva crédito por chamada em andamento, e 6 chamadas em paralelo estouraram o saldo da conta. O teste passou a usar 3.

## Decisão

- **A r3 vai para produção** (19/11): estilo, bloco da categoria, regras de impressão, plano de cores por categoria e base na cor escura da figura.
- **O limite de 4 cores vale para todas as categorias**, inclusive casal e pessoa com pet.

## Pendente

- Apertar o plano de cores dos casos de duas figuras, que ainda passam de 4.
- Testar com pedido do cliente e com edição.
