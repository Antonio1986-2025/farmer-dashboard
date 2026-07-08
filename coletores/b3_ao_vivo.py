"""Coletor de dados AO VIVO: OHLC + Volume para o pregão do dia.

Usa API intraday do Yahoo Finance (15 min) para obter:
  - Abertura, Máxima, Mínima, Atual
  - Volume total do dia
  - Volume nas subidas e descidas
  - Variação percentual

Ativos monitorados:
  - CBOT Milho (ZC=F) — referência global
  - Dólar (USDBRL=X)
  - Milho B3 (CCMN26.SA, fallback Yahoo)
  - Boi Gordo (fonte atual Datagro + Yahoo)
"""

import requests
import json
import time
from datetime import datetime, date

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_intraday(ticker: str, intervalo: str = "15m", dias: int = 2) -> list | None:
    """Busca candles intraday do Yahoo Finance.

    Retorna lista de dicts:
      {ts, abertura, maxima, minima, fechamento, volume}
    ou None se falhar.
    """
    try:
        url = f"{YAHOO_BASE}/{ticker}?interval={intervalo}&range={dias}d"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        dados = resp.json()

        result = dados["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        candles = []
        for i, ts in enumerate(timestamps):
            if quotes["close"][i] is not None:
                candles.append({
                    "ts": ts,
                    "abertura": quotes["open"][i],
                    "maxima": quotes["high"][i],
                    "minima": quotes["low"][i],
                    "fechamento": round(quotes["close"][i], 2),
                    "volume": quotes["volume"][i] or 0,
                })
        return candles if candles else None

    except Exception as e:
        print(f"  ⚠️ Yahoo intraday {ticker}: {e}")
        return None


def _calcular_resumo_pregão(candles: list) -> dict | None:
    """Calcula o resumo do pregão a partir dos candles intraday.

    Retorna:
      abertura, maxima, minima, atual, variacao, volume_total,
      volume_subida, volume_descida, forca_compradora
    """
    if not candles:
        return None

    abertura = candles[0]["abertura"]
    atual = candles[-1]["fechamento"]
    maxima = max(c["maxima"] for c in candles)
    minima = min(c["minima"] for c in candles)
    variacao = round(((atual - abertura) / abertura) * 100, 2)

    volume_total = sum(c["volume"] for c in candles)

    # Volume nas subidas vs descidas
    volume_subida = 0
    volume_descida = 0
    for i in range(1, len(candles)):
        if candles[i]["fechamento"] >= candles[i - 1]["fechamento"]:
            volume_subida += candles[i]["volume"]
        else:
            volume_descida += candles[i]["volume"]

    # Força compradora (percentual de volume em subidas)
    forca_compradora = (
        round((volume_subida / volume_total) * 100, 1)
        if volume_total > 0 else 50.0
    )

    return {
        "abertura": round(abertura, 2),
        "maxima": round(maxima, 2),
        "minima": round(minima, 2),
        "atual": round(atual, 2),
        "variacao": variacao,
        "sinal_variacao": "▲" if variacao > 0 else ("▼" if variacao < 0 else "―"),
        "volume_total": volume_total,
        "volume_subida": volume_subida,
        "volume_descida": volume_descida,
        "forca_compradora": forca_compradora,
        "candles": len(candles),
        "atualizado_em": datetime.now().strftime("%H:%M"),
    }


def _resumo_vazio(ticker: str) -> dict:
    """Resumo vazio para quando o ativo está indisponível."""
    return {
        "disponivel": False,
        "ticker": ticker,
        "atual": None,
        "abertura": None,
        "maxima": None,
        "minima": None,
        "variacao": None,
        "sinal_variacao": "―",
        "volume_total": 0,
        "volume_subida": 0,
        "volume_descida": 0,
        "forca_compradora": 50.0,
        "candles": 0,
        "atualizado_em": datetime.now().strftime("%H:%M"),
    }


def coletar_cbot() -> dict:
    """Coleta dados AO VIVO do CBOT Milho."""
    candles = _fetch_intraday("ZC=F", intervalo="15m", dias=2)
    if not candles:
        return _resumo_vazio("ZC=F")
    resumo = _calcular_resumo_pregão(candles)
    if resumo:
        resumo["disponivel"] = True
        resumo["ticker"] = "ZC=F"
        resumo["nome"] = "CBOT Milho"
    return resumo


def coletar_dolar() -> dict:
    """Coleta dados AO VIVO do Dólar."""
    candles = _fetch_intraday("USDBRL=X", intervalo="15m", dias=2)
    if not candles:
        return _resumo_vazio("USDBRL=X")
    resumo = _calcular_resumo_pregão(candles)
    if resumo:
        resumo["disponivel"] = True
        resumo["ticker"] = "USDBRL=X"
        resumo["nome"] = "Dólar"
    return resumo


def coletar_milho_b3() -> dict | None:
    """Coleta dados do Milho B3 (tenta Yahoo, fallback vazio)."""
    # Tenta ticker do mês corrente
    tickers_tentar = ["CCMN26.SA", "CCMQ26.SA", "CCMU26.SA"]
    for ticker in tickers_tentar:
        candles = _fetch_intraday(ticker, intervalo="15m", dias=2)
        if candles:
            resumo = _calcular_resumo_pregão(candles)
            if resumo:
                resumo["disponivel"] = True
                resumo["ticker"] = ticker
                resumo["nome"] = "Milho B3"
                return resumo
    return None


def coletar_todos() -> dict:
    """Coleta todos os ativos AO VIVO e retorna dict consolidado."""
    print("  📡 Coletando dados AO VIVO (Yahoo intraday)...")

    # Coleta em paralelo simplificada (sequencial)
    cbot = coletar_cbot()
    dolar = coletar_dolar()
    milho_b3 = coletar_milho_b3()
    boi_b3 = None  # Será preenchido pelo Datagro no servidor

    resultado = {
        "data": str(date.today()),
        "atualizado_em": datetime.now().strftime("%H:%M:%S"),
        "cbot": cbot or _resumo_vazio("ZC=F"),
        "dolar": dolar or _resumo_vazio("USDBRL=X"),
        "milho_b3": milho_b3,
        "boi_b3": boi_b3,
    }

    # Log
    disp = lambda r: "✅" if r and r.get("disponivel") else "❌"
    for k in ("cbot", "dolar", "milho_b3", "boi_b3"):
        v = resultado.get(k)
        if v:
            print(f"    {k}: {disp(v)} | "
                  f"A:{v.get('abertura','-')} "
                  f"Atual:{v.get('atual','-')} "
                  f"Vol:{v.get('volume_total',0)}")
        else:
            print(f"    {k}: ❌ indisponível")

    return resultado
