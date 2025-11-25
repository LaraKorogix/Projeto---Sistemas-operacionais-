#  BSB Compute – Orquestração de Tarefas

Este projeto implementa uma simulação de orquestração de requisições de Inteligência Artificial em um cluster de servidores de inferência, desenvolvido para a disciplina de **Sistemas Operacionais**.  
A ideia central é representar a BSB Compute recebendo requisições de IA em tempo real e usando um **orquestrador** para decidir, com base em políticas de escalonamento, qual servidor irá processar cada tarefa.

---

##  Visão geral do sistema

O sistema é composto por três elementos principais, todos executando como processos separados com `multiprocessing`:

- O **gerador de requisições** cria tarefas em tempo real, com intervalos aleatórios, usando os tipos definidos em `config.json`. Cada requisição possui tipo, tempo estimado de execução e prioridade. Essas requisições são enviadas ao orquestrador por meio de uma fila (`multiprocessing.Queue`), que funciona como um canal de IPC entre o processo A (gerador) e o processo B (orquestrador).

- O **orquestrador** funciona como processo master do cluster. Ele recebe as requisições do gerador, registra cada chegada, insere a tarefa em uma fila de prontas e aplica a política de escalonamento escolhida (`round_robin`, `sjf` ou `prioridade`). Em seguida, decide para qual servidor cada tarefa será enviada, respeitando a capacidade (máximo de tarefas simultâneas) e a carga atual de cada servidor. A comunicação com os servidores é feita por filas individuais de tarefas, e os resultados são recebidos em uma fila de resultados compartilhada.

- Os **servidores de inferência (workers)** representam os nós do cluster. Cada servidor é um processo independente que fica bloqueado em sua própria fila, aguardando tarefas. Quando recebe uma `Task`, o servidor registra o horário de início, simula o tempo de CPU com `time.sleep()` usando o campo `custo_estimado` e, ao finalizar, devolve um objeto `Result` ao orquestrador contendo o tempo de espera na fila e o tempo de execução. Esses resultados permitem calcular métricas como tempo médio de resposta e utilização aproximada de CPU.

---

##  Arquitetura em alto nível

O arquivo principal `main.py` concentra a lógica do orquestrador, a criação dos processos de servidores e o disparo do gerador de requisições. A comunicação entre processos é feita exclusivamente com filas (`Queue`), o que simplifica o IPC e evita compartilhamento explícito de memória.

O orquestrador mantém, em memória:

- `fila_pronta` – tarefas que já chegaram e ainda não foram enviadas para nenhum servidor.  
- `cargas_servidor` – mapa que indica quantas tarefas estão ativas em cada servidor (carga atual).  
- `tempo_execucao_por_servidor` – soma do tempo de CPU total gasto por cada servidor, usada para estimar a utilização de CPU.  

A cada iteração, o orquestrador:

1. Lê novas tarefas da fila de entrada (enviadas pelo gerador).  
2. Lê resultados finalizados da fila de resultados (enviados pelos servidores).  
3. Aplica a política de escalonamento para escolher quais tarefas da `fila_pronta` serão despachadas e para quais servidores serão enviadas.  

Tanto o gerador quanto os workers recebem o timestamp de início da simulação e usam isso para imprimir **logs com tempos relativos**, no formato `mm:ss`, organizando a saída de forma mais clara e amigável para análise.

---

##  Arquivo de configuração `config.json`

O comportamento da simulação é parametrizado por um arquivo `config.json`. Um exemplo de configuração é:

```json
{
  "servidores": [
    { "id": 1, "capacidade": 3, "status": "ativo", "velocidade": 1.0 },
    { "id": 2, "capacidade": 2, "status": "ativo", "velocidade": 1.2 },
    { "id": 3, "capacidade": 1, "status": "ativo", "velocidade": 0.8 }
  ],
  "tipos_requisicoes": [
    { "id": 1, "tipo": "visao_computacional", "peso": 3, "tempo_exec": 5 },
    { "id": 2, "tipo": "nlp", "peso": 1, "tempo_exec": 2 },
    { "id": 3, "tipo": "voz", "peso": 2, "tempo_exec": 3 }
  ],
  "config": {
    "intervalo_chegada_min": 0.5,
    "intervalo_chegada_max": 2.0,
    "politica": "sjf"
  }
}
```
## Campos principais

Bloco servidores:

- id: identificador do servidor no cluster.

- capacidade: número máximo de tarefas simultâneas que o servidor suporta antes de ser considerado sobrecarregado.

- status: indica se o servidor participa da simulação ("ativo" ou "inativo").

- velocidade: fator de velocidade (campo já preparado para futuras extensões, não altera diretamente o sleep nesta versão).

Bloco tipos_requisicoes:

- tipo: nome descritivo do tipo de requisição (por exemplo, "visao_computacional", "nlp", "voz").

