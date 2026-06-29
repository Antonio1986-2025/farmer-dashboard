"""Coleta dados climáticos via OpenWeather API gratuita.

API grátis: 60 chamadas/minuto, dados atuais e previsão 5 dias.
Registre-se em: https://openweathermap.org/api
"""
import requests
from config import OPENWEATHER_API_KEY, REGIÕES_CLIMA


def _coletar_regiao(lat: float, lon: float, nome: str) -> dict | None:
    """Coleta clima de uma região via OpenWeather."""
    if OPENWEATHER_API_KEY == "SUA_CHAVE_AQUI":
        return None

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
        f"&units=metric&lang=pt_br"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        dados = resp.json()

        return {
            "regiao": nome,
            "temperatura": round(dados["main"]["temp"], 1),
            "chuva_mm": dados.get("rain", {}).get("1h", 0) or dados.get("rain", {}).get("3h", 0) or 0,
            "umidade": dados["main"]["humidity"],
            "descricao": dados["weather"][0]["description"],
        }

    except Exception as e:
        print(f"    ⚠️ Clima {nome}: erro ({e})")
        return None


def coletar_todas_regioes() -> list[dict]:
    """Coleta clima de todas as regiões configuradas."""
    print("  🌤️  Coletando clima...")
    resultados = []

    for regiao in REGIÕES_CLIMA:
        dados = _coletar_regiao(regiao["lat"], regiao["lon"], regiao["nome"])
        if dados:
            print(f"    {dados['regiao']}: {dados['temperatura']}°C, "
                  f"{dados['chuva_mm']}mm de chuva, "
                  f"{dados['descricao']}")
            resultados.append(dados)
        else:
            print(f"    {regiao['nome']}: ❌ indisponível")

    if not resultados:
        print("    ⚠️ Clima: configure a OPENWEATHER_API_KEY no config.py")

    return resultados
