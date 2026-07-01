"""Coleta preços via Yahoo Finance API (gratuita, sem API key).

Tickers usados:
  ZC=F  — CBOT milho (US$/bushel)
  USDBRL=X — Dólar (BRL/USD)
  CCM24.SA — Milho B3 futuro (R$/saca) — atualizar mês 2x/ano
  BGI24.SA — Boi Gordo B3 futuro (R$/@)
"""
import requests
import json
from datetime import datetime, timedelta

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

TICKERS = {
    "cbot": "ZC=F",
    "dolar": "USDBRL=X",
    # B3 agrícola indisponível no Yahoo Finance atualmente.
    # Tentamos alguns tickers alternativos; falham silenciosamente.
    "milho_b3": "CCMN26.SA",
    "boi_b3": "BGIJ26.SA",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_ticker(ticker: str, dias: int = 5) -> list[dict] | None:
    """Retorna lista de {data, abertura, max, min, fechamento} dos últimos N dias."""
    try:
        url = f"{YAHOO_BASE}/{ticker}?interval=1d&range={dias+5}d"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        dados = resp.json()

        result = dados["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        closes = quotes["close"]

        registros = []
        for i, ts in enumerate(timestamps):
            if closes[i] is not None:
                registros.append({
                    "data": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                    "abertura": quotes["open"][i],
                    "maxima": quotes["high"][i],
                    "minima": quotes["low"][i],
                    "fechamento": round(closes[i], 2),
                    "volume": quotes["volume"][i] or 0,
                })
        return registros

    except Exception as e:
        print(f"  ⚠️ Yahoo {ticker}: {e}")
        return None


def _converter_cbot_para_brl(preco_centavos: float, dolar: float) -> float:
    """Converte CBOT (cents/bushel) para R$/saca (60kg).

    Yahoo retorna preço em centavos de dólar (cents/bushel).
    1 bushel de milho = 25.4 kg
    1 saca = 60 kg
    Fator: (60 / 25.4) * dolar ≈ 2.3622 * dolar
    """
    preco_usd = preco_centavos / 100.0
    return round(preco_usd * dolar * (60 / 25.4), 2)


def coletar_todos() -> dict:
    """Coleta todos os preços via Yahoo Finance."""
    from dados.banco import criar_tabelas
    criar_tabelas()
    print("  📡 Coletando preços via Yahoo Finance...")

    resultado = {"dolar": None, "cbot": None, "milho_b3": None, "boi_b3": None}
    cache_series = {}

    for nome, ticker in TICKERS.items():
        dados = _fetch_ticker(ticker, dias=30)
        if dados:
            cache_series[nome] = dados
            resultado[nome] = dados[-1]["fechamento"]
            print(f"    {nome}: {resultado[nome]} (Yahoo)")
        else:
            print(f"    {nome}: ❌ indisponível")

    # Converte CBOT (USD/bushel → R$/saca) se tiver dólar
    if resultado["cbot"] and resultado["dolar"]:
        resultado["cbot_brl"] = _converter_cbot_para_brl(
            resultado["cbot"], resultado["dolar"]
        )
        print(f"    cbot_brl: R$ {resultado['cbot_brl']}/saca")

    # Salva séries históricas (só os que funcionaram)
    _salvar_series(cache_series)
    _atualizar_precos_b3(resultado, cache_series)

    return resultado


def _salvar_series(series: dict):
    from dados import banco
    for nome, registros in series.items():
        if not registros:
            continue
        banco.salvar_precos_yahoo_lote(nome, registros)


def _atualizar_precos_b3(resultado: dict, series: dict):
    from dados import banco
    # Usa CBOT em R$ se disponível, senão CBOT USD
    cbot = resultado.get("cbot_brl") or resultado.get("cbot")
    dolar = resultado.get("dolar")
    # Milho B3 e Boi B3 vêm do Yahoo se disponível, senão None
    milho = resultado.get("milho_b3")
    boi = resultado.get("boi_b3")
    if milho or boi or cbot or dolar:
        banco.salvar_precos(
            milho_b3=milho,
            boi_b3=boi,
            cbot=cbot,
            dolar=dolar,
        )
