import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import OneClassSVM  # Para detecção de anomalias
import joblib
import logging
import json

# 1. Configuração de logs
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file_dados = os.path.join(log_dir, 'dados_treinamento.log')
log_file_resultados = os.path.join(log_dir, 'resultados_treinamento.log')

logging.basicConfig(filename=log_file_dados, level=logging.INFO, format='%(asctime)s - %(message)s')
logging.info("Iniciando o processo de treinamento.")

# 2. Função para listar subpastas
def listar_pastas(diretorio):
    subpastas = [pasta for pasta in os.listdir(diretorio) if os.path.isdir(os.path.join(diretorio, pasta))]
    if not subpastas:
        print("Não há subpastas no diretório Py_sensor.")
        logging.error("Não há subpastas no diretório Py_sensor.")
        return None

    print("Selecione uma das pastas seguintes:")
    for i, pasta in enumerate(subpastas, 1):
        print(f"{i}. {pasta}")
    print(f"{len(subpastas) + 1}. Sair")

    opcao = input("Digite o número da pasta desejada ou 'Sair': ")
    if opcao == str(len(subpastas) + 1):
        print("Saindo...")
        return None

    try:
        pasta_selecionada = subpastas[int(opcao) - 1]
        return os.path.join(diretorio, pasta_selecionada)
    except (ValueError, IndexError):
        print("Opção inválida. Tente novamente.")
        return listar_pastas(diretorio)

# 3. Selecionar diretório
diretorio = os.path.dirname(__file__)  # Usa o diretório onde o script está localizado
pasta_selecionada = listar_pastas(diretorio)
if not pasta_selecionada:
    exit()  # Se o usuário escolher "Sair" ou não selecionar uma pasta válida

# 4. Carregar os arquivos CSV da pasta selecionada
arquivos_csv = [f for f in os.listdir(pasta_selecionada) if f.endswith('.csv')]
if not arquivos_csv:
    print(f"Não foram encontrados arquivos CSV na pasta {pasta_selecionada}.")
    logging.error(f"Não foram encontrados arquivos CSV na pasta {pasta_selecionada}.")
    exit()

dados_combinados = pd.DataFrame()

# 5. Carregar os dados e adicionar rótulos baseados no nome do arquivo
for arquivo in arquivos_csv:
    caminho_arquivo = os.path.join(pasta_selecionada, arquivo)
    dados = pd.read_csv(caminho_arquivo)
    
    # Adicionar rótulo baseado no nome do arquivo (usa-se o nome do arquivo para determinar o estado)
    estado = arquivo.split('.')[0]  # Pegando o nome do arquivo sem a extensão
    dados['Condicao'] = estado
    
    dados_combinados = pd.concat([dados_combinados, dados], ignore_index=True)
    logging.info(f"Arquivo {arquivo} carregado com condição {estado}.")

# Verificar o total de amostras
logging.info(f"Total de amostras carregadas: {len(dados_combinados)}")

# 6. Codificar rótulos
label_encoder = LabelEncoder()
dados_combinados['Condicao_encoded'] = label_encoder.fit_transform(dados_combinados['Condicao'])

# 7. Engenharia de Features
def extrair_features(dados):
    return np.array([
        dados.mean(),  # Média
        dados.std(),   # Desvio padrão
        dados.max(),   # Valor máximo
        dados.min(),   # Valor mínimo
        np.percentile(dados, 25),  # Primeiro quartil
        np.percentile(dados, 75),  # Terceiro quartil
    ])

# Aplicar a função de extração de features em janelas de 100 amostras
X = np.array([extrair_features(dados_combinados['Magnitude'].iloc[i:i+100]) for i in range(0, len(dados_combinados), 100)])
y = dados_combinados['Condicao_encoded'].values[::100]  # Rótulos codificados (uma amostra a cada 100)

# Verificar o tamanho dos dados após a extração de features
logging.info(f"Total de janelas de 100 amostras: {len(X)}")

# 8. Dividir os dados em treino e teste
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Verificar o tamanho dos conjuntos de treino e teste
logging.info(f"Tamanho do conjunto de treino: {len(X_train)}")
logging.info(f"Tamanho do conjunto de teste: {len(X_test)}")

# 9. Treinar o modelo com GridSearchCV
param_grid = {
    'n_estimators': [200, 300, 400],  # Mais árvores
    'max_depth': [10, 20, 30],        # Profundidades maiores
    'min_samples_split': [2, 5, 10]   # Valores padrão
}

rf_model = RandomForestClassifier(random_state=42)
grid_search = GridSearchCV(rf_model, param_grid, cv=5, scoring='accuracy')
grid_search.fit(X_train, y_train)

# Melhores hiperparâmetros
best_params = grid_search.best_params_
logging.info(f"Melhores hiperparâmetros: {best_params}")

# 10. Avaliar o modelo
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)

# Salvar resultados no arquivo de log de resultados
logging.basicConfig(filename=log_file_resultados, level=logging.INFO, format='%(asctime)s - %(message)s')
logging.info(f"Acurácia: {accuracy_score(y_test, y_pred)}")
logging.info(f"Relatório de Classificação:\n{classification_report(y_test, y_pred, target_names=label_encoder.classes_)}")
logging.info(f"Matriz de Confusão:\n{confusion_matrix(y_test, y_pred)}")

# 11. Treinar um modelo de detecção de anomalias (One-Class SVM)
ocsvm = OneClassSVM(nu=0.1)  # Ajuste o parâmetro 'nu' conforme necessário
ocsvm.fit(X_train)  # Treina apenas com dados normais

# 12. Criar pasta para salvar o modelo, scaler e label_encoder
diretorio_principal = os.path.dirname(os.path.realpath(__file__))
pasta_modelos = os.path.join(diretorio_principal, "modelos")
os.makedirs(pasta_modelos, exist_ok=True)

# Salvar o modelo
joblib.dump(best_model, os.path.join(pasta_modelos, "random_forest_model.pkl"))

# Salvar o LabelEncoder
joblib.dump(label_encoder, os.path.join(pasta_modelos, "label_encoder.pkl"))

# Salvar o modelo de detecção de anomalias
joblib.dump(ocsvm, os.path.join(pasta_modelos, "ocsvm_model.pkl"))

# Criar e salvar o scaler
scaler = StandardScaler()
scaler.fit(X_train)
joblib.dump(scaler, os.path.join(pasta_modelos, "scaler.pkl"))
logging.info(f"Modelo, scaler e label_encoder salvos na pasta '{pasta_modelos}'.")

# 13. Salvar métricas e hiperparâmetros em um arquivo JSON
with open(os.path.join(pasta_modelos, "metricas.json"), "w") as f:
    json.dump({
        "best_params": best_params,
        "accuracy": accuracy_score(y_test, y_pred),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist()
    }, f, indent=4)
logging.info(f"Métricas e hiperparâmetros salvos na pasta '{pasta_modelos}'.")