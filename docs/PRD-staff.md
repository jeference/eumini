# PRD: App Staff da EuMini

| | |
|---|---|
| **Status** | Rascunho para validação |
| **Data** | 26/11/2026 |
| **Documentos irmãos** | [PRD do MVP](PRD.md) (app do cliente) · [PRD do app de Parceiros](PRD-parceiros.md) · [Arquitetura](ARQUITETURA.md) |

> **Como ler as marcações.** **P0** é obrigatório para lançar. **P1** é importante, mas pode entrar logo depois do lançamento. **[Proposta]** é um valor ou escolha inicial que ainda precisa de validação. O restante é decisão tomada.

---

## 1. Visão geral

O app Staff é o painel interno de quem trabalha na EuMini. Hoje, depois do pagamento, o pedido fica parado em **Confirmado**: nenhuma tela mostra os pedidos, entrega os arquivos ou registra o envio, e os alertas só aparecem no log. O app Staff fecha esse ciclo.

Nele, a equipe vê todos os pedidos, baixa a imagem e a foto de cada item, sobe o arquivo de impressão (3MF), atribui o pedido a um [parceiro](PRD-parceiros.md), anexa a etiqueta de envio, confirma a entrega e paga o parceiro.

**Três passos continuam fora do sistema no MVP**, e o app só registra o resultado:

| Passo | Onde é feito | O que o app registra |
|---|---|---|
| Gerar o 3D e fatiar | Ferramentas de 3D e fatiador, fora do sistema | O 3MF, subido no item |
| Comprar a etiqueta | Painel do Melhor Envio | PDF da etiqueta, transportadora e rastreio |
| Pagar o parceiro | PIX pelo banco da EuMini | O repasse, com data e valor |

### O que o app precisa provar

1. A equipe trata cada pedido pago, do pagamento à entrega, sem planilha paralela.
2. Nenhum pedido pago fica esquecido ou atrasado sem que alguém veja.
3. O que cada parceiro tem a receber bate com o que foi postado.

---

## 2. Objetivos e não-objetivos

### Objetivos

- Uma fila de trabalho que mostre, a cada dia, o que precisa de ação.
- Todas as informações do pedido num só lugar, inclusive o histórico de eventos.
- Atribuir pedidos a parceiros e acompanhar a produção.
- Registrar etiqueta, envio e entrega, para o cliente ver o status certo.
- Controlar os ganhos e os repasses dos parceiros.

### Não-objetivos

- **Automação depois do pagamento:** geração do 3D, compra de etiqueta pela API e atribuição automática.
- **Reembolso pelo app:** no MVP, segue pelo painel do gateway, e o pedido se atualiza sozinho (RN-22 do [PRD do MVP](PRD.md)). Entra como P1.
- **Gestão de preços e tamanhos do cliente:** segue por migração de dados.
- **Tela de alertas internos:** seguem no log. Entra como P1.
- Consulta de criações, classificações, lista de espera e custos de IA.
- Atendimento de remoção de conteúdo.
- Papéis diferentes dentro da equipe: no MVP há só `staff` (`admin` segue reservado).
- Gestão das contas da equipe pela interface: são criadas por comando no servidor.

---

## 3. Persona

| Persona | Quem é | O que precisa |
|---|---|---|
| **Operação EuMini** | Pessoa da equipe que trata os pedidos pagos, prepara o 3MF, fala com os parceiros e paga os repasses | Saber o que fazer hoje, achar qualquer pedido rápido, agir sem sair do sistema e não errar o pagamento dos parceiros |

---

## 4. Jornadas

### 4.1 Do pagamento à entrega

| # | Tela | A equipe faz | O sistema faz |
|---|---|---|---|
| 1 | **Hoje** | Vê a fila do dia: **a atribuir**, **sem 3MF**, **aguardando etiqueta**, **atrasados** e **com problema** | Conta e ordena cada grupo pelo prazo de postagem |
| 2 | **Pedido** | Abre o pedido: itens, endereço, cobranças, histórico | Mostra tudo o que foi congelado na compra (RN-17 do PRD do MVP) |
| 3 | **Baixar** | Baixa a imagem comprada e a foto enviada de cada item | Registra o download |
| 4 | **Subir 3MF** | Gera o 3D e fatia fora do sistema, depois sobe o 3MF em cada item | Guarda a versão. Se o parceiro já tiver o pedido, ele é avisado |
| 5 | **Atribuir** | Escolhe o parceiro | Congela o ganho de cada item e envia o e-mail ao parceiro |
| 6 | **Acompanhar** | Vê o parceiro iniciar e marcar pronta, com a foto das peças | Atualiza o status para o cliente |
| 7 | **Etiqueta** | Compra a etiqueta no Melhor Envio, com origem no CEP do parceiro, e anexa o PDF, a transportadora e o rastreio | Avisa o parceiro que a etiqueta está pronta |
| 8 | **Postado** | Vê o parceiro marcar postado | O cliente vê **Enviado**, com rastreio, e o ganho entra no extrato do parceiro |
| 9 | **Entregue** | Confere o rastreio e marca entregue | O cliente vê **Entregue** e recebe o e-mail |

