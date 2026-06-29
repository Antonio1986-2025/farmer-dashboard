import os
from pathlib import Path

PASTA_PROJETO = Path(__file__).parent
PASTA_DADOS = PASTA_PROJETO / "dados"
BANCO_PATH = PASTA_DADOS / "historico.db"

# ─── URLs de coleta ─────────────────────────────────────────
# Investing.com (dólar, CBOT, milho B3, boi B3)
URL_DOLAR = "https://www.investing.com/currencies/usd-brl"
URL_CBOT = "https://www.investing.com/commodities/us-corn"
URL_MILHO_B3 = "https://www.investing.com/commodities/us-corn?cid=964522"
URL_BOI_B3 = "https://www.investing.com/commodities/brazilian-cattle-futures"

# CEPEA (milho físico e arroba do boi)
URL_CEPEA_MILHO = "https://www.cepea.esalq.usp.br/br/indicador/milho.aspx"
URL_CEPEA_BOI = "https://www.cepea.esalq.usp.br/br/indicador/boi-gordo.aspx"

# ─── OpenWeather (clima) ────────────────────────────────────
# Registre-se grátis em: https://openweathermap.org/api
# Pode ser configurado via variável de ambiente (Railway/ .env)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "SUA_CHAVE_AQUI")

# Regiões que impactam milho e boi
REGIÕES_CLIMA = [
    {"nome": "Sorriso-MT",   "lat": -12.54, "lon": -55.71},
    {"nome": "Campo Grande-MS", "lat": -20.44, "lon": -54.65},
    {"nome": "Uberaba-MG",   "lat": -19.75, "lon": -47.93},
    {"nome": "Rio Verde-GO", "lat": -17.79, "lon": -50.92},
]

# ─── Evolution API (WhatsApp) ───────────────────────────────
# Instale a Evolution API via Docker ou use uma hospedada
# Todos podem ser configurados via variáveis de ambiente
EVO_API_URL = os.getenv("EVO_API_URL", "http://localhost:8080")
EVO_API_KEY = os.getenv("EVO_API_KEY", "")
EVO_INSTANCE = os.getenv("EVO_INSTANCE", "farmer")
SEU_NUMERO = os.getenv("SEU_NUMERO", "553199999999")

# ─── Configurações de análise ───────────────────────────────
# Limites para alertas
LIMITE_RELACAO_BOI_MILHO_ALTA = 5.0
LIMITE_RELACAO_BOI_MILHO_BAIXA = 3.0
LIMITE_CBOT_VARIACAO_ALERTA = 1.5  # % de variação do CBOT p/ alertar
LIMITE_DOLAR_VARIACAO_ALERTA = 1.0  # % de variação do dólar p/ alertar

# ─── Configurações Railway ──────────────────────────────────
PORT = int(os.getenv("PORT", "8000"))
