# PRD: App de Parceiros da EuMini

| | |
|---|---|
| **Status** | Rascunho para validação |
| **Data** | 26/11/2026 |
| **Documentos irmãos** | [PRD do MVP](PRD.md) (app do cliente) · [PRD do app Staff](PRD-staff.md) · [Arquitetura](ARQUITETURA.md) |

> **Como ler as marcações.** **P0** é obrigatório para lançar. **P1** é importante, mas pode entrar logo depois do lançamento. **[Proposta]** é um valor ou escolha inicial que ainda precisa de validação. O restante é decisão tomada.

---

## 1. Visão geral

Os parceiros são as pessoas que imprimem as peças da EuMini nas próprias impressoras. O app de parceiros é onde cada um recebe as impressões que a equipe atribuiu a ele, baixa os arquivos, informa o andamento, posta a peça e acompanha quanto tem a receber.

O parceiro **não escolhe pedidos, não prepara o 3D e não compra etiqueta.** A equipe da EuMini, pelo [app Staff](PRD-staff.md), atribui o pedido, sobe o arquivo de impressão (3MF) pronto e anexa a etiqueta de envio. O parceiro imprime, embala e posta.

O cliente compra da EuMini e nunca sabe quem imprimiu (RN-24 do [PRD do MVP](PRD.md)). O parceiro, por sua vez, vê só o necessário para imprimir e enviar.

### O que o app precisa provar

1. Parceiros externos imprimem e postam **dentro do prazo** prometido ao cliente.
2. A qualidade das peças é aceitável sem a equipe ver a peça pessoalmente.
3. O repasse ao parceiro é claro e confiável, sem planilha paralela.

---

## 2. Objetivos e não-objetivos

### Objetivos

- Mostrar ao parceiro, num só lugar, o que ele tem para imprimir e até quando.
- Entregar os arquivos de impressão de forma segura, com registro de quem baixou.
- Fazer o status do pedido avançar para o cliente a partir das ações do parceiro.
- Mostrar os ganhos de cada impressão e os repasses recebidos.

### Não-objetivos

- **Cadastro próprio e candidatura:** o parceiro entra só por convite da equipe.
- **Equipe dentro do parceiro:** um login por parceiro, sem membros nem permissões internas.
- **Vitrine de pedidos** para o parceiro escolher ou disputar.
- **Preparar o 3D:** gerar modelo, reparar malha ou fatiar. O 3MF chega pronto.
- **Comprar etiqueta** ou cotar frete.
- **Receber pelo sistema:** o repasse é feito por PIX fora do sistema; o app só mostra o extrato.
- Chat com a equipe ou com o cliente, avaliação do parceiro, nota fiscal emitida pelo sistema e aplicativo nativo.

---

## 3. Persona

| Persona | Quem é | O que precisa |
|---|---|---|
| **Parceiro** | Pessoa com impressora 3D multicor, que imprime sob demanda para a EuMini. Usa o app no computador ao lado da impressora ou no celular | Saber o que imprimir e até quando, baixar o arquivo certo, informar o andamento sem burocracia e ver quanto vai receber |

---

## 4. Jornadas

### 4.1 Do convite à primeira impressão

| # | Tela | O parceiro faz | O sistema faz |
|---|---|---|---|
| 1 | **E-mail de convite** | Abre o link | A equipe cadastrou o parceiro no app Staff e o convite foi enviado |
| 2 | **Criar senha** | Define a senha | Valida o código do convite e entra no app |
| 3 | **Impressões** | Vê a fila, separada por status, com o prazo de postagem de cada pedido | Destaca os atrasados e os que vencem em até 2 dias |
| 4 | **Pedido** | Vê os itens: imagem, categoria, tamanho e quantidade | Mostra o prazo e o que falta para o próximo passo |
| 5 | **Baixar** | Baixa o 3MF e a imagem de referência de cada item | Registra o download |
| 6 | **Iniciar produção** | Confirma que vai imprimir | O pedido aparece para o cliente como **Em produção** |
| 7 | **Marcar pronta** | Envia uma foto das peças prontas | O pedido fica aguardando etiqueta, e a equipe é avisada |
| 8 | **Etiqueta** | Recebe o e-mail, baixa a etiqueta em PDF, embala e posta | A equipe anexou etiqueta, transportadora e rastreio |
| 9 | **Marcar postado** | Confirma a postagem | O pedido aparece para o cliente como **Enviado**, com rastreio, e o ganho entra no extrato |
| 10 | **Ganhos** | Vê o extrato: a receber e pago | Mostra cada impressão postada com o valor e os repasses recebidos |

### 4.2 Estados de exceção

