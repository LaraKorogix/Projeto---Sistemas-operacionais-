import multiprocessing
import time
import random
import queue
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any


def format_tempo_relativo(inicio: float) -> str:
    """
    Formata tempo decorrido desde início da simulação.
    
    Args:
        inicio: Timestamp de início da simulação
        
    Returns:
        String no formato mm:ss
    """
    delta = time.time() - inicio
    m, s = divmod(int(delta), 60)
    return f"{m:02d}:{s:02d}"


def prioridade_str(p: int) -> str:
    """
    Converte código numérico para descrição textual de prioridade.
    
    Args:
        p: Código de prioridade (1=Alta, 2=Média, 3=Baixa)
        
    Returns:
        String descritiva da prioridade
    """
    return {1: "Alta", 2: "Média", 3: "Baixa"}.get(p, f"{p}")


@dataclass
class Servidor:
    """Representa um servidor de processamento no cluster."""
    id: int
    capacidade: int
    status: str
    velocidade: float


@dataclass
class TipoRequisicao:
    """Define características de um tipo de requisição."""
    id: int
    tipo: str
    peso: int
    tempo_exec: int


@dataclass
class Task:
    """Representa uma tarefa de processamento."""
    id: int
    nome: str
    custo_estimado: int
    criacao: float
    tipo: str = "generico"
    prioridade: int = 2


@dataclass
class Result:
    """Armazena resultado de processamento de tarefa."""
    task_id: int
    worker_id: int
    tempo_espera: float
    tempo_execucao: float


def carregar_config(caminho_arquivo: str) -> Tuple[List[Servidor], List[TipoRequisicao], Dict]:
    """
    Carrega configuração do sistema a partir de arquivo JSON.
    
    Args:
        caminho_arquivo: Caminho para arquivo config.json
        
    Returns:
        Tupla (servidores, tipos_requisicoes, config_extra)
    """
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        dados = json.load(f)

    servidores = [
        Servidor(
            id=s["id"],
            capacidade=s["capacidade"],
            status=s.get("status", "ativo"),
            velocidade=s.get("velocidade", 1.0),
        )
        for s in dados["servidores"]
    ]

    tipos_requisicoes = [
        TipoRequisicao(
            id=r["id"],
            tipo=r["tipo"],
            peso=r["peso"],
            tempo_exec=r["tempo_exec"],
        )
        for r in dados["tipos_requisicoes"]
    ]

    config_extra = dados.get("config", {})

    return servidores, tipos_requisicoes, config_extra


def gerador_requisicoes(tipos_requisicoes: List[TipoRequisicao], 
                        config_extra: Dict, 
                        fila_entrada: multiprocessing.Queue,
                        tempo_simulacao: int, 
                        inicio_global: float,
                        num_workers: int):
    """
    Processo gerador que cria requisições em tempo real.
    
    Args:
        tipos_requisicoes: Lista de tipos de requisições disponíveis
        config_extra: Configurações adicionais do sistema
        fila_entrada: Queue para enviar requisições ao orquestrador
        tempo_simulacao: Duração da simulação em segundos
        inicio_global: Timestamp de início para sincronização
        num_workers: Número de workers ativos (para poison pills)
    """
    intervalo_min = config_extra.get("intervalo_chegada_min", 0.5)
    intervalo_max = config_extra.get("intervalo_chegada_max", 2.0)

    inicio_local = time.time()
    task_id = 1

    print(f"[{format_tempo_relativo(inicio_global)}] [GER] Processo de geração de requisições iniciado.")

    while (time.time() - inicio_local) < tempo_simulacao:
        tipo_escolhido = random.choice(tipos_requisicoes)
        agora = time.time()

        task = Task(
            id=task_id,
            nome="Inferencia",
            custo_estimado=tipo_escolhido.tempo_exec,
            criacao=agora,
            tipo=tipo_escolhido.tipo,
            prioridade=tipo_escolhido.peso,
        )

        ts = format_tempo_relativo(inicio_global)
        print(
            f"[{ts}] [GER] Requisição {task_id} criada "
            f"(Tipo: {tipo_escolhido.tipo}, Custo: {tipo_escolhido.tempo_exec}s, "
            f"Prioridade: {prioridade_str(task.prioridade)})"
        )

        fila_entrada.put(task)
        task_id += 1

        time.sleep(random.uniform(intervalo_min, intervalo_max))

    ts = format_tempo_relativo(inicio_global)
    print(f"[{ts}] [GER] Tempo de simulação esgotado. Enviando {num_workers} poison pills.")
    
    for _ in range(num_workers):
        fila_entrada.put(None)


