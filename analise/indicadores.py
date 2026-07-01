"""Indicadores técnicos para análise de mercado.

Fornece cálculos de SMA, RSI, volatilidade, tendência e sazonalidade
usando dados históricos do banco de dados.
"""
from datetime import date
from dados import banco


# ─── Utilitários ───────────────────────────────────────────

def _extrair_fechamentos(serie: list[dict], chave: str = "fechamento") -> list[float]:
    return [r[chave] for r in serie if r.get(chave) is not None]


# ─── Médias Móveis ─────────────────────────────────────────

def calcular_sma(serie: list[float], periodo: int = 5) -> float | None:
    """Simple Moving Average."""
    if len(serie) < periodo:
        return None
    return round(sum(serie[-periodo:]) / periodo, 2)


def calcular_ema(serie: list[float], periodo: int = 5) -> list[float]:
    """Exponential Moving Average — retorna série completa."""
    if len(serie) < periodo:
        return []
    k = 2 / (periodo + 1)
    ema = [serie[0]]
    for i in range(1, len(serie)):
        ema.append(round(serie[i] * k + ema[-1] * (1 - k), 2))
    return ema


# ─── RSI ────────────────────────────────────────────────────

def calcular_rsi(serie: list[float], periodo: int = 14) -> float | None:
    """Relative Strength Index."""
    if len(serie) < periodo + 1:
        return None
    ganhos, perdas = 0.0, 0.0
    for i in range(-periodo, 0):
        diff = serie[i] - serie[i - 1]
        if diff > 0:
            ganhos += diff
        else:
            perdas -= diff
    if perdas == 0:
        return 100.0
    rs = (ganhos / periodo) / (perdas / periodo)
    return round(100 - (100 / (1 + rs)), 1)


# ─── Volatilidade ───────────────────────────────────────────

def calcular_volatilidade(serie: list[float], periodo: int = 10) -> float | None:
    """Desvio padrão dos retornos diários (volatilidade histórica)."""
    if len(serie) < periodo + 1:
        return None
    retornos = []
    for i in range(-periodo, 0):
        ret = (serie[i] - serie[i - 1]) / serie[i - 1]
        retornos.append(ret)
    media = sum(retornos) / len(retornos)
    var = sum((r - media) ** 2 for r in retornos) / len(retornos)
    return round((var ** 0.5) * 100, 2)


# ─── Tendência ─────────────────────────────────────────────

def analisar_tendencia(serie: list[float]) -> dict:
    """Analisa tendência usando SMA curta vs longa e inclinação."""
    if len(serie) < 5:
        return {"direcao": "neutro", "forca": 0, "inclinacao": 0}

    sma5 = calcular_sma(serie, 5)
    sma20 = calcular_sma(serie, min(20, len(serie)))
    atual = serie[-1]

    # Inclinação (regressão linear simples)
    n = min(10, len(serie))
    xs = list(range(n))
    ys = serie[-n:]
    media_x = sum(xs) / n
    media_y = sum(ys) / n
    inclinacao = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys)) / max(
        sum((x - media_x) ** 2 for x in xs), 0.001
    )

    if sma5 and sma20:
        if sma5 > sma20 and atual > sma5:
            direcao = "alta"
            forca = min(round((sma5 - sma20) / sma20 * 100, 1), 5)
        elif sma5 < sma20 and atual < sma5:
            direcao = "baixa"
            forca = min(round((sma20 - sma5) / sma20 * 100, 1), 5)
        else:
            direcao = "lateral"
            forca = 0
    else:
        direcao = "alta" if inclinacao > 0 else "baixa" if inclinacao < 0 else "lateral"
        forca = min(abs(inclinacao), 3)

    return {
        "direcao": direcao,
        "forca": round(forca, 1),
        "inclinacao": round(inclinacao, 4),
        "sma5": sma5,
        "sma20": sma20,
        "preco_atual": atual,
    }


# ─── Suporte / Resistência ─────────────────────────────────

