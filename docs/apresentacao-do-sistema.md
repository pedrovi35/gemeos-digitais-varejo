# Roteiro de apresentação — Gêmeo Digital de Varejo

Documento de apoio completo para apresentar o sistema **e conduzir a
demonstração ao vivo da interface Streamlit, página por página**.

Cada bloco traz:

- 🎬 **Mostrar** — o que deixar na tela.
- 🎤 **Fala** — o texto sugerido para falar (adapte ao seu tom).
- 💡 **Nota do apresentador** — dicas, o que evitar, o que enfatizar.
- ⏱️ tempo estimado.

## Como usar este roteiro

O roteiro tem **três durações possíveis**. Escolha conforme o público e o tempo:

| Versão | Duração | Blocos |
|--------|---------|--------|
| **Relâmpago** | 5 min | 1, 2, 4.1, 5, 8 |
| **Padrão** | 15 min | 1, 2, 3, 4.1–4.6, 5, 8 |
| **Completa** | 30–35 min | todos os blocos, incluindo o aprofundamento técnico (bloco 6) |

Antes de começar, deixe o app rodando (`streamlit run app.py`) aberto na
**Torre de Controle**, com o seed populado e os filtros limpos. Veja o
**Anexo C — Checklist pré-apresentação** no fim do documento.

---

# PARTE I — A NARRATIVA DE NEGÓCIO

## Bloco 1 · Abertura — o problema (2 min)

🎬 **Mostrar:** slide de título, ou já a Torre de Controle desfocada ao fundo.

🎤 **Fala:**
> "Bom dia a todos. Obrigado pela presença. Nos próximos minutos vou apresentar
> o **Gêmeo Digital de Varejo** — uma plataforma de inteligência operacional
> para a cadeia de suprimentos de redes de supermercados.
>
> Quero começar com uma cena que todo mundo aqui conhece. É sábado de manhã, a
> loja está cheia, e o cliente vai buscar um produto que sempre compra — e a
> gôndola está vazia. O que acontece nos cinco minutos seguintes define muito
> dinheiro: ou ele troca por um substituto, ou ele desiste, ou — pior — ele vai
> comprar no concorrente e leva o resto da lista junto.
>
> Isso é uma **ruptura**. E o problema da ruptura não é ela existir — é que,
> hoje, na maioria das redes, ela só é **percebida depois que já custou caro**.
> O relatório de venda perdida chega na segunda-feira. O ajuste de inventário
> aparece no balanço. O atraso do fornecedor vira problema quando a prateleira
> já esvaziou.
>
> A operação inteira funciona no modo **reativo**: apaga incêndio. E apagar
> incêndio é caro, é estressante e não escala.
>
> A proposta deste sistema é inverter essa lógica. Em vez de reagir à ruptura,
> nós a **antecipamos** — e, mais do que isso, **explicamos o porquê** em
> linguagem que o gerente da loja entende e pode agir. Sair do modo *bombeiro*
> e entrar no modo *meteorologista*: prever a tempestade enquanto ainda dá tempo
> de fechar a janela."

💡 **Nota do apresentador:** a cena do sábado de manhã é o gancho emocional —
conte devagar, faça a plateia visualizar. Não jogue números técnicos aqui;
isso vem depois. O objetivo deste bloco é só fazer todos concordarem que o
problema é real e caro.

---

## Bloco 2 · O que é o sistema (3 min)

🎬 **Mostrar:** Torre de Controle (home), com o menu lateral visível.