def worker_process(id_worker: int, 
                   task_queue: multiprocessing.Queue,
                   result_queue: multiprocessing.Queue, 
                   inicio_global: float):
    """
    Processo worker que executa tarefas de inferência.
    
    Args:
        id_worker: Identificador único do worker
        task_queue: Queue de entrada para receber tarefas
        result_queue: Queue de saída para enviar resultados
        inicio_global: Timestamp de início para sincronização de logs
    """
    print(f"[{format_tempo_relativo(inicio_global)}] [SRV-{id_worker}] Iniciado e aguardando tarefas...")

    while True:
        try:
            task = task_queue.get(timeout=5)
        except queue.Empty:
            continue

        if task is None:
            print(f"[{format_tempo_relativo(inicio_global)}] [SRV-{id_worker}] Recebida poison pill. Encerrando.")
            break

        start_time = time.time()
        time.sleep(task.custo_estimado)
        end_time = time.time()

        tempo_execucao = end_time - start_time
        tempo_espera = start_time - task.criacao

        resultado = Result(task.id, id_worker, tempo_espera, tempo_execucao)
        result_queue.put(resultado)


def migrar_tarefas_dinamicas(task_queues: Dict[int, multiprocessing.Queue],
                             cargas_servidor: Dict[int, int],
                             servidores_ativos: List[Servidor],
                             inicio_simulacao: float,
                             cargas_lock: Any) -> Tuple[int, Dict[int, int]]: 
    """
    Migra tarefas de servidores sobrecarregados para ociosos.
    
    Args:
        task_queues: Dicionário {servidor_id: Queue de tarefas}
        cargas_servidor: Dicionário {servidor_id: carga atual}
        servidores_ativos: Lista de servidores disponíveis
        inicio_simulacao: Timestamp de início para logs
        cargas_lock: Lock para sincronização de cargas_servidor
        
    Returns:
        Dicionário atualizado de cargas por servidor
    """
    capacidades = {s.id: s.capacidade for s in servidores_ativos}
    
    with cargas_lock:
        cargas_relativas = {
            sid: cargas_servidor[sid] / capacidades[sid]
            for sid in cargas_servidor.keys()
            if capacidades[sid] > 0
        }
    
    if not cargas_relativas or len(cargas_relativas) < 2:
        return cargas_servidor # type: ignore
    
    sid_max = max(cargas_relativas, key=lambda x: cargas_relativas[x])
    sid_min = min(cargas_relativas, key=lambda x: cargas_relativas[x])
    
    diferenca = cargas_relativas[sid_max] - cargas_relativas[sid_min]
    
    if diferenca > 0.5:
        try:
            tarefa = task_queues[sid_max].get_nowait()
            
            task_queues[sid_min].put(tarefa)
            
            with cargas_lock:
                cargas_servidor[sid_max] -= 1
                cargas_servidor[sid_min] += 1
            
            ts = format_tempo_relativo(inicio_simulacao)
            print(
                f"[{ts}] [MIG] Tarefa {tarefa.id} migrada do Servidor {sid_max} "
                f"(carga {cargas_relativas[sid_max]:.0%}) para Servidor {sid_min} "
                f"(carga {cargas_relativas[sid_min]:.0%})"
            )
        except queue.Empty:
            pass
    
    return cargas_servidor # type: ignore