| Situação | O que o parceiro faz ou vê | O que acontece |
|---|---|---|
| Não pode imprimir o pedido (impressora parada, sem filamento) | **Recusar**, com motivo, enquanto não tiver iniciado | O pedido volta a ficar sem parceiro e a equipe é avisada |
| Arquivo com defeito ou impressão falhou | **Reportar problema**, com texto e foto opcional | O pedido fica marcado com problema para a equipe, sem mudar o status. A equipe pode subir novo 3MF ou reatribuir |
| A equipe subiu um novo 3MF | Aviso no pedido de que o arquivo mudou | O download passa a entregar a versão nova |
| Pedido cancelado e reembolsado | E-mail e aviso no pedido: **Cancelado, não imprimir nem postar** | O pedido sai da fila, e não há ganho por ele |
| Pedido retirado ou reatribuído pela equipe | E-mail avisando | O pedido some da fila dele |
| Prazo de postagem vencido | Pedido destacado como **Atrasado** | A equipe vê o atraso no app Staff |
| Etiqueta demorando | O pedido mostra **Aguardando etiqueta da EuMini** | A equipe vê o pedido na fila dela |

---

## 5. Requisitos funcionais

### 5.1 Acesso

| ID | Requisito | Prioridade |
|---|---|---|
| RF-PAR-01 | Entrar com e-mail e senha. Só usuários ligados a um parceiro ativo entram | P0 |
| RF-PAR-02 | Criar a senha pelo link do convite, com código de uso único | P0 |
| RF-PAR-03 | Recuperar a senha por código, como no app do cliente | P0 |
| RF-PAR-04 | Parceiro desativado perde o acesso na hora, inclusive às sessões abertas | P0 |

### 5.2 Impressões

| ID | Requisito | Prioridade |
|---|---|---|
| RF-PAR-10 | Listar os pedidos atribuídos ao parceiro, agrupados por status: **Para imprimir**, **Em produção**, **Aguardando etiqueta**, **Para postar** e **Postados** | P0 |
| RF-PAR-11 | Mostrar em cada pedido o número, a quantidade de peças, o prazo de postagem e o destaque de atraso | P0 |
| RF-PAR-12 | Mostrar no detalhe cada item com a imagem comprada, categoria, tamanho e quantidade | P0 |
| RF-PAR-13 | Baixar o 3MF e a imagem de referência de cada item, com registro de cada download | P0 |
| RF-PAR-14 | Mostrar a versão do 3MF e avisar quando a equipe subir uma nova | P0 |
| RF-PAR-15 | Buscar pelo número do pedido | P1 |

### 5.3 Ações

| ID | Requisito | Prioridade |
|---|---|---|
| RF-PAR-20 | **Recusar** um pedido atribuído e ainda não iniciado, com motivo obrigatório | P0 |
| RF-PAR-21 | **Iniciar produção**, só quando todos os itens tiverem 3MF | P0 |
| RF-PAR-22 | **Marcar pronta**, com pelo menos uma foto das peças prontas | P0 |
| RF-PAR-23 | Baixar a etiqueta em PDF e ver transportadora e rastreio, quando a equipe anexar | P0 |
| RF-PAR-24 | **Marcar postado**, só com etiqueta anexada | P0 |
| RF-PAR-25 | **Reportar problema** em qualquer pedido ativo, com texto e foto opcional | P0 |
| RF-PAR-26 | Pedir confirmação antes de recusar e de marcar postado | P0 |

### 5.4 Ganhos

| ID | Requisito | Prioridade |
|---|---|---|
| RF-PAR-30 | Mostrar o extrato: cada item postado com data, categoria, tamanho, quantidade e valor | P0 |
| RF-PAR-31 | Mostrar o total a receber e o total já pago | P0 |
| RF-PAR-32 | Listar os repasses recebidos, com data, valor e os itens que cobrem | P0 |
| RF-PAR-33 | Mostrar ajustes feitos pela equipe, com o motivo | P0 |
| RF-PAR-34 | Mostrar a tabela de valores por categoria e tamanho vigente | P1 |

### 5.5 Notificações e perfil

| ID | Requisito | Prioridade |
|---|---|---|
| RF-PAR-40 | E-mail quando um pedido for atribuído, quando a etiqueta for anexada, quando um pedido for cancelado ou retirado e quando um repasse for pago | P0 |
| RF-PAR-41 | Ver os próprios dados: nome, CEP de origem e chave PIX, cadastrados pela equipe | P0 |
| RF-PAR-42 | Editar a chave PIX e o CEP de origem, com aviso à equipe | P1 |

---

## 6. Regras de negócio

As regras RN-PAR-01 a RN-PAR-07 valem igualmente para o [app Staff](PRD-staff.md).