🎤 **Fala:**
> "Então, o que é exatamente o Gêmeo Digital de Varejo?
>
> Primeiro, o que ele **não é**: não é um ERP, não é um WMS, não substitui
> nenhum sistema que vocês já têm. Ele **se conecta** aos dados que a operação
> já gera — vendas, inventário, pedidos de reposição, cadastro de fornecedores —
> e adiciona uma camada nova por cima: uma **camada de observabilidade e
> predição**.
>
> O conceito de *gêmeo digital* vem da indústria: é uma **réplica computacional
> de um sistema físico**, que permite observar e experimentar sem tocar no
> sistema real. Uma montadora tem o gêmeo digital de uma turbina; nós temos o
> gêmeo digital de uma rede de supermercados.
>
> E esse gêmeo responde a **três perguntas de negócio** — e é importante guardar
> essas três perguntas, porque a interface inteira é organizada em torno delas:
>
> **Pergunta um: como estamos agora?** Esse é o *gêmeo de estado* — um espelho
> fiel da rede, atualizado em tempo quase real. Nível de serviço, ruptura,
> receita, estoque, em todas as lojas.
>
> **Pergunta dois: o que vai dar errado?** Aqui entram cinco modelos de
> machine learning, cada um especializado em prever um tipo de ruptura. Eles
> transformam o estado atual num **score de risco** olhando para a frente.
>
> **Pergunta três: e se...?** Esse é o *gêmeo de simulação*. Ele deixa a gente
> testar cenários — 'e se esse fornecedor cair?', 'e se a demanda dobrar na
> Black Friday?' — e projeta o impacto **antes** de a decisão ser tomada.
>
> E tem um quarto princípio, que é o mais importante de todos para a
> credibilidade do sistema. Eu chamo de: **os modelos preveem, a inteligência
> artificial explica**.
>
> O número de risco — aquele score de 0 a 1 — vem sempre de **modelos
> estatísticos auditáveis**, que a gente consegue abrir, inspecionar e validar.
> A inteligência artificial generativa, o tipo de IA que está na moda, entra
> só no final, e só para **traduzir** esse número numa narrativa que um
> executivo lê em dez segundos. A IA generativa **nunca inventa o risco**. Ela
> nunca decide se algo é perigoso. Ela pega um diagnóstico que já foi calculado
> e o escreve em bom português. Isso é uma decisão de arquitetura deliberada, e
> volto nela mais de uma vez."

💡 **Nota do apresentador:** o "modelos preveem, IA explica" é o ponto de
confiança da apresentação. Plateias céticas de IA generativa vão relaxar quando
ouvirem isso. Repita a frase. Se alguém perguntar "isso é mais um hype de IA?",
a resposta já está plantada.

---

## Bloco 3 · As cinco rupturas R1–R5 (4 min)

🎬 **Mostrar:** página **Rupture Intelligence**, ou um slide com a tabela R1–R5.

🎤 **Fala (introdução):**
> "Eu falei em 'cinco tipos de ruptura'. Vamos detalhar, porque cada um é um
> problema de negócio diferente, com causas diferentes e donos diferentes
> dentro da operação. A gente chama de R1 a R5."

### R1 — Quebra de inventário

🎤 **Fala:**
> "**R1, quebra de inventário.** É quando o estoque que o sistema *diz* que
> existe não bate com o que está *fisicamente* na loja. O sistema acha que tem
> 40 unidades, tem 12. Resultado: o pedido de reposição vem errado, a gôndola
> esvazia sem aviso. As causas são furto, quebra, erro de recebimento, falha de
> contagem. O modelo R1 olha acurácia de estoque, frequência de stockout,
> divergências acumuladas e idade da última contagem física."

### R2 — Venda acima da média

🎤 **Fala:**
> "**R2, venda acima da média.** É um pico de demanda que vai furar a cobertura
> de estoque antes da próxima reposição chegar. Pode ser um fim de semana
> atípico, um evento na região, um efeito climático. O modelo R2 olha a
> aceleração da demanda, o desvio em relação à média móvel, o índice sazonal."

### R3 — Promoção não sinalizada

🎤 **Fala:**
> "**R3, promoção não sinalizada.** Esse é sutil e muito comum. A loja, ou o
> comercial, coloca um desconto na ponta — mas a cadeia de suprimentos não foi
> avisada. A demanda dispara, o estoque planejado era para venda normal, e a
> gôndola seca em horas. O modelo R3 cruza o que está sendo vendido com desconto
> no PDV contra o calendário oficial de promoções, e detecta o uplift que não
> tinha registro."

### R4 — Lead time de reposição

🎤 **Fala:**
> "**R4, lead time de reposição.** É o risco de o reabastecimento chegar tarde
> demais. O pedido foi feito, mas entre o atraso do fornecedor e a cobertura
> baixa de estoque, a conta não fecha — vai faltar produto antes de o caminhão
> chegar. O modelo R4 olha o lead time real contra o planejado, a taxa de
> entregas atrasadas, a cobertura em dias."

### R5 — Restrição de faturamento do fornecedor

🎤 **Fala:**
> "**R5, restrição de faturamento do fornecedor.** É um bloqueio comercial ou
> financeiro que trava os pedidos de um fornecedor inteiro. Quando isso
> acontece, não é um produto que some — são **dezenas de SKUs daquele
> fornecedor** ao mesmo tempo. É a ruptura de maior impacto sistêmico. O modelo
> R5 olha pedidos rejeitados ou bloqueados, taxa de rejeição de nota fiscal,
> indicadores financeiros do fornecedor."

