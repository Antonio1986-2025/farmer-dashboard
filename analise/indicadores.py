"""Cálculo de indicadores e métricas do mercado."""
from datetime import date
from dados import banco


def calcular_relacao_boi_milho(preco_boi: float, preco_milho: float) -> dict:
    """Calcula a Relação de Troca Boi/Milho.

    Fórmula: R$ arroba do boi ÷ R$ saca do milho
    Média histórica: ~4,0 sacas por arroba
    """
    if not preco_boi or not preco_milho or preco_milho == 0:
        return {"valor": None, "sinal": "⚪", "resumo": "Dados insuficientes"}

    relacao = round(preco_boi / preco_milho, 2)

    if relacao >= 5.5:
        sinal = "🟢🟢"
        resumo = f"Recorde histórico! Confinamento com margem altíssima ({relacao} sacas/@)"
    elif relacao >= 5.0:
        sinal = "🟢"
        resumo = f"Muito favorável. Milho barato, boi caro — ótimo para confinamento"
    elif relacao >= 4.0:
        sinal = "🟡"
        resumo = f"Favorável. Acima da média histórica (4,0). Confinamento viável"
    elif relacao >= 3.5:
        sinal = "🟠"
        resumo = f"Neutro pra desfavorável. Abaixo da média. Confinamento apertado"
    else:
        sinal = "🔴"
        resumo = f"Crítico! Milho caro demais — confinamento inviável"

    return {
        "valor": relacao,
        "sinal": sinal,
        "resumo": resumo,
        "media_historica": 4.0,
    }


def calcular_sazonalidade_milho(mes: int = None) -> dict:
    """Retorna a pressão sazonal do milho baseada no mês."""
    if mes is None:
        mes = date.today().month

    tabela = {
        1:  ("Safra verão colhendo", "⬇️"),
        2:  ("Safra verão colhendo", "⬇️"),
        3:  ("Fim colheita verão", "⬇️"),
        4:  ("Plantio safrinha", "➡️"),
        5:  ("Safrinha se desenvolvendo", "➡️"),
        6:  ("Início colheita safrinha", "⬇️"),
        7:  ("Pico colheita safrinha", "⬇️⬇️"),
        8:  ("Final colheita safrinha", "⬇️"),
        9:  ("Entressafra — menor oferta", "⬆️"),
        10: ("Entressafra", "⬆️⬆️"),
        11: ("Plantio safra verão", "⬆️"),
        12: ("Safra verão crescendo", "➡️"),
    }

    nome_meses = [
        "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez"
    ]
    info = tabela.get(mes, ("", ""))
    nome_mes = nome_meses[mes]

    return {
        "mes": nome_mes,
        "fase": info[0],
        "sinal": info[1],
        "resumo": f"{nome_mes}: {info[0]} {'— tendência de ' + ('🔻 queda' if '⬇️' in info[1] else '🔺 alta' if '⬆️' in info[1] else '➡️ estabilidade')}",
    }


def calcular_sazonalidade_boi(mes: int = None) -> dict:
    """Retorna a pressão sazonal do boi gordo baseada no mês."""
    if mes is None:
        mes = date.today().month

    tabela = {
        1:  ("Entressafra — águas", "⬆️"),
        2:  ("Entressafra", "⬆️"),
        3:  ("Safra águas — pasto bom", "⬇️"),
        4:  ("Safra águas", "⬇️"),
        5:  ("Safra águas — pior preço", "⬇️⬇️"),
        6:  ("Fim safra águas", "⬇️"),
        7:  ("Seca início", "⬆️"),
        8:  ("Seca — pasto piora", "⬆️"),
        9:  ("Seca — menor oferta", "⬆️"),
        10: ("Entressafra início", "⬆️⬆️"),
        11: ("Entressafra — pico do ano", "⬆️⬆️"),
        12: ("Entressafra", "⬆️"),
    }

    nome_meses = [
        "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez"
    ]
    info = tabela.get(mes, ("", ""))
    nome_mes = nome_meses[mes]

    return {
        "mes": nome_mes,
        "fase": info[0],
        "sinal": info[1],
        "resumo": f"{nome_mes}: {info[0]} {'— tendência de ' + ('🔺 alta' if '⬆️' in info[1] else '🔻 queda' if '⬇️' in info[1] else '➡️ estabilidade')}",
    }


def analisar_variacao(valor_atual: float | None, valor_anterior: float | None,
                      nome: str, limite_alerta: float = 2.0) -> dict | None:
    """Compara valor atual com o último disponível e retorna análise."""
    if not valor_atual or not valor_anterior or valor_anterior == 0:
        return None

    variacao = round((valor_atual - valor_anterior) / valor_anterior * 100, 2)

    if abs(variacao) >= limite_alerta:
        sinal = "🔴" if variacao < 0 else "🟢"
        resumo = f"{nome} variou {variacao:+.2f}% — acima do limite de {limite_alerta}%"
    elif abs(variacao) >= limite_alerta / 2:
        sinal = "🟡"
        resumo = f"{nome} variou {variacao:+.2f}% — atenção moderada"
    else:
        sinal = "⚪"
        resumo = f"{nome} estável ({variacao:+.2f}%)"

    return {
        "nome": nome,
        "variacao": variacao,
        "sinal": sinal,
        "resumo": resumo,
    }