def despachar_tarefas(fila_pronta: List[Task],
                      politica: str,
                      task_queues: Dict[int, multiprocessing.Queue],
                      servidores_ativos: List[Servidor],
                      cargas_servidor: Dict[int, int],
                      indice_rr: int,
                      inicio_simulacao: float,
                      cargas_lock: Any) -> Tuple[int, Dict[int, int]]:
    """
    Distribui tarefas para servidores conforme política de escalonamento.
    
    Args:
        fila_pronta: Lista de tarefas aguardando processamento
        politica: Nome da política ("round_robin", "sjf", "prioridade")
        task_queues: Dicionário {servidor_id: Queue}
        servidores_ativos: Lista de servidores disponíveis
        cargas_servidor: Dicionário {servidor_id: carga atual}
        indice_rr: Índice atual para Round Robin
        inicio_simulacao: Timestamp de início para logs
        cargas_lock: Lock para sincronização
        
    Returns:
        Tupla (indice_rr atualizado, cargas_servidor atualizadas)
    """
    politica = politica.lower()

    while fila_pronta:
        if politica == "sjf":
            idx_tarefa = min(
                range(len(fila_pronta)),
                key=lambda i: fila_pronta[i].custo_estimado
            )
        elif politica == "prioridade":
            idx_tarefa = min(
                range(len(fila_pronta)),
                key=lambda i: fila_pronta[i].prioridade
            )
        else:
            idx_tarefa = 0

        tarefa = fila_pronta.pop(idx_tarefa)

        servidor_escolhido = None
        servidor_preferido = None

        if politica == "round_robin":
            num_servers = len(servidores_ativos)
            if num_servers == 0:
                fila_pronta.insert(0, tarefa)
                break

            tentativas = 0
            while tentativas < num_servers:
                s = servidores_ativos[indice_rr]
                sid = s.id

                if servidor_preferido is None:
                    servidor_preferido = s

                with cargas_lock:
                    if cargas_servidor[sid] < s.capacidade:
                        servidor_escolhido = s
                        indice_rr = (indice_rr + 1) % num_servers
                        break

                indice_rr = (indice_rr + 1) % num_servers
                tentativas += 1

            if servidor_escolhido is None:
                fila_pronta.insert(0, tarefa)
                break

            if servidor_preferido and servidor_escolhido.id != servidor_preferido.id:
                ts = format_tempo_relativo(inicio_simulacao)
                print(
                    f"[{ts}] [ESC-RR] Requisição {tarefa.id} "
                    f"redirecionada do Servidor {servidor_preferido.id} "
                    f"para o Servidor {servidor_escolhido.id} (sobrecarga)."
                )

        else:
            with cargas_lock:
                servidores_disponiveis = [
                    s for s in servidores_ativos
                    if cargas_servidor[s.id] < s.capacidade
                ]
            
            if not servidores_disponiveis:
                fila_pronta.insert(0, tarefa)
                break

            with cargas_lock:
                servidor_escolhido = min(
                    servidores_disponiveis,
                    key=lambda s: cargas_servidor[s.id] / s.capacidade
                )

        sid = servidor_escolhido.id
        ts = format_tempo_relativo(inicio_simulacao)

        print(
            f"[{ts}] [ESC-{politica.upper()}] Requisição {tarefa.id} "
            f"({prioridade_str(tarefa.prioridade)}) atribuída ao Servidor {sid} "
            f"(tipo={tarefa.tipo}, custo={tarefa.custo_estimado}s)"
        )

        task_queues[sid].put(tarefa)
        
        with cargas_lock:
            cargas_servidor[sid] += 1

    return indice_rr, cargas_servidor


def salvar_metricas(metricas: Dict, arquivo: str = "metricas.json"):
    """
    Exporta métricas de desempenho para arquivo JSON.
    
    Args:
        metricas: Dicionário contendo métricas calculadas
        arquivo: Caminho do arquivo de saída
    """
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False)
    print(f"\nMétricas exportadas para {arquivo}")


