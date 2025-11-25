import multiprocessing
import time
import random
import queue
import json
from dataclasses import dataclass

# ----------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE FORMATAÇÃO
# ----------------------------------------------------------------------

def format_tempo_relativo(inicio: float) -> str:
    """
    Recebe o timestamp de início da simulação e devolve uma string mm:ss
    representando o tempo relativo até o momento atual.
    Ex: 3.2s -> "00:03"
    """
    delta = time.time() - inicio
    m, s = divmod(int(delta), 60)
    return f"{m:02d}:{s:02d}"


def prioridade_str(p: int) -> str:
    """
    Converte o número de prioridade para texto.
      1 -> Alta
      2 -> Média
      3 -> Baixa
    """
    return {1: "Alta", 2: "Média", 3: "Baixa"}.get(p, f"{p}")


# ----------------------------------------------------------------------
# MODELOS DE DADOS
# ----------------------------------------------------------------------

@dataclass
class Servidor:
    id: int
    capacidade: int
    status: str
    velocidade: float


@dataclass
class TipoRequisicao:
    id: int
    tipo: str
    peso: int        # usado como prioridade
    tempo_exec: int  # tempo de CPU simulado


@dataclass
class Task:
    id: int
    nome: str
    custo_estimado: int
    criacao: float
    tipo: str = "generico"
    prioridade: int = 2


@dataclass
class Result:
    task_id: int
    worker_id: int
    tempo_espera: float
    tempo_execucao: float


# ----------------------------------------------------------------------
# LEITURA DO JSON
# ----------------------------------------------------------------------

def carregar_config(caminho_arquivo: str):
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


# ----------------------------------------------------------------------
# PROCESSO A: GERADOR DE REQUISIÇÕES
# ----------------------------------------------------------------------

def gerador_requisicoes(tipos_requisicoes, config_extra, fila_entrada, tempo_simulacao, inicio_global):
    """
    Gera requisições em tempo real com base nos tipos definidos no JSON
    e envia para a fila_entrada, que será lida pelo orquestrador.
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
    print(f"[{ts}] [GER] Tempo de simulação esgotado. Enviando sinal de término.")
    fila_entrada.put(None)


# ----------------------------------------------------------------------
# WORKER: SERVIDOR DE INFERÊNCIA
# ----------------------------------------------------------------------

def worker_process(id_worker: int, task_queue, result_queue, inicio_global):
    """
    Cada worker representa um servidor de inferência.
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


# ----------------------------------------------------------------------
# POLÍTICAS DE ESCALONAMENTO
# ----------------------------------------------------------------------

def despachar_tarefas(
    fila_pronta,
    politica,
    task_queues,
    servidores_ativos,
    cargas_servidor,
    indice_rr,
    inicio_simulacao,
):
    """
    Decide QUAL tarefa vai para QUAL servidor, respeitando:
    - capacidade de cada servidor
    - política de escalonamento (round_robin, sjf, prioridade)
    Também loga "migração" quando um servidor preferido está sobrecarregado.
    """
    politica = politica.lower()

    while fila_pronta:
        # Escolhe tarefa conforme política
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
            idx_tarefa = 0  # round_robin: FIFO

        tarefa = fila_pronta.pop(idx_tarefa)

        servidor_escolhido = None
        servidor_preferido = None

        # Escolha de servidor
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
            # SJF / Prioridade -> escolhe servidor menos carregado
            servidores_disponiveis = [
                s for s in servidores_ativos
                if cargas_servidor[s.id] < s.capacidade
            ]
            if not servidores_disponiveis:
                fila_pronta.insert(0, tarefa)
                break

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
        cargas_servidor[sid] += 1

    return indice_rr, cargas_servidor


# ----------------------------------------------------------------------
# PROCESSO B: ORQUESTRADOR
# ----------------------------------------------------------------------

def orquestrador(servidores, tipos_requisicoes, config_extra, fila_entrada, tempo_simulacao, inicio_simulacao):
    servidores_ativos = [s for s in servidores if s.status == "ativo"]

    politica = config_extra.get("politica", "round_robin").lower()
    print(f"[{format_tempo_relativo(inicio_simulacao)}] [ORQ] Política de escalonamento ativa: {politica}\n")

    result_queue = multiprocessing.Queue()

    # Uma fila de tarefas por servidor
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

    while (
        (time.time() - inicio_simulacao) < tempo_simulacao
        or gerador_ativo
        or fila_pronta
        or any(cargas_servidor.values())
    ):
        # 1) Novas requisições do Gerador
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

        # 2) Resultados dos servidores
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
                    if cargas_servidor[resultado.worker_id] > 0:
                        cargas_servidor[resultado.worker_id] -= 1

                ts = format_tempo_relativo(inicio_simulacao)
                print(
                    f"[{ts}] [SRV-{resultado.worker_id}] Concluiu Requisição {resultado.task_id} "
                    f"(espera={resultado.tempo_espera:.2f}s, exec={resultado.tempo_execucao:.2f}s)"
                )
        except queue.Empty:
            pass

        # 3) Aplicar política de escalonamento
        indice_rr, cargas_servidor = despachar_tarefas(
            fila_pronta=fila_pronta,
            politica=politica,
            task_queues=task_queues,
            servidores_ativos=servidores_ativos,
            cargas_servidor=cargas_servidor,
            indice_rr=indice_rr,
            inicio_simulacao=inicio_simulacao,
        )

        time.sleep(0.1)

    # ------------------------------------------------------------------
    # Encerramento
    # ------------------------------------------------------------------
    print(f"\n[{format_tempo_relativo(inicio_simulacao)}] [ORQ] Tempo esgotado. Encerrando sistema...")

    for sid, q in task_queues.items():
        q.put(None)

    for p in workers:
        p.join()

    tempo_total_simulacao = time.time() - inicio_simulacao

    # ------------------------------------------------------------------
    # Relatório Final
    # ------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("                 === Relatório Final ===")
    print("-" * 60)

    if tasks_finalizadas > 0:
        tempo_medio_espera = tempo_espera_total / tasks_finalizadas
        tempo_medio_execucao = tempo_execucao_total / tasks_finalizadas
        tempo_medio_resposta = tempo_resposta_total / tasks_finalizadas
        throughput = tasks_finalizadas / tempo_total_simulacao

        utilizacoes = {
            sid: t_exec / tempo_total_simulacao
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
    else:
        print("Nenhum processamento realizado.")

    print("-" * 60)


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    servidores, tipos_requisicoes, cfg = carregar_config("config.json")
    print("Configuração carregada com sucesso!\n")

    TEMPO_SIMULACAO = 15

    # tempo base usado para todos os timestamps
    inicio_global = time.time()

    fila_entrada = multiprocessing.Queue()

    gerador = multiprocessing.Process(
        target=gerador_requisicoes,
        args=(tipos_requisicoes, cfg, fila_entrada, TEMPO_SIMULACAO, inicio_global),
    )
    gerador.start()

    orquestrador(servidores, tipos_requisicoes, cfg, fila_entrada, TEMPO_SIMULACAO, inicio_global)

    gerador.join()


if __name__ == "__main__":
    main()
