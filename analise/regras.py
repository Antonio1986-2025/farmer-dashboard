"""Motor de regras com scoring multi-indicador.

Cada sinal recebe uma pontuação (0-100) baseada em múltiplos fatores:
tendência, RSI, volatilidade, sazonalidade e relações entre ativos.
"""
from analise.indicadores import (
    analisar_mercado_completo,
    analisar_tendencia,
    calcular_rsi,
    calcular_volatilidade,
    calcular_suporte_resistencia,
    calcular_relacao_boi_milho,
    calcular_sazonalidade_milho,
    calcular_sazonalidade_boi,
    calcular_indicador_historico,
)
from dados import banco
from dados.historico import pegar_estatisticas_historicas
from datetime import date


def _score(confianca: str) -> int:
    """Converte string de confiança para pontuação numérica."""
    return {"alta": 3, "media": 2, "baixa": 1}.get(confianca, 0)


def _confianca_str(pontos: int) -> str:
    """Converte pontuação numérica para string de confiança."""
    if pontos >= 3:
        return "alta"
    if pontos >= 2:
        return "media"
    return "baixa"


def _sinal_para_direcao(valor: float, limite_alta: float, limite_baixa: float) -> str:
    if valor >= limite_alta:
        return "favoravel"
    if valor <= limite_baixa:
        return "desfavoravel"
    return "neutro"