🎤 **Fala (fechamento do bloco):**
> "Cinco modelos, cinco problemas. Mas — e isso é importante para a usabilidade
> — todos entregam **o mesmo formato de saída**: um score de risco de 0 a 1 por
> entidade. Para R1 a R4, a entidade é uma combinação **loja-produto**. Para R5,
> a entidade é o **fornecedor**. E esse score vem com um nível operacional —
> baixo, médio, alto, crítico — para que o gerente saiba o que priorizar sem
> precisar interpretar um número decimal."

💡 **Nota do apresentador:** se o tempo estiver curto, este bloco é o primeiro
candidato a encurtar — apresente a tabela R1–R5 no slide e fale dois exemplos
(R1 e R5, os extremos: o mais granular e o mais sistêmico). Guarde os detalhes
para perguntas.

---

# PARTE II — A DEMONSTRAÇÃO DA INTERFACE

## Bloco 4 · Passeio guiado pela interface Streamlit (8–10 min)

💡 **Nota do apresentador:** esta é a parte que a plateia veio ver. Navegue
**devagar**. Deixe cada tela respirar dois ou três segundos em silêncio antes
de falar — dá tempo de a plateia ler. Não leia os números da tela em voz alta;
conte a *história* que os números mostram. Se uma página demorar a carregar,
não fique em silêncio constrangido: explique o que vai aparecer.

### 4.1 · Torre de Controle (a home)

🎬 **Mostrar:** página inicial, percorrendo de cima para baixo com o cursor.

🎤 **Fala:**
> "Esta é a **Torre de Controle** — a porta de entrada do sistema, a tela que
> fica aberta no telão da sala de operações.
>
> No topo, a faixa de **KPIs da rede inteira**: nível de serviço, taxa de
> ruptura, receita do dia. É o sinal vital da operação num relance.
>
> Logo abaixo, esse número grande é o **índice de risco da rede** — uma escala
> de 0 a 100 que combina os cinco modelos numa média ponderada. É o número que
> o diretor olha primeiro: subiu, alguma coisa está se deteriorando; está
> estável, a rede está sob controle.
>
> Mais abaixo, o **feed de alertas** e o **ranking das entidades em maior
> risco** — as combinações loja-produto que precisam de atenção agora.
>
> E reparem nessa barra de filtros no topo: **região, loja, categoria,
> fornecedor, período**. Esse é um detalhe de usabilidade que faz diferença no
> dia a dia: qualquer filtro que eu aplicar aqui é **preservado quando eu
> navego para outra página**. Se eu estou investigando a loja 005, eu filtro
> uma vez e o sistema inteiro passa a falar da loja 005."

💡 **Nota:** se os KPIs estiverem zerados (problema conhecido com seed sem dado
na data corrente), não dramatize — diga "nesta instância de demonstração os
KPIs do dia ainda não populei; o que importa aqui é a estrutura" e siga para o
índice de risco, que costuma estar populado.

### 4.2 · Centros por ruptura (R1–R5) — o coração analítico

🎬 **Mostrar:** abrir o **R1 Inventory Break Center**. Rolar até a lista e
abrir os drivers de um item.

🎤 **Fala:**
> "Agora o coração analítico do sistema. Cada uma das cinco rupturas tem o seu
> **centro dedicado** — aqui estou no centro do R1, quebra de inventário.
>
> O que eu vejo é o **ranking das combinações loja-produto com maior risco de
> quebra**. Mas olhar um ranking de risco qualquer dashboard faz. O que torna
> isso uma ferramenta de *decisão* é o que vem a seguir.
>
> Para cada item do ranking, o sistema mostra os **drivers** — quais variáveis,
> especificamente, estão empurrando aquele score para cima. Olhem aqui: não diz
> só *'esse SKU está em risco'*. Diz *'esse SKU está em risco **porque** a
> acurácia de estoque caiu para tal nível **e** a frequência de stockout subiu'*.
>
> Isso usa uma técnica chamada **SHAP**, que é um padrão de mercado para abrir a
> caixa-preta de um modelo de machine learning. Cada barra que vocês veem é a
> contribuição de uma variável para aquela predição específica.
>
> A diferença prática é enorme. Um alarme cego diz 'cuidado'. Isso aqui é um
> **diagnóstico**: diz cuidado, o motivo é esse, e por tabela aponta a ação. Se
> o driver é acurácia de estoque, a ação é contagem física. Se é lead time, a
> ação é falar com o fornecedor. O sistema não só prevê — ele orienta a
> resposta."

🎤 **Fala (navegando rápido pelos outros centros):**
> "E essa mesma estrutura se repete, idêntica, nos cinco centros — R2 demanda,
> R3 promoção, R4 lead time, R5 fornecedor. Quem aprende a ler um centro, sabe
> ler todos. A consistência é proposital: reduz o atrito de adoção."