def calcular_suporte_resistencia(serie: list[float]) -> dict:
    """Encontra níveis de suporte e resistência simples (mín/máx recentes)."""
    if len(serie) < 5:
        return {"suporte": None, "resistencia": None, "range": 0}

    recentes = serie[-20:] if len(serie) >= 20 else serie
    suporte = min(recentes)
    resistencia = max(recentes)
    atual = serie[-1]
    range_pct = round((resistencia - suporte) / suporte * 100, 1) if suporte else 0

    return {
        "suporte": suporte,
        "resistencia": resistencia,
        "range": range_pct,
        "distancia_suporte": round((atual - suporte) / suporte * 100, 1),
        "distancia_resistencia": round((resistencia - atual) / atual * 100, 1),
    }


# ─── Relação Boi/Milho ─────────────────────────────────────

def calcular_relacao_boi_milho(preco_boi: float, preco_milho: float) -> dict:
    """Calcula a Relação de Troca Boi/Milho."""
    if not preco_boi or not preco_milho or preco_milho == 0:
        return {"valor": None, "sinal": "⚪", "resumo": "Dados insuficientes"}

    relacao = round(preco_boi / preco_milho, 2)

    if relacao >= 5.5:
        sinal = "🟢🟢"
        resumo = f"Recorde! Margem altíssima ({relacao} sacas/@) — ótimo p/ confinar"
    elif relacao >= 5.0:
        sinal = "🟢"
        resumo = f"Muito favorável — milho barato, boi caro ({relacao})"
    elif relacao >= 4.0:
        sinal = "🟡"
        resumo = f"Favorável. Acima da média histórica ({relacao})"
    elif relacao >= 3.5:
        sinal = "🟠"
        resumo = f"Neutro pra desfavorável. Confinamento apertado ({relacao})"
    else:
        sinal = "🔴"
        resumo = f"Crítico! Milho caro — confinamento inviável ({relacao})"

    return {"valor": relacao, "sinal": sinal, "resumo": resumo, "media_historica": 4.0}


# ─── Sazonalidade ──────────────────────────────────────────

def _sazonalidade_base(tabela: dict, mes: int = None) -> dict:
    if mes is None:
        mes = date.today().month
    nome_meses = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                  "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    info = tabela.get(mes, ("", ""))
    nome_mes = nome_meses[mes]
    direcao = ("alta" if "⬆️" in info[1] else "baixa" if "⬇️" in info[1] else "neutro")
    return {"mes": nome_mes, "fase": info[0], "sinal": info[1], "direcao": direcao,
            "resumo": f"{nome_mes}: {info[0]}"}


def calcular_sazonalidade_milho(mes: int = None) -> dict:
    return _sazonalidade_base({
        1: ("Safra verão colhendo", "⬇️"), 2: ("Safra verão colhendo", "⬇️"),
        3: ("Fim colheita verão", "⬇️"), 4: ("Plantio safrinha", "➡️"),
        5: ("Safrinha crescendo", "➡️"), 6: ("Início colheita safrinha", "⬇️"),
        7: ("Pico colheita safrinha", "⬇️⬇️"), 8: ("Final colheita safrinha", "⬇️"),
        9: ("Entressafra — menor oferta", "⬆️"), 10: ("Entressafra", "⬆️⬆️"),
        11: ("Plantio safra verão", "⬆️"), 12: ("Safra verão crescendo", "➡️"),
    }, mes)


def calcular_sazonalidade_boi(mes: int = None) -> dict:
    return _sazonalidade_base({
        1: ("Entressafra — águas", "⬆️"), 2: ("Entressafra", "⬆️"),
        3: ("Safra águas — pasto bom", "⬇️"), 4: ("Safra águas", "⬇️"),
        5: ("Safra águas — pior preço", "⬇️⬇️"), 6: ("Fim safra águas", "⬇️"),
        7: ("Seca início", "⬆️"), 8: ("Seca — pasto piora", "⬆️"),
        9: ("Seca — menor oferta", "⬆️"), 10: ("Entressafra início", "⬆️⬆️"),
        11: ("Entressafra — pico", "⬆️⬆️"), 12: ("Entressafra", "⬆️"),
    }, mes)