| ID | Regra |
|---|---|
| RN-PAR-01 | **Atribuição por pedido inteiro.** No MVP, todos os itens de um pedido vão para o mesmo parceiro e saem numa só embalagem e numa só etiqueta. |
| RN-PAR-02 | **Fluxo de cada item** (`ProductionJob`): **Sem parceiro** → a equipe atribui → **Atribuída** → o parceiro inicia → **Em produção** → o parceiro marca pronta → **Pronta para envio** → a equipe anexa a etiqueta e o parceiro posta → **Enviada**. Recusar uma atribuída volta para **Sem parceiro**. **Cancelada** vem do reembolso. As ações do parceiro valem para o pedido inteiro. |
| RN-PAR-03 | **Status do pedido para o cliente**, derivado dos itens: **Confirmado** até o parceiro iniciar, **Em produção** depois, **Enviado** ao marcar postado e **Entregue** quando a equipe confirma. O cliente recebe e-mail a cada mudança (RF-PED-05 do PRD do MVP). |
| RN-PAR-04 | **Prazo de postagem** é a data do pagamento mais o prazo de produção (7 dias úteis, RN-16 do PRD do MVP). Ele não muda com recusas ou reatribuições. |
| RN-PAR-05 | **Reembolso** cancela os itens ainda não postados. O parceiro é avisado para não imprimir nem postar, e não há ganho por eles. |
| RN-PAR-06 | **Ganho por item** = valor da tabela para a categoria e o tamanho × quantidade. O valor é congelado na atribuição, e o ganho entra no extrato quando o pedido é marcado postado. Mudar a tabela não altera pedidos já atribuídos. |
| RN-PAR-07 | **Repasse** é feito pela equipe, por PIX, fora do sistema, e registrado no app Staff. Correções são ajustes com motivo, nunca edição de valores lançados. |
| RN-PAR-08 | **O parceiro só vê os próprios pedidos.** Qualquer acesso a pedido de outro parceiro é negado. |
| RN-PAR-09 | **O que o parceiro vê:** imagem comprada, categoria, tamanho, quantidade, 3MF, prazo e etiqueta. Nome e endereço do cliente chegam só impressos na etiqueta. **Nunca vê** e-mail, CPF ou telefone do cliente, valores pagos pelo cliente nem a foto original enviada. |
| RN-PAR-10 | Arquivos só por URL assinada de curta duração, e cada download fica registrado. |
| RN-PAR-11 | Tabela de ganhos inicial [Proposta, a definir com o custo das amostras de impressão]: valor fixo por categoria e tamanho, cobrindo filamento, energia, desgaste e trabalho do parceiro. |
| RN-PAR-12 | Foto da peça pronta é guardada com o pedido e serve à equipe para conferir a qualidade e tratar reclamações. Ela nunca é mostrada ao cliente no MVP. |

---

## 7. Métricas

| Grupo | Métrica |
|---|---|
| **Prazo** | Tempo de atribuição até iniciar, até pronta e até postado (p50 e p95); pedidos postados depois do prazo |
| **Confiabilidade** | Taxa de recusa por parceiro e por motivo; problemas reportados por tipo; reatribuições |
| **Qualidade** | Reclamações e reembolsos por defeito, por parceiro |
| **Financeiro** | Total a repassar por parceiro e tempo entre postagem e repasse |

---

## 8. Riscos e pontos jurídicos

| Risco | Impacto | Como tratamos |
|---|---|---|
| **Qualidade sem conferência física.** A equipe não vê a peça antes do envio | Alto: reclamações e reembolsos | Foto obrigatória da peça pronta e acompanhamento das reclamações por parceiro |
| **Frete cotado de um CEP e postado de outro.** O cliente paga o frete cotado do CEP da EuMini, mas a etiqueta sai do CEP do parceiro | Médio: custo de frete diferente do cobrado | A EuMini absorve a diferença [Proposta]. Preferir parceiros perto da origem da cotação e medir a diferença por pedido |
| **Parceiro some com pedido atribuído** | Alto: atraso para o cliente | Prazo visível, destaque de atraso no app Staff e reatribuição |
| **Arquivo vazado ou reutilizado** | Médio | Download só autenticado, por URL assinada e com registro, e cláusula no contrato do parceiro |

**Pontos jurídicos (validar com advogado):**

- Contrato com o parceiro: prestação de serviço, prazo, qualidade, confidencialidade dos arquivos e das imagens de clientes.
- Repasse a pessoa física: como formalizar (nota fiscal do parceiro, RPA ou MEI) antes do primeiro repasse.
- LGPD: o parceiro trata nome e endereço do cliente pela etiqueta, e imagens com rostos. Ele entra como operador de dados no contrato.

---

## 9. Glossário

| Termo | Significado |
|---|---|
| **Parceiro** | Quem imprime e posta. Invisível para o cliente |
| **Atribuição** | Ligação de um pedido a um parceiro, feita pela equipe |
| **3MF** | Arquivo de impressão pronto, com cores e fatiamento, subido pela equipe |
| **Imagem de referência** | A imagem 2D que o cliente comprou |
| **Prazo de postagem** | Data limite para postar o pedido |
| **Ganho** | Valor que o parceiro recebe por item postado |
| **Repasse** | Pagamento ao parceiro, por PIX, que quita ganhos |
| **Ajuste** | Crédito ou débito no extrato, com motivo, feito pela equipe |