💡 **Nota:** o SHAP é o momento "uau" técnico da demo. Se houver um item com
drivers bem visíveis, pare nele. Não use a palavra "SHAP" sem explicar — diga
"uma técnica que abre a caixa-preta" antes de nomear.

### 4.3 · Inventory Health e Supplier Risk Center

🎬 **Mostrar:** **Inventory Health**, depois **Supplier Risk Center**.

🎤 **Fala:**
> "Além dos centros por modelo, há visões temáticas. A **Saúde de Inventário**
> consolida a posição de estoque da rede — cobertura, itens críticos, onde está
> a gordura e onde está a magreza.
>
> E o **Centro de Risco de Fornecedores** vira a lente para o lado da oferta:
> quais fornecedores estão com OTD ruim, quais concentram risco, quais SKUs
> ficam expostos se um deles falhar. Lembrando que o fornecedor é a entidade de
> maior alavancagem — por isso ele tem um centro só dele."

### 4.4 · Observatório da Cadeia e Linha do Tempo

🎬 **Mostrar:** **Supply Chain Observatory** (grafo), depois **Operational
Timeline**.

🎤 **Fala:**
> "O **Observatório da Cadeia** dá a visão de **rede**. Esse grafo conecta
> lojas, fornecedores e os fluxos entre eles, e destaca visualmente os pontos
> de tensão. É a visão de quem precisa enxergar a cadeia como um sistema, não
> como uma lista.
>
> E a **Linha do Tempo Operacional** responde à pergunta *'quando isso
> começou?'*. Ela mostra a sequência cronológica de eventos — vendas,
> stockouts, reposições, alertas. Quando uma situação se deteriora, é aqui que
> a gente reconstrói a história e encontra o gatilho."

### 4.5 · Laboratório de Simulação — o gêmeo digital em ação

🎬 **Mostrar:** página **Digital Twin Simulation**. Selecionar um cenário,
mexer nos sliders, clicar em "Projetar impacto", depois "Rodar simulação".

🎤 **Fala:**
> "Agora a parte que dá nome ao produto. Até aqui eu mostrei o gêmeo
> *observando* a operação. Este é o gêmeo **simulando** a operação.
>
> Este é o **Laboratório de Simulação**. À esquerda, um catálogo de cenários de
> stress prontos: disrupção de um fornecedor tier-1, pico promocional tipo
> Black Friday, onda de calor, greve de transporte. Eu escolho um cenário —
> vamos pegar o pico de demanda.
>
> À direita, os controles de stress: **multiplicador de demanda, OTD do
> fornecedor, lead time, horizonte de projeção**. Eu mexo nesses controles e o
> sistema responde **na hora**.
>
> Vejam o que aconteceu nos KPIs: ao subir o multiplicador de demanda, o
> sistema projetou imediatamente como o **nível de serviço cai**, quanto a
> **taxa de ruptura cresce**, e — o número que o financeiro quer ver — quanto
> de **receita fica em risco** naquele horizonte. Isso é um projetor de forma
> fechada, é instantâneo, feito para essa interação de arrastar o controle e
> ver o efeito.
>
> E quando eu quero mais do que uma projeção rápida, eu clico em **'rodar
> simulação'**. Aí entra um **motor de eventos discretos**: ele avança o relógio
> da operação, tick a tick, e simula o comportamento real — cada venda, cada
> stockout, cada disparo de reposição — sob aquele cenário. É o gêmeo digital
> no sentido mais literal: uma operação inteira rodando em paralelo, em silício.
>
> O valor disso para o negócio é uma frase: **testar a decisão antes de
> tomá-la**. Antes de aprovar a campanha, simule. Antes de trocar de
> fornecedor, simule. Antes de mudar a política de estoque, simule. O custo do
> erro na simulação é zero."

💡 **Nota:** é a tela mais visual — gaste tempo aqui. Mexa nos sliders ao vivo,
deixe a plateia ver os KPIs mudando em tempo real. Se o motor de eventos
demorar, fale por cima explicando o que ele faz.

### 4.6 · Análise de Causa Raiz com IA

🎬 **Mostrar:** **AI Root Cause Analysis**. Digitar uma pergunta real, ex.:
*"Por que a loja com maior risco de ruptura está nessa situação?"*

