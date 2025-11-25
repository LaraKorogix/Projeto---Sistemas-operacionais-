# BSB Compute – Orquestração de Tarefas com Políticas de Escalonamento

Projeto prático da disciplina de Sistemas Operacionais, simulando a orquestração de requisições de IA em um cluster de servidores de inferência.

O objetivo é **distribuir requisições** entre vários servidores (processos) usando **diferentes políticas de escalonamento**, monitorando tempos de espera, execução e utilização aproximada da CPU.

---

## 🎯 Objetivos do Projeto

- Simular um **orquestrador central (master)** que distribui requisições de IA para servidores de inferência.
- Utilizar **IPC (comunicação entre processos)** via `multiprocessing.Queue`.
- Implementar e testar **três políticas de escalonamento**:
  - Round Robin (RR)
  - Shortest Job First (SJF)
  - Prioridade
- Medir **desempenho do cluster**:
  - tempo médio e máximo de espera,
  - tempo médio de execução,
  - tempo médio de resposta,
  - throughput,
  - utilização aproximada da CPU por servidor.
- Simular **chegada em tempo real** de novas requisições, com intervalo aleatório.

---

## 🧱 Arquitetura do Sistema

O sistema é dividido em três tipos principais de processos:

### 1. Orquestrador (Processo B)

- Lê as requisições geradas em tempo real.
- Mantém uma **fila de tarefas prontas**.
- Aplica a **política de escalonamento** configurada (`round_robin`, `sjf` ou `prioridade`).
- Distribui as tarefas entre os servidores, respeitando a **capacidade** de cada um.
- Coleta os resultados e atualiza as métricas de desempenho.

### 2. Gerador de Requisições (Processo A)

- Gera requisições de forma contínua e aleatória ao longo da simulação.
- Usa os **tipos de requisição** definidos no JSON (`tipos_requisicoes`).
- Define:
  - tipo da requisição,
  - tempo estimado de execução (`tempo_exec`),
  - prioridade (mapeada a partir do `peso`).
- Envia essas requisições para o orquestrador via uma `Queue`.

### 3. Servidores de Inferência (Workers)

- Cada servidor é um **processo separado**.
- Cada servidor possui:
  - `id`,
  - `capacidade` (quantas tarefas suporta simultaneamente),
  - `status` (`ativo` ou `inativo`),
  - `velocidade` (fator para extensões futuras).
- Lê sua própria fila de tarefas, simula o processamento com `time.sleep()` e devolve um `Result` ao orquestrador.

---

## 📂 Estrutura de Arquivos

```text
Projeto---Sistemas-operacionais-/
├── main.py        # implementação do orquestrador, gerador e workers
├── config.json    # configurações de servidores, tipos de requisições e política
└── README.md      # este arquivo