### 4.2 Pagar um parceiro

| # | Tela | A equipe faz | O sistema faz |
|---|---|---|---|
| 1 | **Parceiros** | Vê o saldo a pagar de cada parceiro | Soma os ganhos postados ainda não pagos e os ajustes |
| 2 | **Repasse** | Faz o PIX pelo banco e registra o repasse: data, valor e comprovante opcional | Marca como pagos os ganhos cobertos e avisa o parceiro por e-mail |

### 4.3 Estados de exceção

| Situação | O que a equipe vê | O que faz |
|---|---|---|
| Parceiro recusou | O pedido volta para **a atribuir**, com o motivo | Atribui a outro parceiro |
| Parceiro reportou problema | O pedido entra em **com problema**, com texto e foto | Sobe novo 3MF, reatribui ou fala com o parceiro. Marca o problema como resolvido |
| Parceiro não avança | O pedido aparece em **atrasados** | Fala com o parceiro ou retira e reatribui, enquanto não tiver sido postado |
| Pedido reembolsado no gateway | O pedido mostra **Reembolsado** e os itens **Cancelados** | Nada: o parceiro é avisado automaticamente |
| Etiqueta errada | O pedido ainda não postado mostra a etiqueta atual | Substitui a etiqueta, e o parceiro é avisado |
| Peça perdida ou com defeito depois de postada | O pedido mostra **Enviado** ou **Entregue** | Reembolsa pelo gateway ou cria um pedido de reposição fora do MVP. Faz ajuste no extrato do parceiro, se for o caso |
| Erro no extrato do parceiro | O extrato com os lançamentos | Lança um ajuste de crédito ou débito, com motivo |

---

## 5. Requisitos funcionais

### 5.1 Acesso

| ID | Requisito | Prioridade |
|---|---|---|
| RF-STF-01 | Entrar com e-mail e senha. Só usuários com o papel `staff` entram | P0 |
| RF-STF-02 | Recuperar a senha por código, como no app do cliente | P0 |
| RF-STF-03 | Criar e desativar contas da equipe por comando no servidor | P0 |

### 5.2 Fila e pedidos

| ID | Requisito | Prioridade |
|---|---|---|
| RF-STF-10 | Tela **Hoje** com os grupos: a atribuir, sem 3MF, aguardando etiqueta, atrasados e com problema, cada um com contagem e ordenado pelo prazo | P0 |
| RF-STF-11 | Listar todos os pedidos, com filtros por status, data, número, e-mail do cliente e parceiro | P0 |
| RF-STF-12 | Detalhe do pedido: cliente (nome, e-mail, CPF mascarado), endereço, frete e prazo prometido, valores, cobranças e parceiro | P0 |
| RF-STF-13 | Em cada item: imagem comprada, foto enviada, pedido de alteração do cliente, prompt final, categoria, tamanho, quantidade, 3MF e status | P0 |
| RF-STF-14 | Histórico do pedido com todos os eventos (pagamento, atribuições, recusas, ações do parceiro, etiqueta, entrega), com ator e data | P0 |
| RF-STF-15 | Mostrar a foto da peça pronta e os problemas reportados pelo parceiro | P0 |

### 5.3 Arquivos

| ID | Requisito | Prioridade |
|---|---|---|
| RF-STF-20 | Baixar a imagem comprada e a foto original de cada item, com registro de cada download | P0 |
| RF-STF-21 | Subir o 3MF de cada item. Uma nova versão substitui a anterior para o parceiro, e as antigas ficam guardadas | P0 |
| RF-STF-22 | Subir o mesmo 3MF para itens iguais do pedido de uma vez | P1 |

### 5.4 Produção e envio

| ID | Requisito | Prioridade |
|---|---|---|
| RF-STF-30 | **Atribuir** o pedido inteiro a um parceiro ativo | P0 |
| RF-STF-31 | **Retirar** ou **reatribuir** o pedido enquanto não tiver sido postado, com motivo | P0 |
| RF-STF-32 | **Anexar etiqueta:** PDF, transportadora e rastreio, quando o pedido estiver pronto para envio. Substituir enquanto não tiver sido postado | P0 |
| RF-STF-33 | **Marcar entregue** um pedido enviado | P0 |
| RF-STF-34 | **Marcar problema como resolvido**, com nota | P0 |
| RF-STF-35 | Avançar pelo parceiro, com motivo, quando ele não conseguir usar o app (iniciar, pronta, postado) | P1 |

### 5.5 Parceiros

| ID | Requisito | Prioridade |
|---|---|---|
| RF-STF-40 | Cadastrar parceiro: nome, e-mail do login, CEP de origem e chave PIX. O cadastro envia o convite | P0 |
| RF-STF-41 | Reenviar o convite, editar os dados e desativar ou reativar o parceiro. Desativar exige que ele não tenha pedidos ativos | P0 |
| RF-STF-42 | Listar parceiros com pedidos ativos, atrasados e saldo a pagar | P0 |