🎤 **Fala:**
> "Esta página é a que democratiza o sistema. Tudo o que mostrei até agora
> exige saber navegar, ler um gráfico, interpretar um ranking. Aqui, **qualquer
> pessoa da operação conversa com o sistema em português, em linguagem
> natural**.
>
> Eu vou digitar uma pergunta de verdade... [digitar]. O que acontece nos
> bastidores: o sistema **classifica a intenção** da pergunta, roteia para o
> **agente especialista** certo — tem um agente de ruptura, um de fornecedor,
> um de simulação —, esse agente **monta o contexto a partir dos dados reais**
> do warehouse, e só então gera a resposta.
>
> E aqui eu volto, pela última vez, ao princípio mais importante da
> apresentação. A inteligência artificial generativa que escreveu essa resposta
> **não calculou nenhum risco**. Ela recebeu os scores e os drivers que os
> modelos estatísticos já tinham calculado, e o trabalho dela foi só **redigir
> a explicação** de forma clara. Modelo prevê, IA explica. Se a IA estiver fora
> do ar, o sistema inteiro continua funcionando — só perde a redação
> automática. O risco nunca dependeu dela."

💡 **Nota:** prepare a pergunta de antemão e teste antes da apresentação. Se a
LLM estiver lenta ou indisponível, tenha um print de uma resposta boa como
plano B, e explique que "a redação é a única parte que depende da IA externa".

### 4.7 · ML Operations Center e System Console

🎬 **Mostrar:** **ML Operations Center**, depois rápido o **System Console**.

🎤 **Fala:**
> "As duas últimas páginas são para o time técnico. O **Centro de Operações de
> ML** é a sala de máquinas: aqui se dispara o **treino dos modelos**, se
> acompanham as **métricas de qualidade** — AUC, precisão, recall — e se
> verifica se os dados e os artefatos estão atualizados.
>
> E o **Console de Sistema** é o diagnóstico de infraestrutura: status do banco
> de dados, do lake de arquivos, das variáveis de ambiente. É o que o
> desenvolvedor olha quando precisa garantir que a fundação está sólida.
>
> Eu mostro essas telas de propósito: este não é um protótipo de tela bonita
> com dado fixo por trás. É um sistema **end-to-end**, com pipeline de dados,
> treino de modelo e operação de verdade."

---

# PARTE III — APROFUNDAMENTO E PROVA

## Bloco 5 · Prova de Valor — o diferencial (4 min)

🎬 **Mostrar:** página **Prova de Valor**. Escolher um cutoff, mostrar os KPIs
agregados e os gráficos de calibração.

🎤 **Fala:**
> "E eu deixei o melhor para o final, de propósito. Porque toda apresentação de
> sistema preditivo enfrenta, mais cedo ou mais tarde, **a pergunta difícil**.
> A pergunta é: *'tudo bem, bonito, o sistema preve — mas como eu sei que a
> previsão presta? E quanto isso vale, em reais?'*
>
> A maioria dos sistemas não responde isso. Esta página responde, e responde
> com método científico. Chama-se **Prova de Valor**.
>
> Funciona assim. Eu escolho uma **data de corte no passado** — digamos, três
> semanas atrás. O sistema então faz uma coisa muito específica: ele **retreina
> os modelos usando apenas os dados que existiam até aquela data**. Ele
> literalmente finge que hoje é três semanas atrás. Não deixa o modelo espiar
> nada do futuro.
>
> Aí ele usa esse modelo para prever — e compara a previsão com **o que de
> fato aconteceu** na janela seguinte, que o modelo nunca viu. Isso se chama
> **backtest walk-forward**, e a métrica que sai dali é honesta: é desempenho
> de verdade, fora da amostra de treino. Sem auto-engano.
>
> Esses gráficos de **calibração** mostram a qualidade da previsão. O da
> esquerda responde: quando o modelo diz 'risco 70%', a ruptura realmente
> acontece em torno de 70% das vezes? Quanto mais perto da diagonal, mais
> confiável. O do meio mostra **com quantos dias de antecedência** o alerta
> dispara — porque um alerta que chega tarde não serve. E o da direita mostra a
> qualidade do **ranking**: dos itens que o modelo colocou no topo, quantos
> realmente ruptaram.
>
> Mas a parte mais poderosa é o **contrafactual**. O sistema simula **dois
> universos paralelos** para o mesmo período.
>
> No **universo A**, o gêmeo digital **não existe** — ninguém faz nada. E a
> gente vê, com dados reais, quantas rupturas aconteceram e quanto de receita
> se perdeu.
>
> No **universo B**, o gêmeo **age**: ele alerta os itens de maior risco, e a
> equipe intervém — faz o pedido extra, a transferência, o desbloqueio. A gente
> aplica uma taxa realista de eficácia, porque nem toda intervenção dá certo, e
> contabiliza o custo de cada ação, inclusive os alarmes falsos.
>
> A diferença entre os dois universos é, literalmente, **o valor do sistema em
> reais**: estas são as **rupturas evitadas**, esta é a **receita salva**, e
> este é o **valor líquido** — já descontado o custo de operar. É a plataforma
> **provando o próprio ROI**, com número auditável, não com promessa de
> vendedor.
>
> E eu quero ser transparente num ponto, porque transparência é o que dá
> credibilidade a tudo isso: no backtest atual, **dois dos cinco modelos — o R1
> e o R4 — generalizam bem**. Os outros três precisam de mais histórico para
> chegar lá. E o sistema **mostra isso abertamente** nesta própria página. Um
> sistema que esconde os modelos fracos não é confiável. Este expõe — e essa é
> exatamente a postura que vocês querem numa ferramenta de decisão."

