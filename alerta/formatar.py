"""Formatação de mensagens para WhatsApp / dashboard."""


def _resumir_ao_vivo(ao_vivo: dict | None = None) -> str:
    """Monta linha com OHLC + Volume do pregão para incluir nos alertas."""
    if not ao_vivo:
        return ""
    partes = []
    for ticker, info in [("cbot", "🌽 CBOT"), ("dolar", "💵 Dólar")]:
        ativo = ao_vivo.get(ticker, {})
        if not ativo.get("disponivel"):
            continue
        vol = ativo.get("volume_total", 0)
        linha = f"   {info}: "
        linha += f"Abertura {ativo.get('abertura','—')} | "
        linha += f"Máx {ativo.get('maxima','—')} | "
        linha += f"Mín {ativo.get('minima','—')} | "
        linha += f"Atual {ativo.get('atual','—')} "
        linha += f"{ativo.get('sinal_variacao','')}{ativo.get('variacao','')}%"
        if vol:
            linha += f"\n   📊 Volume: {vol:,} contratos"
            sub = ativo.get("volume_subida", 0)
            desc = ativo.get("volume_descida", 0)
            pct_sub = round(sub / vol * 100, 1) if vol else 50
            linha += f" (▲ {pct_sub}% subida)"
        partes.append(linha)
    return "\n".join(partes) if partes else ""


def formatar_alerta_whatsapp(alerta: dict, ao_vivo: dict | None = None) -> str:
    """Monta a mensagem formatada pro WhatsApp."""
    emoji_ativos = {"milho": "🌽", "boi": "🐄", "ambos": "📊", "cbot": "🌽", "dolar": "💵"}

    if alerta.get("confianca") == "alta":
        header = "🔴🔴 ALERTA PRIORITÁRIO"
    elif alerta.get("confianca") == "media":
        header = "🟡 ATENÇÃO"
    else:
        header = "ℹ️ INFORMATIVO"

    ativo = alerta.get("ativo", "ambos")
    emoji = emoji_ativos.get(ativo, "📊")

    # Se tem AO VIVO, prioriza dados de mercado
    if ao_vivo:
        # Pega o ativo relevante
        ticker_map = {"milho": "cbot", "boi": "cbot", "cbot": "cbot", "dolar": "dolar"}
        tk = ticker_map.get(ativo, None)
        mercado = None
        if tk and ao_vivo.get(tk, {}).get("disponivel"):
            mercado = ao_vivo[tk]
        elif tk == "cbot":
            mercado = ao_vivo.get("cbot", {})
        mercado_linha = ""
        if mercado and mercado.get("disponivel"):
            mercado_linha = f"\n💱 OHLC: Aber {mercado.get('abertura','—')} · "
            mercado_linha += f"Máx {mercado.get('maxima','—')} · "
            mercado_linha += f"Mín {mercado.get('minima','—')} · "
            mercado_linha += f"Atual {mercado.get('atual','—')}"
            vol = mercado.get("volume_total", 0)
            if vol:
                mercado_linha += f"\n📊 Volume: {vol:,} contratos"
                sub = mercado.get("volume_subida", 0)
                sub_pct = round(sub / vol * 100, 1) if vol else 50
                mercado_linha += f" (▲ {sub_pct}% em subida)"
    else:
        mercado_linha = ""

    msg = f"""{header}

{emoji} {alerta['titulo']}

📌 Sinal: {alerta.get('valor', '')}
📊 Confiança: {alerta['confianca'].upper()}
⏱️ Prazo: {alerta.get('prazo', 'não definido')}
{mercado_linha}
🔎 Por que:
{alerta.get('explicacao', '')}
"""
    return msg.strip()


def formatar_resumo_diario(precos: dict, clima: list,
                           alertas: list, trades_abertos: list,
                           ao_vivo: dict | None = None) -> str:
    """Monta um resumo do dia pra enviar no WhatsApp."""
    dolar = precos.get("dolar", "—")
    cbot = precos.get("cbot", "—")

    linha_clima = ""
    for c in clima[:2]:
        linha_clima += f"\n   • {c['regiao']}: {c['temperatura']}°C, {c['chuva_mm']}mm"

    linha_ao_vivo = ""
    if ao_vivo:
        linha_ao_vivo = f"\n\n🔴 AO VIVO:\n{_resumir_ao_vivo(ao_vivo)}"

    if alertas_prioritarios := [a for a in alertas if a.get("confianca") == "alta"]:
        linha_alerta = f"\n⚠️ {len(alertas_prioritarios)} alerta(s) prioritário(s)"
        for a in alertas_prioritarios[:2]:
            linha_alerta += f"\n   • {a['titulo']}: {a['explicacao'][:80]}..."
    else:
        linha_alerta = "\n✅ Nenhum alerta prioritário hoje"

    msg = f"""🌅 RESUMO DO DIA — {__import__('datetime').date.today()}

💵 Dólar: {dolar}
🌽 CBOT: {cbot}
{linha_clima}
{linha_alerta}
{linha_ao_vivo}"""
    return msg.strip()
