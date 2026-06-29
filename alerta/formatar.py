"""Formatação de mensagens para WhatsApp / dashboard."""


def formatar_alerta_whatsapp(alerta: dict) -> str:
    """Monta a mensagem formatada pro WhatsApp."""
    emoji_ativos = {"milho": "🌽", "boi": "🐄", "ambos": "📊"}

    if alerta.get("confianca") == "alta":
        header = "🔴🔴 ALERTA PRIORITÁRIO"
    elif alerta.get("confianca") == "media":
        header = "🟡 ATENÇÃO"
    else:
        header = "ℹ️ INFORMATIVO"

    ativo = alerta.get("ativo", "ambos")
    emoji = emoji_ativos.get(ativo, "📊")

    msg = f"""{header}

{emoji} {alerta['titulo']}

📌 Sinal: {alerta.get('valor', '')}
📊 Confiança: {alerta['confianca'].upper()}
⏱️ Prazo: {alerta.get('prazo', 'não definido')}

🔎 Por que:
{alerta.get('explicacao', '')}
"""
    return msg.strip()


def formatar_resumo_diario(precos: dict, clima: list,
                           alertas: list, trades_abertos: list) -> str:
    """Monta um resumo do dia pra enviar no WhatsApp."""
    dolar = precos.get("dolar", "—")
    cbot = precos.get("cbot", "—")

    linha_clima = ""
    for c in clima[:2]:
        linha_clima += f"\n   • {c['regiao']}: {c['temperatura']}°C, {c['chuva_mm']}mm"

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
"""
    return msg.strip()