def orquestrador(servidores: List[Servidor],
                 tipos_requisicoes: List[TipoRequisicao],
                 config_extra: Dict,
                 fila_entrada: multiprocessing.Queue,
                 tempo_simulacao: int,
                 inicio_simulacao: float):
    """
    Processo central de orquestração que gerencia distribuição de tarefas.
    
    Args:
        servidores: Lista de servidores disponíveis
        tipos_requisicoes: Lista de tipos de requisições
        config_extra: Configurações adicionais
        fila_entrada: Queue para receber requisições do gerador
        tempo_simulacao: Duração da simulação em segundos
        inicio_simulacao: Timestamp de início
    """
    servidores_ativos = [s for s in servidores if s.status == "ativo"]

    politica = config_extra.get("politica", "round_robin").lower()
    print(f"[{format_tempo_relativo(inicio_simulacao)}] [ORQ] Política de escalonamento ativa: {politica}\n")

    result_queue = multiprocessing.Queue()
    cargas_lock = multiprocessing.Lock()

    task_queues = {}
    workers = []

    for s in servidores_ativos:
        q = multiprocessing.Queue()
        task_queues[s.id] = q
        p = multiprocessing.Process(
            target=worker_process,
            args=(s.id, q, result_queue, inicio_simulacao)
        )
        p.start()
        workers.append(p)

    print(f"=== BSB Compute: Simulação em Tempo Real ({tempo_simulacao}s) ===\n")
    print("Servidores ativos:")
    for s in servidores_ativos:
        print(f"  - Servidor {s.id} | cap={s.capacidade} | vel={s.velocidade}")
    print()

    fila_pronta = []
    cargas_servidor = {s.id: 0 for s in servidores_ativos}
    tempo_execucao_por_servidor = {s.id: 0.0 for s in servidores_ativos}

    tasks_finalizadas = 0
    tempo_espera_total = 0.0
    tempo_execucao_total = 0.0
    tempo_resposta_total = 0.0
    tempo_espera_max = 0.0

    gerador_ativo = True
    indice_rr = 0
    contador_ciclos = 0

    while (
        (time.time() - inicio_simulacao) < tempo_simulacao
        or gerador_ativo
        or fila_pronta
        or any(cargas_servidor.values()) # type: ignore
    ):
        try:
            while True:
                nova_task = fila_entrada.get_nowait()

                if nova_task is None:
                    gerador_ativo = False
                    print(f"[{format_tempo_relativo(inicio_simulacao)}] [ORQ] Recebeu sinal de término do gerador.")
                    break
                else:
                    ts = format_tempo_relativo(inicio_simulacao)
                    print(
                        f"[{ts}] [ORQ] Requisição {nova_task.id} "
                        f"({prioridade_str(nova_task.prioridade)}) chegou ao orquestrador "
                        f"(Tipo: {nova_task.tipo}, Custo: {nova_task.custo_estimado}s)"
                    )
                    fila_pronta.append(nova_task)
        except queue.Empty:
            pass

        try:
            while True:
                resultado = result_queue.get_nowait()

                tasks_finalizadas += 1
                tempo_espera_total += resultado.tempo_espera
                tempo_execucao_total += resultado.tempo_execucao
                tempo_resposta_total += resultado.tempo_espera + resultado.tempo_execucao

                if resultado.tempo_espera > tempo_espera_max:
                    tempo_espera_max = resultado.tempo_espera

                if resultado.worker_id in tempo_execucao_por_servidor:
                    tempo_execucao_por_servidor[resultado.worker_id] += resultado.tempo_execucao
                    
                    with cargas_lock:
                        if cargas_servidor[resultado.worker_id] > 0:
                            cargas_servidor[resultado.worker_id] -= 1 # type: ignore

                ts = format_tempo_relativo(inicio_simulacao)
                print(
                    f"[{ts}] [SRV-{resultado.worker_id}] Concluiu Requisição {resultado.task_id} "
                    f"(espera={resultado.tempo_espera:.2f}s, exec={resultado.tempo_execucao:.2f}s)"
                )
        except queue.Empty:
            pass

        indice_rr, cargas_servidor = despachar_tarefas(
            fila_pronta=fila_pronta,
            politica=politica,
            task_queues=task_queues,
            servidores_ativos=servidores_ativos,
            cargas_servidor=cargas_servidor, # type: ignore
            indice_rr=indice_rr,
            inicio_simulacao=inicio_simulacao,
            cargas_lock=cargas_lock,
        )

        contador_ciclos += 1
        if contador_ciclos % 5 == 0:
            cargas_servidor = migrar_tarefas_dinamicas(
                task_queues=task_queues,
                cargas_servidor=cargas_servidor,
                servidores_ativos=servidores_ativos,
                inicio_simulacao=inicio_simulacao,
                cargas_lock=cargas_lock,
            )

        time.sleep(0.1)

    print(f"\n[{format_tempo_relativo(inicio_simulacao)}] [ORQ] Tempo esgotado. Encerrando sistema...")

    for sid, q in task_queues.items():
        q.put(None)

    for p in workers:
        p.join()

    tempo_total_simulacao = time.time() - inicio_simulacao

    print("\n" + "-" * 60)
    print("                 === Relatório Final ===")
    print("-" * 60)

    if tasks_finalizadas > 0:
        tempo_medio_espera = tempo_espera_total / tasks_finalizadas
        tempo_medio_execucao = tempo_execucao_total / tasks_finalizadas
        tempo_medio_resposta = tempo_resposta_total / tasks_finalizadas
        throughput = tasks_finalizadas / tempo_total_simulacao

        utilizacoes = {
            sid: min(1.0, t_exec / tempo_total_simulacao)
            for sid, t_exec in tempo_execucao_por_servidor.items()
        }
        utilizacao_media = (
            sum(utilizacoes.values()) / len(utilizacoes) if utilizacoes else 0.0
        )

        print(f"Total de tarefas processadas     : {tasks_finalizadas}")
        print(f"Tempo total de simulação         : {tempo_total_simulacao:.2f}s")
        print(f"Tempo médio de espera na fila    : {tempo_medio_espera:.2f}s")
        print(f"Tempo máximo de espera na fila   : {tempo_espera_max:.2f}s")
        print(f"Tempo médio de execução na CPU   : {tempo_medio_execucao:.2f}s")
        print(f"Tempo médio de resposta          : {tempo_medio_resposta:.2f}s")
        print(f"Throughput                       : {throughput:.2f} tarefas/segundo")
        print()
        print("Utilização aproximada de CPU por servidor:")
        for sid, uso in utilizacoes.items():
            print(f"  - Servidor {sid}: {uso*100:.1f}%")
        print(f"Utilização média da CPU (cluster): {utilizacao_media*100:.1f}%")

        metricas = {
            "politica": politica,
            "tarefas_processadas": tasks_finalizadas,
            "tempo_total_simulacao": round(tempo_total_simulacao, 2),
            "tempo_medio_espera": round(tempo_medio_espera, 2),
            "tempo_maximo_espera": round(tempo_espera_max, 2),
            "tempo_medio_execucao": round(tempo_medio_execucao, 2),
            "tempo_medio_resposta": round(tempo_medio_resposta, 2),
            "throughput": round(throughput, 2),
            "utilizacao_media_cpu": round(utilizacao_media * 100, 1),
            "utilizacao_por_servidor": {
                sid: round(uso * 100, 1) for sid, uso in utilizacoes.items()
            }
        }

        salvar_metricas(metricas)
    else:
        print("Nenhum processamento realizado.")

    print("-" * 60)


def main():
    """Ponto de entrada principal do sistema BSB Compute."""
    servidores, tipos_requisicoes, cfg = carregar_config("config.json")
    print("Configuração carregada com sucesso!\n")

    TEMPO_SIMULACAO = cfg.get("tempo_simulacao", 15)
    inicio_global = time.time()

    fila_entrada = multiprocessing.Queue()
    num_workers = len([s for s in servidores if s.status == "ativo"])

    gerador = multiprocessing.Process(
        target=gerador_requisicoes,
        args=(tipos_requisicoes, cfg, fila_entrada, TEMPO_SIMULACAO, inicio_global, num_workers),
    )
    gerador.start()

    orquestrador(servidores, tipos_requisicoes, cfg, fila_entrada, TEMPO_SIMULACAO, inicio_global)

    gerador.join()


if __name__ == "__main__":
    main()
