import subprocess
import json
import time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Dict, List

class ComparadorPoliticas:
    def __init__(self, config_base: str = "config.json"):
        self.config_base = config_base
        self.politicas = ["round_robin", "sjf", "prioridade"]
        self.resultados = {}
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
        
        self.cores = {
            "round_robin": "#3498db",
            "sjf": "#2ecc71",
            "prioridade": "#e74c3c"
        }

    def carregar_config(self) -> Dict:
        with open(self.config_base, "r", encoding="utf-8") as f:
            return json.load(f)

    def salvar_config(self, config: Dict):
        with open(self.config_base, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def executar_simulacao(self, politica: str, rodada: int = 1) -> Dict:
        print(f"\n{'='*70}")
        print(f"  Executando: {politica.upper()} - Rodada {rodada}/3")
        print(f"{'='*70}")
        
        config = self.carregar_config()
        config["config"]["politica"] = politica
        self.salvar_config(config)
        
        subprocess.run(["python", "main.py", "--auto"], check=True)
        
        time.sleep(1)
        
        try:
            with open("metricas.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Arquivo metricas.json não encontrado para {politica}")
            return {}

    def executar_multiplas_rodadas(self, num_rodadas: int = 3):
        print("\n" + "="*70)
        print("  COMPARADOR DE POLÍTICAS BSB COMPUTE")
        print("="*70)
        print(f"Políticas a testar: {', '.join(self.politicas)}")
        print(f"Rodadas por política: {num_rodadas}\n")
        
        for politica in self.politicas:
            rodadas = []
            
            for i in range(1, num_rodadas + 1):
                metricas = self.executar_simulacao(politica, i)
                if metricas:
                    rodadas.append(metricas)
                time.sleep(1)
            
            if rodadas:
                self.resultados[politica] = self.calcular_estatisticas(rodadas)
                self.salvar_resultado_individual(politica, self.resultados[politica])
    
    def calcular_estatisticas(self, rodadas: List[Dict]) -> Dict:
        metricas_chave = [
            "tarefas_processadas", "tempo_medio_resposta", "throughput",
            "utilizacao_media_cpu", "tempo_medio_espera", "tempo_maximo_espera"
        ]
        
        estatisticas = {}
        
        for metrica in metricas_chave:
            valores = [r.get(metrica, 0) for r in rodadas]
            
            estatisticas[f"{metrica}_media"] = float(np.mean(valores))
            estatisticas[f"{metrica}_std"] = float(np.std(valores))
            estatisticas[f"{metrica}_min"] = float(np.min(valores))
            estatisticas[f"{metrica}_max"] = float(np.max(valores))
        
        return estatisticas
    
    def salvar_resultado_individual(self, politica: str, stats: Dict):
        arquivo = self.output_dir / f"{politica}_stats.json"
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"\n📊 Estatísticas salvas: {arquivo}")

    def _configurar_ax(self, ax, title, ylabel):
        ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
        ax.set_ylabel(ylabel, fontsize=10, color='#555555')
        ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#dddddd')
        ax.spines['bottom'].set_color('#aaaaaa')
        ax.tick_params(axis='x', colors='#333333')
        ax.tick_params(axis='y', colors='#555555')

    def gerar_graficos(self):
        if not self.resultados:
            print("⚠️  Nenhum resultado disponível para gerar gráficos")
            return
        
        plt.style.use('seaborn-v0_8-whitegrid')
        fig = plt.figure(figsize=(18, 12))
        fig.suptitle('Análise de Performance: Políticas de Escalonamento', fontsize=16, fontweight='bold', y=0.95)
        plt.subplots_adjust(hspace=0.4, wspace=0.3)
        
        self.plot_tempo_resposta(fig.add_subplot(2, 3, 1))
        self.plot_throughput(fig.add_subplot(2, 3, 2))
        self.plot_utilizacao_cpu(fig.add_subplot(2, 3, 3))
        self.plot_tempo_espera(fig.add_subplot(2, 3, 4))
        self.plot_tarefas_processadas(fig.add_subplot(2, 3, 5))
        self.plot_comparacao_geral(fig.add_subplot(2, 3, 6))
        
        arquivo_grafico = self.output_dir / "comparacao_politicas.png"
        plt.savefig(arquivo_grafico, dpi=300, bbox_inches='tight')
        print(f"\n📈 Gráficos salvos: {arquivo_grafico}")
        plt.show()
    
    def plot_tempo_resposta(self, ax):
        politicas = list(self.resultados.keys())
        medias = [self.resultados[p]["tempo_medio_resposta_media"] for p in politicas]
        colors = [self.cores.get(p, '#95a5a6') for p in politicas]
        
        bars = ax.bar(politicas, medias, color=colors, alpha=0.9, width=0.6, zorder=3)
        self._configurar_ax(ax, 'Tempo Médio de Resposta', 'Segundos (s)')
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}s',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    def plot_throughput(self, ax):
        politicas = list(self.resultados.keys())
        medias = [self.resultados[p]["throughput_media"] for p in politicas]
        colors = [self.cores.get(p, '#95a5a6') for p in politicas]
        
        bars = ax.bar(politicas, medias, color=colors, alpha=0.9, width=0.6, zorder=3)
        self._configurar_ax(ax, 'Throughput (Vazão)', 'Tarefas / Segundo')
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    def plot_utilizacao_cpu(self, ax):
        politicas = list(self.resultados.keys())
        medias = [self.resultados[p]["utilizacao_media_cpu_media"] for p in politicas]
        colors = [self.cores.get(p, '#95a5a6') for p in politicas]
        
        bars = ax.bar(politicas, medias, color=colors, alpha=0.9, width=0.6, zorder=3)
        
        ax.axhline(y=80, color='#e74c3c', linestyle=':', linewidth=2, label='Meta Ideal (80%)', zorder=2)
        self._configurar_ax(ax, 'Utilização de CPU', 'Percentual (%)')
        ax.set_ylim(0, 110)
        ax.legend(loc='upper right', frameon=True)
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    def plot_tempo_espera(self, ax):
        politicas = list(self.resultados.keys())
        medias = [self.resultados[p]["tempo_medio_espera_media"] for p in politicas]
        maximos = [self.resultados[p]["tempo_maximo_espera_media"] for p in politicas]
        
        x = np.arange(len(politicas))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, medias, width, label='Média', color='#34495e', alpha=0.8, zorder=3)
        bars2 = ax.bar(x + width/2, maximos, width, label='Máximo', color='#e74c3c', alpha=0.8, zorder=3)
        
        self._configurar_ax(ax, 'Tempo de Espera na Fila', 'Segundos (s)')
        ax.set_xticks(x)
        ax.set_xticklabels(politicas)
        ax.legend(frameon=True, fancybox=True, framealpha=0.9)
        
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{height:.1f}s',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 5), textcoords="offset points",
                            ha='center', va='bottom', fontsize=8, fontweight='bold')

    def plot_tarefas_processadas(self, ax):
        politicas = list(self.resultados.keys())
        medias = [self.resultados[p]["tarefas_processadas_media"] for p in politicas]
        colors = [self.cores.get(p, '#95a5a6') for p in politicas]
        
        bars = ax.bar(politicas, medias, color=colors, alpha=0.9, width=0.6, zorder=3)
        self._configurar_ax(ax, 'Volume de Tarefas', 'Total Processado')
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{int(height)}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 5), textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    def plot_comparacao_geral(self, ax):
        metricas_nomes = ['Throughput', 'CPU (%)', 'Tarefas (Vol)']
        politicas = list(self.resultados.keys())
        
        x = np.arange(len(metricas_nomes))
        width = 0.25
        
        for i, politica in enumerate(politicas):
            throughput_norm = self.resultados[politica]["throughput_media"]
            cpu_norm = self.resultados[politica]["utilizacao_media_cpu_media"] / 100
            tarefas_norm = self.resultados[politica]["tarefas_processadas_media"] / 25 
            
            valores = [throughput_norm, cpu_norm, tarefas_norm]
            offset = width * (i - 1)
            
            ax.bar(x + offset, valores, width, label=politica.replace('_', ' ').title(),
                   color=self.cores.get(politica), alpha=0.85, zorder=3)
        
        self._configurar_ax(ax, 'Comparativo Normalizado (Score)', 'Índice Relativo')
        ax.set_xticks(x)
        ax.set_xticklabels(metricas_nomes)
        ax.legend(loc='upper left', bbox_to_anchor=(0, 1.3), ncol=3, frameon=False, fontsize=9)
        ax.set_ylim(0, max(ax.get_ylim()) * 1.2)

    def gerar_relatorio_markdown(self):
        relatorio = ["# Relatório Comparativo de Políticas de Escalonamento\n"]
        relatorio.append("## BSB Compute - Análise de Desempenho\n")
        relatorio.append(f"**Data de Execução:** {time.strftime('%d/%m/%Y %H:%M')}\n\n")
        
        relatorio.append("## Resultados por Política\n")
        
        for politica in self.politicas:
            if politica not in self.resultados:
                continue
            
            stats = self.resultados[politica]
            
            relatorio.append(f"### {politica.upper().replace('_', ' ')}\n")
            relatorio.append("| Métrica | Média | Desvio Padrão |\n")
            relatorio.append("|---------|-------|---------------|\n")
            
            metricas = [
                ("Tarefas Processadas", "tarefas_processadas", ""),
                ("Tempo Médio de Resposta", "tempo_medio_resposta", "s"),
                ("Throughput", "throughput", "tarefas/s"),
                ("Utilização CPU", "utilizacao_media_cpu", "%"),
                ("Tempo Médio de Espera", "tempo_medio_espera", "s"),
                ("Tempo Máximo de Espera", "tempo_maximo_espera", "s")
            ]
            
            for nome, chave, unidade in metricas:
                media = stats[f"{chave}_media"]
                std = stats[f"{chave}_std"]
                relatorio.append(f"| {nome} | {media:.2f}{unidade} | {std:.2f}{unidade} |\n")
            
            relatorio.append("\n")
        
        relatorio.append("## Análise Comparativa\n\n")
        
        if self.resultados:
            melhor_throughput = max(self.resultados.items(), 
                                   key=lambda x: x[1]["throughput_media"])
            melhor_resposta = min(self.resultados.items(),
                                 key=lambda x: x[1]["tempo_medio_resposta_media"])
            melhor_cpu = max(self.resultados.items(),
                            key=lambda x: x[1]["utilizacao_media_cpu_media"])
            
            relatorio.append(f"- **Melhor Throughput:** {melhor_throughput[0]} "
                            f"({melhor_throughput[1]['throughput_media']:.2f} tarefas/s)\n")
            relatorio.append(f"- **Menor Tempo de Resposta:** {melhor_resposta[0]} "
                            f"({melhor_resposta[1]['tempo_medio_resposta_media']:.2f}s)\n")
            relatorio.append(f"- **Melhor Utilização CPU:** {melhor_cpu[0]} "
                            f"({melhor_cpu[1]['utilizacao_media_cpu_media']:.1f}%)\n\n")
        
        relatorio.append("## Recomendações\n\n")
        relatorio.append("- **Round Robin:** Ideal para ambientes com requisições homogêneas e fairness prioritária\n")
        relatorio.append("- **SJF:** Recomendado quando tempo de resposta é crítico e custos são previsíveis\n")
        relatorio.append("- **Prioridade:** Adequado para sistemas com SLA diferenciados por tipo de cliente\n")
        
        arquivo_relatorio = self.output_dir / "relatorio_comparativo.md"
        with open(arquivo_relatorio, "w", encoding="utf-8") as f:
            f.writelines(relatorio)
        
        print(f"\n📄 Relatório gerado: {arquivo_relatorio}")
    
    def executar_analise_completa(self, num_rodadas: int = 3):
        self.executar_multiplas_rodadas(num_rodadas)
        self.gerar_graficos()
        self.gerar_relatorio_markdown()
        self.exibir_resumo()
    
    def exibir_resumo(self):
        print("\n" + "="*70)
        print("  ANÁLISE COMPLETA FINALIZADA")
        print("="*70)
        print(f"✅ Políticas testadas: {len(self.resultados)}")
        print(f"✅ Arquivos gerados no diretório: {self.output_dir}/")
        print("   - Gráficos comparativos (PNG)")
        print("   - Relatório técnico (Markdown)")
        print("   - Estatísticas por política (JSON)")
        print("="*70)

if __name__ == "__main__":
    comparador = ComparadorPoliticas()
    comparador.executar_analise_completa(num_rodadas=1)