💡 **Nota do apresentador:** este é o bloco de fechar negócio. Vá devagar no
contrafactual — é o conceito mais sofisticado da apresentação e o de maior
impacto. A transparência sobre R1/R4 não é fraqueza: apresentada com confiança,
ela *aumenta* a credibilidade. Ensaie essa parte final.

---

## Bloco 6 · Aprofundamento técnico (opcional — 5 a 7 min)

> Use este bloco apenas para plateias técnicas (TI, ciência de dados,
> arquitetura). Para plateia de negócio, pule direto para o Bloco 7.

### 6.1 · Arquitetura em camadas

🎬 **Mostrar:** slide do diagrama de arquitetura, ou o System Console.

🎤 **Fala:**
> "Para quem é da área técnica, um corte na arquitetura. O sistema é organizado
> em camadas bem separadas.
>
> A **camada de dados** é um warehouse analítico em **DuckDB** — um banco
> colunar embarcado, sem servidor, sem custo de licença — alimentado por um
> *data lake* em Parquet com o padrão **medallion**: bronze, silver, gold. Os
> dados crus entram no bronze, são tratados no silver, e os scores de risco
> dos modelos vivem no gold.
>
> A **camada de modelos** tem um pacote Python por ruptura, todos herdando da
> mesma estrutura base — feature engineering, trainer, predictor, explainer.
> Isso garante consistência e facilita adicionar uma sexta ruptura no futuro.
>
> A **camada de serviços** é a fronteira entre a interface e o domínio. A
> interface nunca chama um modelo direto; ela conversa com serviços.
>
> E a **interface** é Streamlit, multipage, com componentes reutilizáveis."

### 6.2 · Os modelos de machine learning

🎤 **Fala:**
> "Cada uma das cinco rupturas é prevista por um **ensemble** — uma combinação —
> de dois algoritmos: **XGBoost e LightGBM**, ambos do estado da arte em dados
> tabulares. A predição final é a média das probabilidades dos dois. Usar dois
> algoritmos e combiná-los reduz a variância e o risco de um viés específico de
> um deles.
>
> O treino usa **split temporal**: treina no passado, valida no futuro. Isso
> evita o vazamento de informação — o erro clássico de deixar o modelo aprender
> com dados que, no mundo real, ele não teria no momento da previsão.
>
> A explicabilidade é via **SHAP**, valores de Shapley — uma base teórica
> sólida, da teoria dos jogos, para atribuir a cada variável a sua contribuição
> exata para cada predição individual.
>
> E quando ainda não há modelo treinado, o sistema tem um **modo heurístico**:
> um score estatístico de fallback. A plataforma nunca quebra — ela degrada com
> elegância."

### 6.3 · A metodologia anti-vazamento

🎤 **Fala:**
> "Um ponto que vale destacar para os cientistas de dados na sala. Durante o
> desenvolvimento, descobrimos que três dos modelos tinham um **vazamento de
> target**: a definição do alvo reutilizava, sem querer, uma variável que
> também era usada como feature. O efeito disso é traiçoeiro — a métrica de
> treino fica linda, perto de perfeita, e o modelo desaba quando vê dado novo.
>
> Nós **redesenhamos os alvos** para serem estritamente futuros, e foi
> justamente o **backtest walk-forward** — aquela página de Prova de Valor —
> que expôs o problema. O AUC de treino dizia 0,99; o AUC fora da amostra dizia
> 0,43, que é pior do que cara ou coroa. Esse contraste é o que separa um
> sistema honesto de um sistema que se engana sozinho. Hoje os números de R1 e
> R4 são modestos, mas são **reais**."

💡 **Nota:** este sub-bloco impressiona plateias técnicas porque mostra
maturidade — admitir e corrigir um vazamento é sinal de rigor. Para plateia de
negócio, é detalhe demais; pule.