def avaliar_todas(dados_precos: dict, dados_cepea: dict, dados_clima: list) -> list[dict]:
    """Avalia todas as regras com scoring multi-indicador."""
    alertas = []
    hoje = date.today()

    # Análise completa com indicadores técnicos
    analise = analisar_mercado_completo()

    # Dados históricos para comparação (10 anos)
    historico = pegar_estatisticas_historicas()

    # ─── 1. MILHO — Análise técnica ─────────────────────────
    m = analise.get("milho", {})
    if m:
        pontos = 0
        fatores = []

        # Tendência
        tend = m.get("tendencia", {})
        if tend.get("direcao") == "baixa":
            pontos += 1
            fatores.append("tendencia_baixa")
        elif tend.get("direcao") == "alta":
            pontos += 1
            fatores.append("tendencia_alta")

        # RSI
        rsi = m.get("rsi")
        if rsi is not None:
            if rsi <= 35:
                pontos += 2
                fatores.append(f"rsi_sobrevendido_{rsi}")
            elif rsi >= 70:
                pontos += 2
                fatores.append(f"rsi_sobrecomprado_{rsi}")
            elif rsi <= 45:
                pontos += 1
                fatores.append(f"rsi_baixo_{rsi}")

        # Volatilidade
        vol = m.get("volatilidade")
        if vol is not None and vol > 2:
            pontos += 1
            fatores.append(f"volatilidade_{vol}")

        # Suporte/Resistência
        sr = m.get("sr", {})
        ds = sr.get("distancia_suporte", 0)
        dr = sr.get("distancia_resistencia", 0)
        if ds is not None and ds < 3:
            pontos += 1
            fatores.append(f"proximo_suporte_{ds}%")
        if dr is not None and dr < 3:
            pontos += 1
            fatores.append(f"proximo_resistencia_{dr}%")

        # Sazonalidade
        saz = analise.get("sazonalidade", {}).get("milho", {})
        if saz.get("direcao") == "baixa":
            pontos += 1
            fatores.append("safra")
        elif saz.get("direcao") == "alta":
            pontos += 1
            fatores.append("entressafra")

        # Indicador histórico (10 anos)
        hist_cbot = historico.get("cbot", {})
        if hist_cbot:
            ih = calcular_indicador_historico(m.get("atual"), hist_cbot)
            if ih["score"] > 0 and pontos <= 4:
                pontos += 1
                fatores.append(f"historico_compra_{ih['variacao_media']}%")
            elif ih["score"] < 0 and pontos <= 4:
                pontos += 1
                fatores.append(f"historico_venda_{ih['variacao_media']}%")

        if pontos >= 2:
            forca = "alta" if pontos >= 4 else "media"
            direcao = "venda" if tend.get("direcao") == "baixa" else "compra"
            if "proximo_resistencia" in str(fatores) or "rsi_sobrecomprado" in str(fatores):
                direcao = "venda"
            elif "proximo_suporte" in str(fatores) or "rsi_sobrevendido" in str(fatores):
                direcao = "compra"

            alertas.append({
                "tipo": "analise_milho",
                "titulo": "Análise Técnica Milho",
                "valor": m.get("atual"),
                "sinal": "🔴" if "venda" in direcao else "🟢",
                "confianca": forca,
                "explicacao": (
                    f"Milho R$ {m['atual']} | RSI {rsi} | "
                    f"Tendência {tend.get('direcao')} | "
                    f"Suporte R$ {sr.get('suporte')} | "
                    f"Resistência R$ {sr.get('resistencia')} | "
                    f"Vol {vol}% | Fatores: {len(fatores)}/{pontos}"
                ),
                "prazo": "médio (4-10 dias)",
                "ativo": "milho",
                "direcao": direcao,
                "score": pontos,
            })

    # ─── 2. BOI — Análise técnica ──────────────────────────
    b = analise.get("boi", {})
    if b:
        pontos = 0
        tend = b.get("tendencia", {})
        rsi = b.get("rsi")
        sr = b.get("sr", {})
        saz = analise.get("sazonalidade", {}).get("boi", {})

        if tend.get("direcao") == "alta":
            pontos += 1
        if rsi is not None and rsi <= 35:
            pontos += 2
        elif rsi is not None and rsi >= 70:
            pontos += 2
        if sr.get("distancia_suporte", 99) < 3:
            pontos += 1
        if sr.get("distancia_resistencia", 99) < 3:
            pontos += 1
        if saz.get("direcao") == "alta":
            pontos += 1

        if pontos >= 2:
            alertas.append({
                "tipo": "analise_boi",
                "titulo": "Análise Técnica Boi Gordo",
                "valor": b.get("atual"),
                "sinal": "🟢" if tend.get("direcao") == "alta" else "🔴",
                "confianca": "alta" if pontos >= 4 else "media",
                "explicacao": (
                    f"Boi R$ {b['atual']}/@ | RSI {rsi} | "
                    f"Tendência {tend.get('direcao')} | "
                    f"Suporte R$ {sr.get('suporte')} | "
                    f"Resistência R$ {sr.get('resistencia')} | "
                    f"Sazonalidade: {saz.get('fase', '')}"
                ),
                "prazo": "médio (4-10 dias)",
                "ativo": "boi",
                "direcao": "compra" if tend.get("direcao") == "alta" else "venda",
                "score": pontos,
            })

    # ─── 3. Relação Boi/Milho ──────────────────────────────
    rel = analise.get("relacao_boi_milho", {})
    if rel.get("valor"):
        conf = "alta" if rel["valor"] >= 5.5 or rel["valor"] <= 3.0 else "media"
        alertas.append({
            "tipo": "relacao_boi_milho",
            "titulo": "Relação Boi/Milho",
            "valor": rel["valor"],
            "sinal": rel["sinal"],
            "confianca": conf,
            "explicacao": rel["resumo"],
            "prazo": "médio (4-10 dias)",
            "ativo": "ambos",
            "direcao": "neutro",
            "score": _score(conf),
        })

    # ─── 4. CBOT ────────────────────────────────────────────
    c = analise.get("cbot", {})
    if c:
        tend = c.get("tendencia", {})
        rsi = c.get("rsi")
        if tend.get("direcao") == "baixa" or (rsi is not None and rsi >= 70):
            conf = "alta" if rsi and rsi >= 70 else "media"
            alertas.append({
                "tipo": "cbot",
                "titulo": "CBOT (Milho Chicago)",
                "valor": c.get("atual"),
                "sinal": "🔴",
                "confianca": conf,
                "explicacao": (
                    f"CBOT US$ {c['atual']} | RSI {rsi} | "
                    f"Tendência {tend.get('direcao')} | "
                    f"SMA5 {c.get('sma5')} SMA20 {c.get('sma20')}"
                ),
                "prazo": "curto (1-3 dias)",
                "ativo": "milho",
                "direcao": "milho_tende_cair" if tend.get("direcao") == "baixa" else "milho_tende_subir",
                "score": _score(conf),
            })
        elif tend.get("direcao") == "alta" or (rsi is not None and rsi <= 35):
            conf = "alta" if rsi and rsi <= 35 else "media"
            alertas.append({
                "tipo": "cbot",
                "titulo": "CBOT (Milho Chicago)",
                "valor": c.get("atual"),
                "sinal": "🟢",
                "confianca": conf,
                "explicacao": (
                    f"CBOT US$ {c['atual']} | RSI {rsi} | "
                    f"Tendência {tend.get('direcao')}"
                ),
                "prazo": "curto (1-3 dias)",
                "ativo": "milho",
                "direcao": "milho_tende_subir" if tend.get("direcao") == "alta" else "milho_tende_cair",
                "score": _score(conf),
            })

    # ─── 5. HISTÓRICO (10 anos) ────────────────────────────
    hist_cbot = historico.get("cbot", {})
    hist_dolar = historico.get("dolar", {})

    if hist_cbot:
        preco_cbot = dados_precos.get("cbot")
        if preco_cbot:
            ih_cbot = calcular_indicador_historico(preco_cbot, hist_cbot)
            if abs(ih_cbot["score"]) >= 2:
                alertas.append({
                    "tipo": "historico_cbot",
                    "titulo": "📜 CBOT vs Média Histórica (10 anos)",
                    "valor": preco_cbot,
                    "sinal": "🟢" if ih_cbot["score"] > 0 else "🔴",
                    "confianca": "alta",
                    "explicacao": ih_cbot["resumo"],
                    "prazo": "longo (30-90 dias)",
                    "ativo": "milho",
                    "direcao": "compra" if ih_cbot["score"] > 0 else "venda",
                    "score": abs(ih_cbot["score"]),
                })

    if hist_dolar:
        preco_dolar = dados_precos.get("dolar")
        if preco_dolar:
            ih_dolar = calcular_indicador_historico(preco_dolar, hist_dolar)
            if abs(ih_dolar["score"]) >= 2:
                alertas.append({
                    "tipo": "historico_dolar",
                    "titulo": "📜 Dólar vs Média Histórica (10 anos)",
                    "valor": preco_dolar,
                    "sinal": "🟢" if ih_dolar["score"] < 0 else "🔴",
                    "confianca": "alta",
                    "explicacao": ih_dolar["resumo"],
                    "prazo": "longo (30-90 dias)",
                    "ativo": "ambos",
                    "direcao": "compra" if ih_dolar["score"] < 0 else "venda",
                    "score": abs(ih_dolar["score"]),
                })

    # ─── 6. DÓLAR ──────────────────────────────────────────
    d = analise.get("dolar", {})
    if d:
        tend = d.get("tendencia", {})
        rsi = d.get("rsi")
        vol = d.get("volatilidade")
        if tend.get("direcao") in ("alta", "baixa") and (vol is None or vol > 1.5):
            conf = "alta" if vol and vol > 2.5 else "media"
            alertas.append({
                "tipo": "dolar",
                "titulo": "Dólar (USD/BRL)",
                "valor": d.get("atual"),
                "sinal": "🔴" if tend.get("direcao") == "alta" else "🟢",
                "confianca": conf,
                "explicacao": (
                    f"Dólar R$ {d['atual']} | RSI {rsi} | "
                    f"Tendência {tend.get('direcao')} | "
                    f"Vol {vol}% | SMA5 {d.get('sma5')} SMA20 {d.get('sma20')}"
                ),
                "prazo": "curto (1-3 dias)",
                "ativo": "ambos",
                "direcao": "pressao_alta" if tend.get("direcao") == "alta" else "pressao_baixa",
                "score": _score(conf),
            })

    # ─── 7. SINAIS COMBINADOS ──────────────────────────────
    # Milho: CBOT baixista + tendência baixa + sazonalidade baixa
    caindo = [a for a in alertas if a["tipo"] in ("cbot", "analise_milho")
              and "cair" in a.get("direcao", "") or a.get("direcao") == "venda"]
    subindo = [a for a in alertas if a["tipo"] in ("cbot", "analise_milho")
               and "subir" in a.get("direcao", "") or a.get("direcao") == "compra"]

    if len(caindo) >= 2:
        pontuacao = sum(a.get("score", 0) for a in caindo)
        alertas.append({
            "tipo": "combinado_milho",
            "titulo": "⚠️ SINAL FORTE: MILHO PRESSIONADO",
            "valor": f"{len(caindo)} fatores",
            "sinal": "🔴🔴",
            "confianca": "alta",
            "explicacao": (
                f"Múltiplos fatores negativos para o milho "
                f"(CBOT, tendência, sazonalidade). "
                f"Score: {pontuacao}/10 — recomendação: VENDA"
            ),
            "prazo": "curto (1-3 dias)",
            "ativo": "milho",
            "direcao": "venda",
            "score": min(pontuacao, 5),
        })

    if len(subindo) >= 2:
        pontuacao = sum(a.get("score", 0) for a in subindo)
        alertas.append({
            "tipo": "combinado_milho",
            "titulo": "⚠️ SINAL FORTE: MILHO EM ALTA",
            "valor": f"{len(subindo)} fatores",
            "sinal": "🟢🟢",
            "confianca": "alta",
            "explicacao": (
                f"Múltiplos fatores positivos para o milho "
                f"(CBOT, tendência, sazonalidade). "
                f"Score: {pontuacao}/10 — recomendação: COMPRA"
            ),
            "prazo": "médio (4-10 dias)",
            "ativo": "milho",
            "direcao": "compra",
            "score": min(pontuacao, 5),
        })

    return alertas
