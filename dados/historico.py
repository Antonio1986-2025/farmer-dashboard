"""Dados históricos de preços (10 anos).

Baixa séries longas do Yahoo Finance e calcula estatísticas
para comparação com preços atuais e sazonalidade real.
"""
import requests
from datetime import date, datetime
from collections import defaultdict

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

TICKERS = {
    "cbot": "ZC=F",
    "dolar": "USDBRL=X",
}


def baixar_historico(ticker_yahoo: str, anos: int = 10) -> list[dict]:
    """Baixa dados OHLCV do Yahoo Finance por um período longo."""
    try:
        url = f"{YAHOO_BASE}/{ticker_yahoo}?interval=1d&range={anos}y"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        dados = resp.json()
        result = dados["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        registros = []
        for i, ts in enumerate(timestamps):
            if quotes["close"][i] is not None:
                data_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                registros.append({
                    "data": data_str,
                    "abertura": quotes["open"][i],
                    "maxima": quotes["high"][i],
                    "minima": quotes["low"][i],
                    "fechamento": round(quotes["close"][i], 6),
                    "volume": quotes["volume"][i] or 0,
                })
        return registros
    except Exception as e:
        print(f"  ⚠️ Yahoo histórico {ticker_yahoo}: {e}")
        return []


def salvar_historico(ticker_nome: str, dados: list[dict]):
    """Salva lote de dados históricos no banco."""
    from dados import banco
    banco.salvar_precos_yahoo_lote(ticker_nome, dados)


def carregar_historico_startup():
    """Baixa e salva 10 anos de dados para cada ticker disponível."""
    print("  📜 Carregando dados históricos (10 anos)...")
    for nome, ticker_yahoo in TICKERS.items():
        dados = baixar_historico(ticker_yahoo)
        if dados:
            salvar_historico(nome, dados)
            print(f"    ✅ {nome}: {len(dados)} registros ({dados[0]['data']} a {dados[-1]['data']})")
        else:
            print(f"    ❌ {nome}: indisponível")


def pegar_estatisticas_historicas() -> dict:
    """Calcula médias mensais, percentis e faixas para cada ticker."""
    from dados import banco
    resultado = {}
    mes_atual = date.today().month
    for ticker in ["cbot", "dolar", "milho_b3", "boi_b3"]:
        series = banco.pegar_serie_yahoo(ticker, 3650)
        if not series:
            continue
        fechamentos = [r["fechamento"] for r in series if r.get("fechamento")]
        if len(fechamentos) < 20:
            continue
        atual = fechamentos[-1]
        minimo = min(fechamentos)
        maximo = max(fechamentos)
        media = round(sum(fechamentos) / len(fechamentos), 4)
        abaixo = sum(1 for v in fechamentos if v < atual)
        percentil = round(abaixo / len(fechamentos) * 100, 1)
        variacao_media = round((atual - media) / media * 100, 1)
        medias_mensais = defaultdict(list)
        for r in series:
            v = r.get("fechamento")
            if v is not None:
                try:
                    medias_mensais[date.fromisoformat(r["data"]).month].append(v)
                except (ValueError, TypeError):
                    continue
        medias = {mes: round(sum(vs) / len(vs), 4) for mes, vs in medias_mensais.items()}
        resultado[ticker] = {
            "atual": atual,
            "minimo": minimo,
            "maximo": maximo,
            "media": media,
            "total_dias": len(fechamentos),
            "percentil": percentil,
            "variacao_media": variacao_media,
            "acima_media": atual > media,
            "media_mes_atual": medias.get(mes_atual),
            "medias_mensais": medias,
        }
    return resultado