### 6.4 · Modos de operação e custo

🎤 **Fala:**
> "Por fim, sobre operação. O sistema roda em três modos. **Local**, com seed
> completo, para desenvolvimento. **Cloud leve**, no Streamlit Cloud, com seed
> reduzido — roda sem nenhum banco de dados pago, porque o DuckDB é embarcado.
> E o **modo heurístico**, antes do primeiro treino. A camada de IA generativa
> é **opcional** — sem chave de API, o sistema funciona inteiro, só sem a
> redação automática. O custo de infraestrutura para rodar isto é,
> essencialmente, o custo de uma máquina."

---

## Bloco 7 · Roadmap e visão de futuro (2 min — opcional)

🎤 **Fala:**
> "Onde isto pode chegar. O sistema hoje está completo de ponta a ponta, mas
> roda sobre **dados sintéticos** — um seed gerado com assinaturas realistas das
> cinco rupturas. O primeiro passo é a **conexão com os dados reais** da rede;
> e aqui está a boa notícia: a metodologia não muda, o pipeline não muda. Troca-
> se a fonte de dados, e os números passam a ser os de verdade.
>
> Em seguida: **fortalecer R2, R3 e R5** com mais histórico até generalizarem
> tão bem quanto R1 e R4. Adicionar **novos tipos de ruptura** — a arquitetura
> foi feita para isso, é só mais um pacote. E evoluir as **intervenções
> automáticas**: hoje o sistema alerta e a equipe age; o passo seguinte é o
> sistema **sugerir a ação ótima** — o tamanho exato do pedido extra, a
> transferência específica entre lojas."

---

## Bloco 8 · Encerramento (1,5 min)

🎬 **Mostrar:** voltar à Torre de Controle.

🎤 **Fala:**
> "Vou fechar recolhendo os fios. O que vimos hoje:
>
> Um **gêmeo digital** que faz três coisas. **Espelha** a operação da rede em
> tempo quase real. **Antecipa** cinco tipos de ruptura com modelos de machine
> learning, e — o ponto que repeti de propósito — **explica cada risco** em
> linguagem de negócio, porque previsão sem explicação não vira ação.
>
> Um **laboratório de simulação** que deixa testar qualquer decisão num
> universo paralelo, onde errar não custa nada.
>
> E uma **Prova de Valor** que não pede para vocês acreditarem na minha
> palavra: ela **mede**, em reais e com método científico, o impacto da
> plataforma — e tem a honestidade de mostrar onde os modelos ainda são fortes
> e onde precisam crescer.
>
> A frase que eu queria que ficasse: este sistema tira a operação do modo
> **bombeiro**, apagando incêndio quando o prejuízo já aconteceu, e a coloca no
> modo **meteorologista**, prevendo a tempestade enquanto ainda dá tempo de
> agir.
>
> Está tudo rodando, end-to-end, e vocês podem explorar a interface comigo
> agora. Muito obrigado. Vamos às perguntas."

---

# ANEXOS

## Anexo A — Perguntas prováveis e respostas

| Pergunta | Resposta sugerida |
|----------|-------------------|
| "Os dados são reais?" | "Nesta demonstração, não — é um seed sintético determinístico, com assinaturas causais das cinco rupturas embutidas. A arquitetura está pronta para dados reais; troca-se a fonte e o pipeline não muda." |
| "Quanto tempo para conectar aos nossos dados?" | "O esforço está no mapeamento das fontes para o schema do warehouse — vendas, inventário, reposição, fornecedores. O pipeline de feature, treino e scoring já está pronto e não muda." |
| "Que modelos de IA vocês usam?" | "Para a previsão, um ensemble de XGBoost + LightGBM por ruptura. Para a explicabilidade, SHAP. Para a redação das narrativas, um LLM via Groq — mas essa parte é opcional." |
| "E se a IA generativa errar ou alucinar?" | "Ela não calcula risco — só redige. O número vem dos modelos estatísticos auditáveis. Se a IA generativa estiver fora do ar, o sistema funciona inteiro, só sem a redação automática." |
| "Todos os cinco modelos funcionam bem?" | "No backtest atual, R1 e R4 generalizam bem fora da amostra. R2, R3 e R5 precisam de mais histórico — e o sistema mostra isso abertamente na Prova de Valor. Transparência é parte do design." |
| "Por que o backtest dá números modestos?" | "Porque são honestos. Métricas fora da amostra sempre são menores que as de treino. O valor está em o número ser real e auditável, não inflado." |
| "Qual a stack tecnológica?" | "Streamlit na interface, DuckDB como warehouse, lake Parquet bronze/silver/gold, XGBoost/LightGBM/SHAP no ML, Groq como camada opcional de LLM. Tudo Python." |
| "Quanto custa rodar?" | "Roda local ou em Streamlit Cloud com seed leve. Sem banco de dados pago — DuckDB é embarcado. A LLM é opcional. O custo é essencialmente o de uma máquina." |
| "Isso substitui meu ERP/WMS?" | "Não. É uma camada de inteligência por cima. Ele consome os dados que esses sistemas geram e adiciona predição e explicação — não substitui nenhum deles." |
| "Como o gerente da loja usa isso no dia a dia?" | "Ele abre a Torre de Controle ou o centro da ruptura relevante, vê o ranking de risco e os drivers, e age sobre o topo da lista. Ou, mais simples ainda, pergunta em português na página de IA." |
| "E a simulação, é confiável?" | "O projetor rápido é uma forma fechada calibrada — ótimo para comparar cenários relativamente. O motor de eventos discretos simula a operação tick a tick. São ferramentas de apoio à decisão, não bola de cristal." |
| "Quanto tempo levou para construir?" | [responda com o histórico real do projeto] |

