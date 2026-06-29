"""Regras de alerta — combinam indicadores e decidem o que disparar."""
from datetime import date
from analise.indicadores import (
    calcular_relacao_boi_milho,
    calcular_sazonalidade_milho,
    calcular_sazonalidade_boi,
    analisar_variacao,
)
from config import (
    LIMITE_RELACAO_BOI_MILHO_ALTA,
    LIMITE_RELACAO_BOI_MILHO_BAIXA,
    LIMITE_CBOT_VARIACAO_ALERTA,
    LIMITE_DOLAR_VARIACAO_ALERTA,
)
from dados import banco


def avaliar_todas(dados_precos: dict, dados_cepea: dict, dados_clima: list) -> list[dict]:
    """Avalia todas as regras e retorna lista de alertas."""
    alertas = []
    ontem = None
    hoje = None
    mes_atual = date.today().month

    # Busca dia anterior pra comparar
    registros = banco.pegar_ultimos_precos(2)
    if len(registros) >= 2:
        hoje, ontem = registros[0], registros[1]
    elif len(registros) == 1:
        hoje = registros[0]

    # ─── 1. Relação Boi/Milho ──────────────────────────────
    boi = dados_cepea.get("arroba_cepea") or dados_precos.get("boi_b3")
    milho = dados_cepea.get("milho_cepea") or dados_precos.get("milho_b3")

    if boi and milho:
        rel = calcular_relacao_boi_milho(boi, milho)
        if rel["valor"]:
            alertas.append({
                "tipo": "relacao_boi_milho",
                "titulo": "Relação Boi/Milho",
                "valor": rel["valor"],
                "sinal": rel["sinal"],
                "confianca": "alta" if rel["valor"] >= LIMITE_RELACAO_BOI_MILHO_ALTA or
                             rel["valor"] <= LIMITE_RELACAO_BOI_MILHO_BAIXA else "media",
                "explicacao": rel["resumo"],
                "prazo": "médio (4-10 dias)",
                "ativo": "ambos",
                "direcao": "neutro",
            })

    # ─── 2. Variação CBOT ──────────────────────────────────
    cbot_atual = dados_precos.get("cbot")
    cbot_anterior = _pegar_coluna(ontem, "cbot") if ontem else None
    if cbot_atual and cbot_anterior:
        var = analisar_variacao(cbot_atual, cbot_anterior,
                                "CBOT", LIMITE_CBOT_VARIACAO_ALERTA)
        if var and abs(var["variacao"]) >= LIMITE_CBOT_VARIACAO_ALERTA:
            direcao = "milho_tende_cair" if var["variacao"] < 0 else "milho_tende_subir"
            alertas.append({
                "tipo": "cbot",
                "titulo": "Variação CBOT",
                "valor": var["variacao"],
                "sinal": var["sinal"],
                "confianca": "alta",
                "explicacao": var["resumo"],
                "prazo": "curto (1-3 dias)",
                "ativo": "milho",
                "direcao": direcao,
            })

    # ─── 3. Variação Dólar ─────────────────────────────────
    dolar_atual = dados_precos.get("dolar")
    dolar_anterior = _pegar_coluna(ontem, "dolar") if ontem else None
    if dolar_atual and dolar_anterior:
        var = analisar_variacao(dolar_atual, dolar_anterior,
                                "Dólar", LIMITE_DOLAR_VARIACAO_ALERTA)
        if var and abs(var["variacao"]) >= LIMITE_DOLAR_VARIACAO_ALERTA:
            direcao = "pressao_alta" if var["variacao"] > 0 else "pressao_baixa"
            alertas.append({
                "tipo": "dolar",
                "titulo": "Variação Dólar",
                "valor": var["variacao"],
                "sinal": var["sinal"],
                "confianca": "alta",
                "explicacao": var["resumo"],
                "prazo": "curto (1-3 dias)",
                "ativo": "ambos",
                "direcao": direcao,
            })

    # ─── 4. Sazonalidade Milho ─────────────────────────────
    saz_milho = calcular_sazonalidade_milho(mes_atual)
    if "⬇️" in saz_milho["sinal"] or "⬆️" in saz_milho["sinal"]:
        alertas.append({
            "tipo": "sazonalidade_milho",
            "titulo": f"Sazonalidade Milho ({saz_milho['mes']})",
            "valor": saz_milho["fase"],
            "sinal": saz_milho["sinal"],
            "confianca": "media",
            "explicacao": saz_milho["resumo"],
            "prazo": "longo (semanas)",
            "ativo": "milho",
            "direcao": "tendencia_baixa" if "⬇️" in saz_milho["sinal"] else "tendencia_alta",
        })

    # ─── 5. Sazonalidade Boi ───────────────────────────────
    saz_boi = calcular_sazonalidade_boi(mes_atual)
    if "⬆️" in saz_boi["sinal"] or "⬇️" in saz_boi["sinal"]:
        alertas.append({
            "tipo": "sazonalidade_boi",
            "titulo": f"Sazonalidade Boi ({saz_boi['mes']})",
            "valor": saz_boi["fase"],
            "sinal": saz_boi["sinal"],
            "confianca": "media",
            "explicacao": saz_boi["resumo"],
            "prazo": "longo (semanas)",
            "ativo": "boi",
            "direcao": "tendencia_alta" if "⬆️" in saz_boi["sinal"] else "tendencia_baixa",
        })

    # ─── 6. Combinações (sinais fortes) ────────────────────
    # CBOT caiu + Sazonalidade de baixa = confiança muito alta
    caindo = [a for a in alertas if a.get("tipo") == "cbot" and a.get("direcao") == "milho_tende_cair"]
    subindo = [a for a in alertas if a.get("tipo") == "cbot" and a.get("direcao") == "milho_tende_subir"]
    saz_baixa = [a for a in alertas if a.get("tipo") == "sazonalidade_milho" and "⬇️" in str(a.get("sinal", ""))]
    saz_alta = [a for a in alertas if a.get("tipo") == "sazonalidade_milho" and "⬆️" in str(a.get("sinal", ""))]

    if caindo and saz_baixa:
        alertas.append({
            "tipo": "combinado",
            "titulo": "⚠️ SINAL FORTE: Milho Pressionado",
            "valor": "CBOT caindo + Safrinha",
            "sinal": "🔴🔴",
            "confianca": "alta",
            "explicacao": "CBOT caiu + estamos em período de safra (colheita). Dois fatores negativos simultâneos. Alta probabilidade de queda no milho B3.",
            "prazo": "curto (1-3 dias)",
            "ativo": "milho",
            "direcao": "venda",
        })

    if subindo and saz_alta:
        alertas.append({
            "tipo": "combinado",
            "titulo": "⚠️ SINAL FORTE: Milho em Alta",
            "valor": "CBOT subindo + Entressafra",
            "sinal": "🟢🟢",
            "confianca": "alta",
            "explicacao": "CBOT subiu + entressafra (menor oferta). Dois fatores positivos. Alta probabilidade de alta no milho B3.",
            "prazo": "médio (4-10 dias)",
            "ativo": "milho",
            "direcao": "compra",
        })

    return alertas


def _pegar_coluna(registro, coluna: str):
    """Pega valor de uma coluna do banco, lida com tupla nomeada."""
    if not registro:
        return None
    colunas = [
        "id", "data", "milho_b3", "boi_b3", "cbot", "dolar",
        "milho_cepea", "arroba_cepea", "relacao_boi_milho",
        "created_at"
    ]
    if coluna in colunas:
        idx = colunas.index(coluna)
        if idx < len(registro):
            return registro[idx]
    return None