- peso: usado como prioridade da requisição:

  - 1 → prioridade alta

  - 2 → prioridade média

  - 3 → prioridade baixa

- tempo_exec: tempo estimado de execução na CPU, em segundos, usado diretamente como custo_estimado da Task.

Bloco config:

- intervalo_chegada_min: intervalo mínimo (em segundos) entre duas requisições geradas pelo gerador.

- intervalo_chegada_max: intervalo máximo (em segundos) entre requisições. O gerador sorteia um valor aleatório entre o mínimo e o máximo para cada chegada.

- politica: define qual política de escalonamento será usada pelo orquestrador. Valores suportados:

  - "round_robin"

  - "sjf"

  - "prioridade"

Alterando apenas o valor de "politica" no config.json, é possível comparar o comportamento do sistema sob as três estratégias de escalonamento, sem modificar o código-fonte.

## Políticas de escalonamento implementadas

O orquestrador suporta três políticas de escalonamento, escolhidas a partir de config["politica"].

## Round Robin ("round_robin")

- As tarefas são mantidas em ordem de chegada (fila FIFO).

- Os servidores são percorridos em ordem circular (1 → 2 → 3 → 1 → ...).

- Para cada tarefa, o orquestrador tenta enviá-la ao próximo servidor na ordem que ainda tenha capacidade disponível.

- Se o servidor preferido estiver cheio (carga ≥ capacidade), a tarefa é redirecionada para outro servidor com capacidade livre, registrando um log de redirecionamento (migração por sobrecarga).

- Essa política enfatiza a justiça entre servidores, distribuindo a carga de forma relativamente uniforme.

## Shortest Job First – SJF ("sjf")

- Entre todas as tarefas prontas em fila_pronta, o orquestrador escolhe sempre a tarefa com menor custo_estimado / tempo_exec.

- Depois de escolher a tarefa, o servidor é escolhido com base na menor carga relativa (carga / capacidade).

- Essa política tende a reduzir o tempo médio de resposta, favorecendo tarefas mais curtas.

## Prioridade ("prioridade")

- A escolha leva em conta o campo prioridade da Task, derivado do peso configurado no tipo de requisição.

- Tarefas com prioridade mais alta (número menor) são escolhidas primeiro.

- Em caso de empate, o orquestrador envia a tarefa para o servidor menos carregado, combinando prioridade da requisição com balanceamento de carga.

- Essa política é útil para cenários em que certos tipos de requisição (por exemplo, voz em tempo real) são mais críticos que outros.

## Métricas coletadas e relatório final

Durante a simulação, o orquestrador acumula informações de todas as tarefas processadas:

- Tempo de espera na fila

- Tempo de execução na CPU

- Tempo de resposta (espera + execução)

Com base nesses dados, o relatório final apresenta:

- Total de tarefas processadas

- Tempo total de simulação

- Tempo médio de espera na fila

- Tempo máximo de espera observado

- Tempo médio de execução na CPU

- Tempo médio de resposta

- Throughput em tarefas por segundo (tarefas_processadas / tempo_total_simulacao)

- Utilização aproximada de CPU por servidor (tempo_execucao_servidor / tempo_total_simulacao)

- Utilização média de CPU do cluster (média das utilizações dos servidores)

Essas métricas permitem comparar quantitativamente as três políticas de escalonamento, bastando alterar a política no config.json, executar novamente e observar as diferenças.

## Estrutura do projeto
```text
Projeto---Sistemas-operacionais-/
  main.py        # código-fonte principal: orquestrador, gerador e workers
  config.json    # arquivo de configuração da simulação
  README.md      # documentação do projeto
```

- main.py contém a implementação dos processos, IPC, escalonamento e métricas.

- config.json define servidores, tipos de requisição e parâmetros da simulação.

- README.md explica o funcionamento do sistema e como executar.

## Como executar a simulação

- Instale o Python 3 (se ainda não tiver instalado).

- Garanta que main.py e config.json estejam na mesma pasta.

- (Opcional) Edite o config.json para ajustar:

- quantidade e capacidade dos servidores,

- tipos de requisição,

- intervalo de chegada,

- política de escalonamento ("round_robin", "sjf", "prioridade").

- No terminal, navegue até a pasta do projeto e execute:

    - python main.py


Durante a execução você verá:

- Mensagens do gerador criando requisições.

- Mensagens do orquestrador recebendo, enfileirando e despachando essas requisições.

- Mensagens dos servidores indicando a conclusão de cada tarefa com tempos de espera e execução.

- Ao final, o relatório com as métricas de desempenho será exibido no console.


## Autoria

Projeto desenvolvido como prática da disciplina de Sistemas Operacionais, simulando um ambiente simplificado de orquestração de tarefas da BSB Compute e explorando conceitos de processos concorrentes, IPC e políticas de escalonamento.
