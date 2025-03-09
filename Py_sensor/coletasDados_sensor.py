import serial
import serial.tools.list_ports
import csv
import os
import time
import statistics

# Função para encontrar a porta do Arduino
def encontrar_porta_arduino():
    portas_disponiveis = list(serial.tools.list_ports.comports())
    if not portas_disponiveis:
        print("Nenhuma porta serial encontrada. Conecte o Arduino e tente novamente.")
        return None

    print("Portas disponíveis:")
    for i, porta in enumerate(portas_disponiveis):
        print(f"[{i}] {porta.device} - {porta.description}")

    escolha = input("Digite o número da porta que deseja usar: ")
    try:
        return portas_disponiveis[int(escolha)].device
    except (IndexError, ValueError):
        print("Escolha inválida!")
        return None

# Função para conectar à porta serial
def conectar_serial():
    """
    Tenta conectar à porta serial e retorna o objeto serial.
    Com limite de 5 tentativas para evitar tentativa infinita.
    """
    tentativas = 0
    while tentativas < 5:
        porta = encontrar_porta_arduino()
        if porta:
            try:
                ser = serial.Serial(porta, 115200)
                ser.flushInput()
                print(f"Conectado ao Arduino na porta {porta}.")
                return ser
            except serial.SerialException:
                print("Erro ao conectar à porta serial. Tentando novamente...")
        tentativas += 1
        time.sleep(2)  # Aguarda um tempo antes de tentar novamente

    print("Falha ao conectar após 5 tentativas. Verifique a conexão do Arduino.")
    return None

# Conectar à porta serial
ser = conectar_serial()
if not ser:
    exit()  # Se não conseguir conectar, encerra o programa

# Função para registrar log com mais detalhes
def registrar_log(mensagem):
    """
    Salva eventos importantes em um arquivo de log na pasta Py_sensor.
    """
    log_path = os.path.join("Py_sensor", "log_execucao.txt")
    with open(log_path, "a") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {mensagem}\n")

# Função de filtro de dados usando média móvel
def filtrar_dados(dados, tamanho_filtro=5):
    """
    Aplica um filtro de média móvel simples nos dados coletados.
    """
    if len(dados) < tamanho_filtro:
        return dados
    return [statistics.mean(dados[i:i+tamanho_filtro]) for i in range(len(dados)-tamanho_filtro+1)]

# Função para coletar dados da porta serial e salvar em CSV
def coletar_dados(diretorio, nome_arquivo, num_amostras):
    """
    Coleta os dados da porta serial e salva em um arquivo CSV dentro do diretório escolhido.
    """
    caminho_completo = os.path.join(diretorio, nome_arquivo + ".csv")
    os.makedirs(diretorio, exist_ok=True)  # Cria o diretório se não existir

    try:
        with open(caminho_completo, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Magnitude"])  # Cabeçalho

            print(f"Coletando {num_amostras} amostras...")
            registrar_log(f"Iniciando coleta: {caminho_completo}")
            dados_coletados = []

            try:
                for i in range(num_amostras):
                    line = ser.readline().decode('utf-8').strip()
                    if line.replace(".", "").isdigit():
                        try:
                            magnitude = float(line)
                            dados_coletados.append(magnitude)
                            if len(dados_coletados) >= 5:  # Filtra dados a cada 5 leituras
                                magnitude_filtrada = filtrar_dados(dados_coletados)[-1]
                                magnitude_filtrada = round(magnitude_filtrada, 2)  # Arredonda para 2 casas decimais
                                writer.writerow([magnitude_filtrada])
                                file.flush()
                        except ValueError:
                            continue  # Ignora erros de conversão e continua

                    # Feedback visual de progresso (apenas no terminal)
                    print(f"Amostras coletadas: {i + 1}/{num_amostras}", end='\r')

                print("\nColeta finalizada!")
                registrar_log(f"Coleta finalizada: {caminho_completo}")
            except KeyboardInterrupt:
                print("\nColeta interrompida pelo usuário.")
                registrar_log("Coleta interrompida pelo usuário.")

    except Exception as e:
        print(f"Erro ao salvar os dados no arquivo: {e}")
        registrar_log(f"Erro ao salvar os dados: {e}")

# Menu interativo
while True:
    print("\nMenu Principal")
    print("1 - Criar nova pasta e coletar dados")
    print("2 - Usar pasta existente e coletar dados")
    print("3 - Listar pastas disponíveis")
    print("4 - Sair")
    opcao = input("Escolha uma opção: ")

    if opcao == "1":
        nome_pasta = input("Digite o nome da nova pasta: ")
        diretorio = os.path.join("Py_sensor", nome_pasta)
    elif opcao == "2":
        pastas = [p for p in os.listdir("Py_sensor") if os.path.isdir(os.path.join("Py_sensor", p))]
        if not pastas:
            print("Nenhuma pasta encontrada. Crie uma nova primeiro.")
            continue
        print("Pastas disponíveis:")
        for i, p in enumerate(pastas):
            print(f"[{i}] {p}")
        escolha = input("Escolha o número da pasta: ")
        try:
            diretorio = os.path.join("Py_sensor", pastas[int(escolha)])
        except (IndexError, ValueError):
            print("Escolha inválida!")
            continue
    elif opcao == "3":
        pastas = [p for p in os.listdir("Py_sensor") if os.path.isdir(os.path.join("Py_sensor", p))]
        if pastas:
            print("Pastas disponíveis:")
            for p in pastas:
                print(f"- {p}")
        else:
            print("Nenhuma pasta encontrada.")
        continue
    elif opcao == "4":
        print("Encerrando o programa...")
        registrar_log("Programa encerrado pelo usuário.")
        break
    else:
        print("Opção inválida!")
        continue

    nome_arquivo = input("Digite o nome do arquivo para salvar os dados: ").strip()
    num_amostras = int(input("Digite o número de amostras a serem coletadas: "))
    coletar_dados(diretorio, nome_arquivo, num_amostras)

ser.close()