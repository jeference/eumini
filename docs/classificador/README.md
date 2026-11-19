# Teste do classificador: Jev (TypeSafe)

| | |
|---|---|
| **Data** | 19/11/2026 |
| **Objetivo** | Saber se o Jev serve como classificador da Kubo (RN-30 a RN-38 do [PRD](../PRD.md)): decidir a categoria da foto antes de gerar e a categoria de cada versão gerada |
| **Resultado** | **Aprovado no teste.** Na versão final das perguntas, acertou 46 de 47 casos, sempre com a mesma resposta nas 3 repetições, em 0,23 s (mediana) e por cerca de US$ 0,0001 por chamada |

## Como foi feito

- **Modelo:** `jev-1.14.0`, pela API da TypeSafe (`POST https://api.typesafe.ai/v1/systemone`), com a imagem ligada pelo cabeçalho `TypeSafe-Danger-Zone-Images: true`. A TypeSafe diz que a entrada de imagem ainda não está pronta para produção.
- **Casos:** 47 imagens em [`casos.json`](casos.json), cada uma com a resposta esperada.
  - **29 fotos:** os casos difíceis do estudo da Pockella, mais fotos do Wikimedia Commons e fotos enviadas no app em desenvolvimento.
  - **18 versões:** imagens geradas pela Kubo em desenvolvimento e resultados do estudo de estilos da Jujubit.
  - **Excluídas:** fotos de crianças e fotos de uma pessoa real que não é pública.
- **Uma chamada por imagem**, com várias perguntas, todas no [`teste_jev.py`](teste_jev.py):
  - `subject` (escolha): quem está na imagem, entre as 4 categorias vendidas e as 4 recusadas da Pockella. A descrição muda entre foto e versão.
  - `character` (sim ou não): se mostra um personagem ou marca protegidos, inclusive como fantasia.
- **Decisão:** personagem com probabilidade ≥ 0,8 → `protected_character`; senão, vale a escolha de `subject`.
- **Desenhos e pinturas são aceitos** quando mostram uma pessoa ou um pet (RN-31). A v2 tinha uma pergunta `artwork` que os recusava; ela foi retirada na v3.
- **Repetições:** 3 por caso, para medir se a resposta se repete.
- **Imagens pequenas:** imagens com o menor lado abaixo de 280 px são ampliadas antes do envio, porque o Jev as recusa com erro 400.

Para rodar de novo: `apps/backend/.venv/Scripts/python.exe -I docs/classificador/teste_jev.py jev-1.14.0 3`. O resultado vai para [`resultados/`](resultados/).

## Resultados

| Rodada | Fotos certas | Versões certas | Estáveis nas repetições | Tempo p50 / p95 | Custo por chamada |
|---|---|---|---|---|---|
| v1: pergunta "é foto real?", limite de personagem 0,5 | 26 de 30 | 17 de 18 | Todas | 0,24 s / 0,36 s | US$ 0,00012 |
| v2: pergunta "é desenho ou pintura?", limite de personagem 0,8 | 29 de 30 | 18 de 18 | Todas | 0,22 s / 0,27 s | US$ 0,00012 |
| v2 no `jev-1.13.0` (1 repetição) | 29 de 30 | 18 de 18 | - | 0,25 s / 0,38 s | US$ 0,00012 |
| **v3: sem a pergunta de desenho, desenhos e pinturas aceitos** | **28 de 29** | **18 de 18** | **Todas** | **0,23 s / 0,44 s** | **US$ 0,00012** |

As rodadas v1 e v2 contaram 30 fotos porque uma delas estava duplicada (`f-pet-gato-casa` era o mesmo arquivo de `f-pet-gato`, e as duas deram certo). A cópia saiu, e a v3 foi rodada de novo com 29 fotos.

A v3 é a versão que vai para produção (`resultados/jev-1.14.0.json`). As rodadas anteriores ficam em `resultados/*-v1.json` e `*-v2.json`.

O custo considera só os tokens de entrada (cerca de 2.800 por chamada, imagem incluída), a US$ 0,042 por milhão.

### O que a v1 e a v2 ensinaram

- **"É foto real?" é a pergunta errada** (v1). Duas fotos realistas, muito tratadas e talvez feitas por IA (mulher abraçando um cachorro, dois cães), tiveram notas de 0,17 e 0,26. O desenho infantil teve 0,20, então nenhum limite separava os dois grupos. Perguntando "é desenho, pintura ou ilustração?", a arte ficou entre 0,94 e 0,97, e todas as fotos ficaram em 0,31 ou menos.
- **A pergunta de desenho quase não mudava as decisões** (v2). Sem ela, o desenho infantil já cai em `no_subject` e o Mickey em `protected_character`. Só os retratos pintados passavam a ser vendidos. Ela saiu porque recusaria avatares e retratos de pets feitos por encomenda; o risco que fica é o de ilustração de outro autor (RN-27).
- **Personagem com limite 0,5 erra.** Um gatinho gerado pela Kubo, com laço rosa, teve 0,67, provavelmente por lembrar a Hello Kitty. Os personagens de verdade ficaram entre 0,97 e 0,99, então o limite passou a 0,8.
- **Imagens pequenas são recusadas.** A foto do busto do Batman, com 231 × 300 px, deu erro 400 ("Invalid image dimensions").

### Casos difíceis da Pockella

| Caso | Pockella | Jev (v3) |
|---|---|---|
| Mickey | Vendeu como pessoa | `protected_character` (0,99) |
| Desenho infantil | Vendeu como pessoa | `no_subject` |
| Pelúcia | Vendeu como pet (estudo anterior) | `no_subject` |
| Pessoa + cavalo | Vendeu como Pessoa + Pet | `person_pet` |
| Papagaio | Vendeu como pet | `pet` |
| Três homens, multidão | Recusou (3 ou mais) | `three_or_more_people` |
| Dois cães | Recusou (2 ou mais pets) | `multiple_pets` |
| Mulher com dois cães (preto e branco) | Recusou (grupo com pets) | **`person_pet`**: erro, veja abaixo |
| Cartão-postal manuscrito | Recusou (sem pessoa ou pet) | `no_subject` |

Nas versões, o Jev reconheceu gatos vestidos, de boné, astronauta e dentro de um foguete como `pet`. Reconheceu o Batman, o Batman vermelho e o gato fantasiado de Batman como `protected_character`.

### O único erro

Na foto antiga da mulher com dois cães, o segundo cão está quase escondido. O Jev respondeu `person_pet`, com confiança de 0,81, nas 3 repetições e também no 1.13. A consequência é pequena: a criação seguiria como Pessoa + Pet, e se a imagem gerada tiver os dois cães, a classificação da versão (RN-34) a recusa para compra.

## Limitações

- **Os limites foram ajustados nos mesmos casos em que foram medidos.** O acerto real tende a ser menor. Antes de produção, vale rodar um segundo conjunto, que não tenha sido usado no ajuste.
- **47 casos é pouco** para medir taxas de erro pequenas. As fotos de clientes reais (selfies, iluminação ruim, várias pessoas ao fundo) só serão conhecidas no uso.
- **A confiança da escolha não aponta o erro.** O único erro veio com 0,81, acima de vários acertos (0,60 a 0,70). Ela não serve, sozinha, como gatilho para o "Quem está na foto?".
- **A entrada de imagem é experimental** segundo a própria TypeSafe. O comportamento pode mudar entre versões, e a integração precisa de um modelo de reserva.
- **Não foi comparado com a OpenAI nem com o Google**, por falta de chaves.
