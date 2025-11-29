# Relatório Comparativo de Políticas de Escalonamento
## BSB Compute - Análise de Desempenho
**Data de Execução:** 28/11/2025 21:58

## Resultados por Política
### ROUND ROBIN
| Métrica | Média | Desvio Padrão |
|---------|-------|---------------|
| Tarefas Processadas | 15.00 | 0.00 |
| Tempo Médio de Resposta | 1.92s | 0.00s |
| Throughput | 0.87tarefas/s | 0.00tarefas/s |
| Utilização CPU | 52.40% | 0.00% |
| Tempo Médio de Espera | 0.12s | 0.00s |
| Tempo Máximo de Espera | 0.51s | 0.00s |

### SJF
| Métrica | Média | Desvio Padrão |
|---------|-------|---------------|
| Tarefas Processadas | 12.00 | 0.00 |
| Tempo Médio de Resposta | 1.88s | 0.00s |
| Throughput | 0.73tarefas/s | 0.00tarefas/s |
| Utilização CPU | 44.70% | 0.00% |
| Tempo Médio de Espera | 0.05s | 0.00s |
| Tempo Máximo de Espera | 0.09s | 0.00s |

### PRIORIDADE
| Métrica | Média | Desvio Padrão |
|---------|-------|---------------|
| Tarefas Processadas | 12.00 | 0.00 |
| Tempo Médio de Resposta | 2.08s | 0.00s |
| Throughput | 0.73tarefas/s | 0.00tarefas/s |
| Utilização CPU | 48.50% | 0.00% |
| Tempo Médio de Espera | 0.08s | 0.00s |
| Tempo Máximo de Espera | 0.10s | 0.00s |

## Análise Comparativa

- **Melhor Throughput:** round_robin (0.87 tarefas/s)
- **Menor Tempo de Resposta:** sjf (1.88s)
- **Melhor Utilização CPU:** round_robin (52.4%)

## Recomendações

- **Round Robin:** Ideal para ambientes com requisições homogêneas e fairness prioritária
- **SJF:** Recomendado quando tempo de resposta é crítico e custos são previsíveis
- **Prioridade:** Adequado para sistemas com SLA diferenciados por tipo de cliente
