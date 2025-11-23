import multiprocessing
import time
import random
import queue
from dataclasses import dataclass

@dataclass
class Task:
    id: int
    nome: str
    custo_estimado:int  # tempo estimado
    criacao: float  # tempo de criacao


@dataclass
class Result:
    task_id: int
    worker_id: int
    tempo_espera: float # Quanto tempo ficou na fila
    tempo_execucao: float # Quanto tempo rodou na CPU

    
# simula o servidor de interferencia
def worker_process(id_worker: int, task_queue, result_queue):
    
    '''
    Este código roda em um processo separado (CPU dedicada).`
    '''
    print(f'Worker {id_worker} iniciado e aguardando')
    while True:
        try:
            task = task_queue.get(timeout=5)
        except queue.Empty:
            continue # se a fila esta vaiz, tenta denovo
        if task is None:
            break # poison pill

        start_time = time.time()
        
        #simular o processamento
        time.sleep(task.custo_estimado)
        end_time = time.time()
        tempo_execucao = end_time - start_time
        tempo_espera = start_time - task.criacao # turnaround parcial 
        #ipc: envia para o chefe
        resultado = Result(task.id, id_worker, tempo_espera, tempo_execucao)  
        result_queue.put(resultado)
# Kernel
def orquestrador():
    # CONFIG
    NUM_WORKERS = 3
    TEMPO_SIMULACAO = 15 # sistema vai rodar por 15 segundos

    # IPC
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    
    workers = []
    for i in range(NUM_WORKERS):
        p = multiprocessing.Process(target=worker_process, args=(i+1, task_queue, result_queue))
        p.start()
        workers.append(p)
    print(f"=== BSB Compute Fase 2: Simulação em Tempo Real ({TEMPO_SIMULACAO}s) ===\n")
    iniciar_simulacao = time.time()
    tasks_id_gerados = 1

    tasks_finalizadas = 0
    tempo_espera_total = 0
    while (time.time() - start_simulation) < TEMPO_SIMULACAO: # tick do relogio
        # simula chegada aleatoria das tarefas (IO Burst)
        # chance de 30% de chegar uma nova tarefa a cada ciclo 
        if random.random() < 0.3:
            custo = random.randint(1,3)
            nova_task = Task(tasks_id_gerados, "Inferencia", custo, time.time())
            print(f"[Orquestrador] Tarefa {task_id_counter} chegou! (Custo: {custo}s)")
            task_queue.put(nova_task)
            tasks_id_gerados += 1
        # verifica se algum worker finalizou algo (polling nao-bloqueante)
        try:
            # .get_nowait() não trava o loop se a fila estiver vazia
            resultado = result_queue.get_nowait()
            print(f"[Orquestrador] Tarefa {resultado.task_id} finalizada! (Worker: {resultado.worker_id})")
            tasks_finalizadas += 1
            tempo_espera_total += resultado.tempo_espera
        except queue.Empty:
            continue # ninguem terminou nada , vida que segue

        time.sleep(0.5)
    
    # shutdown
    print(' tempo esgotado . encerrando sistema')
    for _ in range(NUM_WORKERS):
        task_queue.put(None)
    for p in workers:
        p.join()
    
    if tasks_finalizadas > 0:
        tempo_medio_espera = tempo_espera_total / tasks_finalizadas
        print(f"\n=== Relatório Final ===")
        print('total processado ', tasks_finalizadas)
        print('tempo medio de espera ', tempo_medio_espera)
    else:
        print('nenhum processamento realizado')

    
    
if __name__ == "__main__":
    orquestrador()
        
    

        