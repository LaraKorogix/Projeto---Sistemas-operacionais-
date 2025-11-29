import os
import sys
import subprocess
import time
from comparador import ComparadorPoliticas

class MenuTerminal:
    def __init__(self):
        self.is_windows = os.name == 'nt'

    def _get_key(self):
        """Lê tecla pressionada. Retorna 'up', 'down', 'enter' ou 'esc'."""
        if self.is_windows:
            import msvcrt
            key = msvcrt.getch()
            if key == b'\xe0':
                key = msvcrt.getch()
                return {b'H': 'up', b'P': 'down'}.get(key, '')
            if key == b'\x1b': 
                return 'esc'
            return {b'\r': 'enter'}.get(key, '')
        else:
  
            import tty, termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == '\x1b':
 
                    return 'esc' 
                   
                return {'\n': 'enter', '\r': 'enter'}.get(ch, '')
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def selecionar(self, titulo: str, opcoes: list) -> int:
        """
        Retorna o índice da opção escolhida ou -1 se pressionar ESC.
        """
        idx = 0
        print(f"\n{titulo}")
        print("\033[?25l", end="") 
        
        for _ in opcoes: print() 
        print(f"\033[{len(opcoes)}A", end="") 

        try:
            while True:
                for i, op in enumerate(opcoes):
                    cor = "\033[96m" if i == idx else "\033[0m" 
                    prefixo = " ➤ " if i == idx else "   "
                    print(f"\r\033[K{cor}{prefixo}{op}\033[0m")
                
                print(f"\033[{len(opcoes)}A", end="")
                
                k = self._get_key()
                
                if k == 'esc':
                    print(f"\033[{len(opcoes)}B", end="")
                    return -1
                elif k == 'up' and idx > 0: 
                    idx -= 1
                elif k == 'down' and idx < len(opcoes)-1: 
                    idx += 1
                elif k == 'enter':
                    print(f"\033[{len(opcoes)}B", end="")
                    return idx
                    
        finally:
            print("\033[?25h", end="") 

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def pausar_retorno():
    print("\n" + "="*50)
    input("  Pressione [ENTER] para voltar ao menu...")

def main():
    menu = MenuTerminal()
    
    while True: 
        limpar_tela()
        print("="*50)
        print("      BSB COMPUTE - LAUNCHER SYSTEM")
        print("="*50)
        print(" Use as setas para navegar, Enter para confirmar.")
        print(" Pressione ESC para sair.")
        print("-" * 50)
        
        opcoes = [
            "Simulação Única (Modo Visual)",
            "Comparativo de Performance (Benchmark)",
            "Sair do Sistema"
        ]
        
        escolha = menu.selecionar("Menu Principal:", opcoes)
    
        
        if escolha == -1 or escolha == 2: 
            print("\nEncerrando BSB Compute. Até logo!")
            sys.exit(0)
            
        elif escolha == 0:
            try:
                subprocess.run(["python", "main.py"])
                pausar_retorno()
            except KeyboardInterrupt:
                pass
                
        elif escolha == 1:
            # Modo Comparativo
            print("\n--- Configuração do Benchmark ---")
            try:
                r_input = input("Quantas rodadas por política? [Enter = 3]: ").strip()
                rodadas = int(r_input) if r_input.isdigit() else 3
                
                print(f"\nIniciando análise com {rodadas} rodadas...")
                time.sleep(1)
                
                comp = ComparadorPoliticas()
                comp.executar_analise_completa(num_rodadas=rodadas)
                
                pausar_retorno()
                
            except KeyboardInterrupt:
                print("\nOperação cancelada.")
                time.sleep(1)

if __name__ == "__main__":
    if os.name == 'nt': os.system('color')
    try:
        main()
    except KeyboardInterrupt:
        print("\nSaída forçada.")