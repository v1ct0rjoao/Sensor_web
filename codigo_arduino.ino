#include <LiquidCrystal.h>
LiquidCrystal lcd(12, 11, 10, 9, 6, 5);

#include <Wire.h>

#define ACELEROMETRO_ESCALA 0 // Sensibilidade do acelerômetro definida para ±2g
#define FILTRO_DIGITAL 2

const int MPU_ENDERECO = 0x68; // Endereço I2C do MPU-6050
int AcX, AcY, AcZ; // Valores do Acelerômetro

long Calib_eixoX, Calib_eixoY, Calib_eixoZ; // Valores de Calibração

float GAcX, GAcY, GAcZ; // Converter acelerômetro para valor de gravidade
float unidade_de_valor_gravidade;

// Variáveis para o filtro passa-baixa
float magnitudeSuavizada = 0;
const float alpha = 0.05; // Fator de suavização (ajuste conforme necessário)

void setup() {
  Wire.begin();
  Iniciar_MPU6050();
  Serial.begin(115200);
  lcd.begin(16, 2);

  Faixa_gravidade();
  Calibrar_MPU6050();
}

void loop() {
  Leitor_dados();
  Calculo_gravidade();
  Calcular_magnitude();
  Visualizar_vibracao();
  delay(100); // Ajuste o delay conforme necessário
}

// INICIAR ===============
void Iniciar_MPU6050() {
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);

  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x6B);
  Wire.write(0x03);
  Wire.endTransmission(true);

  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x1C);
  Wire.write(0x00); // Configura para ±2g
  Wire.endTransmission(true);

  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x1A);
  Wire.write(0x02); // Configura o filtro digital
  Wire.endTransmission(true);
}

// UNIDADE DE GRAVIDADE ================
void Faixa_gravidade() {
  switch (ACELEROMETRO_ESCALA) {
    case 0:
      unidade_de_valor_gravidade = 16384;
      break;
    case 1:
      unidade_de_valor_gravidade = 8192;
      break;
    case 2:
      unidade_de_valor_gravidade = 4096;
      break;
    case 3:
      unidade_de_valor_gravidade = 3276.8;
      break;
  }
}

// CALIBRAÇÃO ================
void Calibrar_MPU6050() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Calibrando...");

  for (int i = 0; i < 300; i++) {
    if (i % 30 == 0) {
      lcd.setCursor(0, 1);
      lcd.print("Progresso: ");
      lcd.print(i / 3);
      lcd.print("%");
    }

    Leitor_dados();
    delay(10);

    Calib_eixoX += AcX;
    Calib_eixoY += AcY;
    Calib_eixoZ += AcZ;
  }

  Calib_eixoX /= 300;
  Calib_eixoY /= 300;
  Calib_eixoZ /= 300;

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Calibracao OK!");
  delay(2000);
}

// LEITOR DOS DADOS ================
void Leitor_dados() {
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ENDERECO, 6, true);

  AcX = Wire.read() << 8 | Wire.read();
  AcY = Wire.read() << 8 | Wire.read();
  AcZ = Wire.read() << 8 | Wire.read();
}

// CALCULO DE GRAVIDADE ================
void Calculo_gravidade() {
  AcX = (AcX - Calib_eixoX);
  AcY = (AcY - Calib_eixoY);
  AcZ = (AcZ - Calib_eixoZ);

  GAcX = AcX / unidade_de_valor_gravidade;
  GAcY = AcY / unidade_de_valor_gravidade;
  GAcZ = AcZ / unidade_de_valor_gravidade;
}

// CALCULAR MAGNITUDE DA VIBRAÇÃO ================
void Calcular_magnitude() {
  // Calcula a magnitude da vibração
  float magnitude = sqrt(GAcX * GAcX + GAcY * GAcY + GAcZ * GAcZ);

  // Aplica o filtro passa-baixa
  magnitudeSuavizada = filtroPassaBaixa(magnitudeSuavizada, magnitude, alpha);
}

// FILTRO PASSA-BAIXA ================
float filtroPassaBaixa(float valorAnterior, float valorAtual, float alpha) {
  return alpha * valorAtual + (1 - alpha) * valorAnterior;
}

// VISUALIZAÇÃO DA VIBRAÇÃO ================
void Visualizar_vibracao() {
  // Exibe a magnitude suavizada no LCD
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Vibracao:");
  lcd.setCursor(0, 1);
  lcd.print(magnitudeSuavizada, 2); // Exibe com 2 casas decimais

  // Exibe a magnitude suavizada no Monitor Serial
  Serial.print("Magnitude da Vibracao: ");
  Serial.println(magnitudeSuavizada, 2);
}
