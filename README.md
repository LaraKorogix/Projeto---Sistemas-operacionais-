# BSB Compute – Orquestração de Tarefas

Este repositório contém o projeto prático da disciplina **Sistemas Operacionais (2025.2)**, orientado pelo professor **Michel Junio Ferreira Rosa**.  
O objetivo é simular um sistema de **orquestração de tarefas de IA em um cluster de servidores**, aplicando conceitos de **processos concorrentes, escalonamento e comunicação entre processos (IPC)**.

## 🎯 Objetivo Geral

Implementar um **orquestrador de requisições de IA** que distribui tarefas entre vários servidores de forma **justa, eficiente e escalonável**, aproximando o funcionamento de um escalonador real de sistemas operacionais. :contentReference[oaicite:0]{index=0}

## 🧠 Contexto

Com o aumento do uso de **modelos de Inteligência Artificial** (como visão computacional, NLP, reconhecimento de voz etc.), provedores de nuvem precisam lidar com milhares de requisições simultâneas, cada uma com:

- Diferente **prioridade** (alta, média, baixa);
- Diferente **tempo de execução estimado**;
- Diferentes **capacidades de processamento** em cada servidor.

Neste projeto, a empresa fictícia **BSB Compute** utiliza um **orquestrador central (master)** e vários **servidores de inferência (workers)** para:

- Receber requisições de IA;
- Organizar uma **fila de tarefas**;
- Distribuir as requisições de acordo com a **política de escalonamento** escolhida;
- Coletar métricas de desempenho do sistema.

## ⚙️ Funcionalidades previstas

- Criação de um **processo principal (orquestrador)**;
- Criação de **subprocessos/serviços (servidores de inferência)**;
- Fila de requisições com:
  - Prioridade;
  - Tempo estimado de execução;
  - Tipo de tarefa (ex.: visão computacional, NLP, voz);
- Suporte a múltiplas **políticas de escalonamento**:
  - Round Robin (RR);
  - Shortest Job First (SJF);
  - Por prioridade;
- Uso de **IPC** (pipes, sockets ou filas de mensagens) para comunicação entre orquestrador e servidores;
- Geração de **logs em tempo real** com eventos da simulação;
- Cálculo de métricas como:
  - Tempo médio de resposta;
  - Utilização média de CPU;
  - Throughput (tarefas/segundo).

## 🏗️ Arquitetura (visão geral)

- **Orquestrador Central (Master)**  
  - Recebe as requisições;
  - Mantém a fila de tarefas;
  - Aplica a política de escalonamento;
  - Envia tarefas aos servidores e recebe os resultados.

- **Servidores de Inferência (Workers)**  
  - Representam nós do cluster;
  - Executam as tarefas simuladas;
  - Avisam ao orquestrador quando terminam uma requisição, liberando capacidade.

## 🧪 Tecnologias

- Linguagem de programação: **C, Python ou Java** (a definir pelo grupo/conforme implementação);
- Conceitos principais:
  - Processos e subprocessos;
  - Comunicação entre processos (IPC);
  - Escalonamento de processos;
  - Medição de desempenho em sistemas operacionais.

## 📌 Status do Projeto

> ✅ Repositório criado  
> 📝 Etapa atual: definição da arquitetura, linguagem e estrutura inicial do código  
> 🚧 Implementação do orquestrador e servidores: _em desenvolvimento_

## 🗂 Planejamento e Organização

O planejamento das tarefas do projeto é feito em um quadro no Trello, com colunas como:

- 📌 Backlog
- 🛠️ Em andamento
- ✅ Concluído

Link do quadro (somente para o grupo e professor):  
[Quadro do projeto no Trello]([https://trello.com/...](https://trello.com/invite/b/691c57cb56aed87baae550a9/ATTI70f394186d39d56cf86679bdfd1f987f346349F7/projeto-pratico-bsb-compute-orquestracao-de-tarefas))

---

> ℹ️ Este projeto é exclusivamente acadêmico e faz parte da avaliação da disciplina de **Sistemas Operacionais – Centro Universitário de Brasília (UniCEUB)**.