## Anexo B — Glossário de bolso (termos que vão aparecer)

| Termo | Como explicar em uma frase |
|-------|----------------------------|
| **Ruptura** | Qualquer falha na continuidade do abastecimento ou da venda. |
| **Score de risco** | Probabilidade de 0 a 1 de uma entidade sofrer uma ruptura. |
| **Entidade** | A unidade analisada — uma combinação loja-produto, ou um fornecedor. |
| **Gêmeo digital** | Réplica computacional da operação, para observar e simular sem tocar no real. |
| **SHAP** | Técnica que abre a caixa-preta do modelo e mostra o peso de cada variável. |
| **Ensemble** | Combinação de dois algoritmos (XGBoost + LightGBM) para uma previsão mais robusta. |
| **Backtest walk-forward** | Treinar o modelo numa data passada e testá-lo contra o que de fato aconteceu depois. |
| **Contrafactual** | Comparar dois universos — com e sem a ação do gêmeo — para medir o valor gerado. |
| **AUC** | Métrica de 0,5 a 1 que mede a qualidade da previsão (0,5 = sorte; 1 = perfeito). |
| **Lead time** | Tempo entre fazer o pedido e receber a mercadoria. |
| **OTD** | *On-Time Delivery* — percentual de entregas no prazo. |
| **KPI** | Indicador-chave: nível de serviço, taxa de ruptura, receita. |

## Anexo C — Checklist pré-apresentação

**Ambiente (fazer 30 min antes):**
- [ ] `streamlit run app.py` rodando e estável.
- [ ] App aberto na **Torre de Controle**, navegador em ~90–100% de zoom.
- [ ] Seed populado — rodar `python scripts/bootstrap.py --force --full` e
      conferir que os KPIs **não** estão zerados.
- [ ] Filtros limpos: rede inteira, período padrão.
- [ ] Testar a navegação completa uma vez, página por página.

**Conteúdo pré-carregado:**
- [ ] Uma pergunta pronta (copiada) para colar no **AI Root Cause Analysis**.
- [ ] **Prova de Valor** já testada num cutoff com dados (ex.: 21 dias atrás).
- [ ] Um item com drivers SHAP bem visíveis localizado num centro R1–R5.
- [ ] Print de uma resposta boa da IA, como **plano B** se a LLM falhar ao vivo.

**Logística:**
- [ ] Modo não-perturbe / apresentação ativado (sem notificações na tela).
- [ ] Segunda aba do navegador fechada (sem vazar nada).
- [ ] Slide de título pronto para o Bloco 1.
- [ ] Decidir a versão — relâmpago, padrão ou completa — conforme o tempo real.
- [ ] Água por perto. Respirar. Ir devagar.

**Regra de ouro da demo:** se algo travar, **não entre em pânico e não fique em
silêncio**. Explique o que *deveria* aparecer, siga em frente, e volte depois se
der. A plateia perdoa um bug; não perdoa um apresentador perdido.

---

Documentos de apoio: [visão geral](visao-geral-do-gemeo-digital.md) ·
[como o gêmeo funciona](gemeo-digital-funcionamento.md) ·
[arquitetura](arquitetura-e-fluxo-de-dados.md) ·
[catálogo R1–R5](catalogo-das-rupturas-r1-r5.md) ·
[prova de valor](prova-de-valor-backtest-e-contrafactual.md) ·
[interface e módulos](interface-streamlit-e-modulos.md) ·
[glossário](glossario-operacional.md).