# ─── Indicador Histórico (10 anos) ──────────────────────────

def calcular_indicador_historico(preco_atual: float, dados_historicos: dict) -> dict:
    """Compara preço atual com médias históricas e retorna score.

    Args:
        preco_atual: Preço atual do ativo
        dados_historicos: Saída de pegar_estatisticas_historicas() para o ticker

    Returns:
        dict com score (-3 a +3), sinal, resumo, variacao_media, percentil
    """
    if not dados_historicos:
        return {"score": 0, "sinal": "neutro", "resumo": "Sem dados históricos"}

    variacao = dados_historicos.get("variacao_media", 0)
    percentil = dados_historicos.get("percentil", 50)
    score = 0

    if variacao > 20:
        score -= 2
    elif variacao > 10:
        score -= 1
    elif variacao < -20:
        score += 2
    elif variacao < -10:
        score += 1

    if percentil > 90:
        score -= 1
    elif percentil < 10:
        score += 1

    if score > 0:
        sinal = "compra_historica"
        resumo = f"Preço {abs(variacao):.1f}% abaixo da média — janela histórica de compra"
    elif score < 0:
        sinal = "venda_historica"
        resumo = f"Preço {abs(variacao):.1f}% acima da média — janela histórica de venda"
    else:
        sinal = "neutro"
        resumo = f"Preço próximo da média histórica (var: {variacao:.1f}%)"

    return {
        "score": score,
        "sinal": sinal,
        "resumo": resumo,
        "variacao_media": variacao,
        "percentil": percentil,
        "media": dados_historicos.get("media"),
        "minimo": dados_historicos.get("minimo"),
        "maximo": dados_historicos.get("maximo"),
    }


# ─── Análise completa ──────────────────────────────────────

def analisar_mercado_completo() -> dict:
    """Retorna análise completa com todos os indicadores para todos ativos."""
    resultado = {
        "milho": {}, "boi": {}, "dolar": {}, "cbot": {},
        "relacao_boi_milho": {}, "sazonalidade": {}, "data": str(date.today()),
    }

    # Séries Yahoo
    series = {}
    for ticker in ["milho_b3", "boi_b3", "cbot", "dolar"]:
        serie = banco.pegar_serie_yahoo(ticker, 60)
        fechamentos = _extrair_fechamentos(serie)
        if fechamentos:
            series[ticker] = {"raw": serie, "close": fechamentos}

    # Séries CEPEA (precos_diarios)
    diarios = banco.pegar_serie_precos_diarios(60)
    if diarios:
        series["cepea"] = {"raw": diarios}

    for ativo in ["milho_b3", "boi_b3", "cbot", "dolar"]:
        dados = series.get(ativo)
        if not dados:
            continue
        fech = dados["close"]
        resultado[ativo.replace("_b3", "") if "_b3" in ativo else ativo] = {
            "atual": fech[-1],
            "tendencia": analisar_tendencia(fech),
            "rsi": calcular_rsi(fech, 14),
            "volatilidade": calcular_volatilidade(fech, 10),
            "sr": calcular_suporte_resistencia(fech),
            "sma5": calcular_sma(fech, 5),
            "sma20": calcular_sma(fech, 20),
        }

    # Relação Boi/Milho
    boi = series.get("boi_b3", {}).get("close", [None])[-1]
    milho = series.get("milho_b3", {}).get("close", [None])[-1]
    if boi and milho:
        resultado["relacao_boi_milho"] = calcular_relacao_boi_milho(boi, milho)

    # Sazonalidade
    resultado["sazonalidade"] = {
        "milho": calcular_sazonalidade_milho(),
        "boi": calcular_sazonalidade_boi(),
    }

    return resultado
