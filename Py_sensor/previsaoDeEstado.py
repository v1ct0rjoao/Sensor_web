import serial
import serial.tools.list_ports
import numpy as np
import joblib
import os
import time

# 1. Carregar o modelo treinado, o LabelEncoder e o modelo de detecção de anomalias
caminho_modelos = os.path.join(os.path.dirname(__file__), "modelos")

# Carregar o modelo Random Forest
modelo = joblib.load(os.path.join(caminho_modelos, 'random_forest_model.pkl'))

# Carregar o LabelEncoder
label_encoder = joblib.load(os.path.join(caminho_modelos, 'label_encoder.pkl'))

# Carregar o modelo de detecção de anomalias (One-Class SVM)
ocsvm = joblib.load(os.path.join(caminho_modelos, 'ocsvm_model.pkl'))

# 2. Função para encontrar a porta do Arduino
def encontrar_porta_arduino():
    """
    Lista as portas disponíveis e permite ao usuário escolher a porta do Arduino.
    Retorna a porta selecionada ou None se a escolha for inválida.
    """
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

# 3. Função para conectar à porta serial
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

# 4. Conectar à porta serial
ser = conectar_serial()
if not ser:
    exit()  # Se não conseguir conectar, encerra o programa

# 5. Função para extrair características
def extrair_features(dados):
    """
    Extrai características dos dados coletados.
    """
    return np.array([
        dados.mean(),  # Média
        dados.std(),   # Desvio padrão
        dados.max(),   # Valor máximo
        dados.min(),   # Valor mínimo
        np.percentile(dados, 25),  # Primeiro quartil
        np.percentile(dados, 75),  # Terceiro quartil
    ])

# 6. Função para prever o estado em tempo real e detectar anomalias
def prever_estado_tempo_real():
    print("Iniciando previsão em tempo real...")
    print("Pressione Ctrl+C para parar.")

    # Variável para armazenar o último estado registrado
    ultimo_estado = None

    # Caminho para salvar as mudanças de estado dentro da pasta Py_sensor
    caminho_mudancas = os.path.join(os.path.dirname(__file__), "mudancas_estado.txt")

    # Abrir arquivo para armazenar as mudanças de estado
    with open(caminho_mudancas, 'w') as arquivo:
        arquivo.write("Estado de Maquina:\n")  # Cabeçalho do arquivo

        try:
            # Buffer para armazenar as últimas 200 amostras
            buffer = []

            while True:
                # Lê uma linha da porta serial
                line = ser.readline().decode('utf-8').strip()

                # Verifica se a linha contém um valor numérico
                if line.replace(".", "").isdigit():  # Verifica se é um número válido
                    try:
                        magnitude = float(line)  # Converte para float

                        # Adiciona a magnitude ao buffer
                        buffer.append(magnitude)

                        # Quando o buffer tiver 200 amostras, faz a previsão
                        if len(buffer) == 200:
                            # Extrai as características das 200 amostras
                            features = extrair_features(np.array(buffer))

                            # Fazer a previsão do estado
                            estado_codificado = modelo.predict([features])[0]  # Estado codificado (número)
                            estado_nome = label_encoder.inverse_transform([estado_codificado])[0]  # Mapeia para o nome descritivo

                            # Verificar se é uma anomalia
                            anomalia = ocsvm.predict([features])[0]  # -1 para anomalia, 1 para normal

                            # Verifica se houve mudança de estado
                            if estado_nome != ultimo_estado:
                                # Atualiza o último estado registrado
                                ultimo_estado = estado_nome

                                # Exibe o estado previsto no terminal
                                print(f"Estado Previsto: {estado_nome}")

                                # Armazena o estado previsto no arquivo
                                arquivo.write(f"Estado Previsto: {estado_nome}\n")
                                arquivo.flush()  # Força a gravação no arquivo

                            # Verifica se é uma anomalia
                            if anomalia == -1:
                                # Exibe a anomalia no terminal
                                print("Anomalia Detectada!")

                                # Armazena a anomalia no arquivo
                                arquivo.write("Anomalia Detectada!\n")
                                arquivo.flush()  # Força a gravação no arquivo

                            # Limpa o buffer para coletar novas amostras
                            buffer = []

                    except ValueError:
                        print(f"Erro ao converter valor: {line}")
                else:
                    print(f"Formato inesperado: {line}")

        except KeyboardInterrupt:
            print("Previsão em tempo real interrompida.")
        finally:
            ser.close()

# 7. Iniciar a previsão em tempo real
prever_estado_tempo_real()