### 5.6 Ganhos e repasses

| ID | Requisito | Prioridade |
|---|---|---|
| RF-STF-50 | Manter a tabela de ganhos por categoria e tamanho. Mudanças valem só para novas atribuições | P0 |
| RF-STF-51 | Ver o extrato de cada parceiro: ganhos, ajustes, repasses e saldo | P0 |
| RF-STF-52 | **Registrar repasse:** data, valor e comprovante opcional, cobrindo os ganhos a pagar. O valor precisa bater com a soma dos itens escolhidos | P0 |
| RF-STF-53 | **Lançar ajuste** de crédito ou débito, com motivo obrigatório | P0 |

### 5.7 Depois do lançamento

| ID | Requisito | Prioridade |
|---|---|---|
| RF-STF-60 | Cancelar e reembolsar o pedido inteiro pela API do gateway, com motivo | P1 |
| RF-STF-61 | Tela de alertas internos: pagamento sem pedido, pagamento em duplicidade, disputa, teto de gasto | P1 |
| RF-STF-62 | Ativar e desativar tamanhos e mudar preços do cliente | P1 |

---

## 6. Regras de negócio

As regras de atribuição, fluxo, status, prazo, reembolso, ganho e repasse são as mesmas do app de parceiros: [RN-PAR-01 a RN-PAR-07](PRD-parceiros.md#6-regras-de-negócio).

| ID | Regra |
|---|---|
| RN-STF-01 | **Só a equipe atribui pedidos.** Um pedido só vai para parceiro ativo. |
| RN-STF-02 | **O 3MF não é exigido para atribuir**, mas o parceiro só inicia a produção com o 3MF de todos os itens. |
| RN-STF-03 | **Toda ação da equipe gera um evento** com o ator, a data e, quando houver, o motivo. |
| RN-STF-04 | **Nada da equipe altera o que o cliente pagou:** categoria, preço, frete, imagem e endereço seguem congelados (RN-17 do PRD do MVP). Correção de endereço, se precisar, é combinada com o cliente fora do sistema e anotada no pedido. |
| RN-STF-05 | **Etiqueta só com o pedido pronto para envio**, para não pagar etiqueta de pedido que pode ser cancelado ou reimpresso. |
| RN-STF-06 | A etiqueta é comprada com origem no **CEP do parceiro** e destino no endereço congelado do pedido. |
| RN-STF-07 | **Entregue é marcado pela equipe**, conferindo o rastreio. Não há consulta automática à transportadora no MVP. |
| RN-STF-08 | **Downloads só por URL assinada de curta duração**, com registro. Arquivos ligados a pedidos nunca são apagados (RN-28 do PRD do MVP). |
| RN-STF-09 | **A equipe vê os dados pessoais do cliente**, com CPF sempre mascarado. Eles nunca passam ao parceiro (RN-PAR-09). |
| RN-STF-10 | **Repasses e ajustes não são editados nem apagados.** Um erro é corrigido com novo ajuste. |

---

## 7. Métricas

| Grupo | Métrica |
|---|---|
| **Fila** | Pedidos pagos sem atribuição, por idade; pedidos sem 3MF; pedidos aguardando etiqueta |
| **Prazo** | Tempo de pago até atribuído, postado e entregue (p50 e p95); pedidos atrasados |
| **Qualidade** | Problemas reportados, reatribuições e reembolsos por motivo |
| **Financeiro** | Saldo a repassar por parceiro; diferença entre frete cobrado do cliente e etiqueta comprada |

---

## 8. Riscos

| Risco | Impacto | Como tratamos |
|---|---|---|
| **Gargalo no 3D e no fatiamento manuais.** Cada item exige gerar o 3D e fatiar fora do sistema | Alto: atrasos com o volume | Fila **sem 3MF** visível e medida. Automatizar na preparação de impressão, depois do MVP |
| **Rastreio digitado errado** ao anexar a etiqueta | Médio: cliente sem rastreio certo | Rastreio aparece para o parceiro conferir com a etiqueta, e pode ser corrigido antes de postar |
| **Repasse registrado errado** | Médio: parceiro pago a mais ou a menos | Valor do repasse precisa bater com os itens cobertos, e correção só por ajuste |
| **Pessoa única na operação** | Alto: pedidos parados | Fila **Hoje** e atrasos visíveis para qualquer pessoa da equipe |

---

## 9. Glossário

| Termo | Significado |
|---|---|
| **Equipe** | Pessoas da EuMini com o papel `staff` |
| **Fila Hoje** | Pedidos que precisam de ação da equipe, por grupo |
| **Atribuir** | Ligar o pedido inteiro a um parceiro |
| **3MF** | Arquivo de impressão pronto, com cores e fatiamento |
| **Etiqueta** | Etiqueta de frete comprada no Melhor Envio, em PDF |
| **Extrato** | Ganhos, ajustes e repasses de um parceiro |
| **Repasse** | Pagamento ao parceiro, por PIX fora do sistema, registrado no app |
