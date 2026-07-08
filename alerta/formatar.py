"""Formatação de mensagens para WhatsApp / dashboard com lentes por perfil."""


# ─── Interpretação por perfil ─────────────────────────────────

def _interpretar_para_perfil(alerta: dict, ao_vivo: dict | None, perfil: str) -> str:
    """
    Gera um parágrafo extra no alerta, adaptado ao perfil do usuário.
    Funciona como 'lente' — mesma informação, ângulo diferente.
    """
    titulo = alerta.get("titulo", "").lower()
    ativo = alerta.get("ativo", "ambos")
    explicacao = alerta.get("explicacao", "")
    direcao = alerta.get("direcao", "alta")
    confianca = alerta.get("confianca", "media")

    # Dados de mercado se disponíveis
    mercado = {}
    if ao_vivo:
        for chave in ("cbot", "dolar"):
            if ao_vivo.get(chave, {}).get("disponivel"):
                mercado[chave] = ao_vivo[chave]

    if perfil == "produtor":
        return _interpretar_produtor(titulo, ativo, direcao, confianca, mercado, explicacao)
    elif perfil == "fisico":
        return _interpretar_fisico(titulo, ativo, direcao, confianca, mercado, explicacao)
    elif perfil == "swinger":
        return _interpretar_swinger(titulo, ativo, direcao, confianca, mercado, explicacao)
    elif perfil == "daytrade":
        return _interpretar_daytrade(titulo, ativo, direcao, confianca, mercado, explicacao)
    elif perfil == "hedger":
        return _interpretar_hedger(titulo, ativo, direcao, confianca, mercado, explicacao)
    return ""


def _preco_mercado(mercado: dict, ativo: str) -> str:
    """Pega o preço atual do mercado."""
    tk = "cbot" if ativo in ("milho", "cbot", "ambos") else "dolar"
    if tk in mercado:
        return str(mercado[tk].get("atual", "—"))
    return "—"


def _vol_forca(mercado: dict, ativo: str) -> tuple:
    """Retorna (volume_total, forca_compradora)."""
    tk = "cbot" if ativo in ("milho", "cbot", "ambos") else "dolar"
    if tk in mercado:
        m = mercado[tk]
        vol = m.get("volume_total", 0)
        sub = m.get("volume_subida", 0)
        forca = round(sub / vol * 100, 1) if vol else 50
        return vol, forca
    return 0, 50


# ─── Lentes individuais ───────────────────────────────────────

def _interpretar_produtor(titulo, ativo, direcao, confianca, mercado, explicacao):
    vol, forca = _vol_forca(mercado, ativo)
    preco = _preco_mercado(mercado, ativo)

    if confianca == "alta":
        if direcao in ("alta", "compra"):
            return (
                f"🧑‍🌾 **ÓTIMA NOTÍCIA PRODUTOR:**\n"
                f"   Preço subindo com força. Se tem produção pra vender, "
                f"esse movimento pode ser a janela que você esperava.\n"
                f"   📍 Acompanhe os próximos dias — se o volume continuar forte, "
                f"é sinal de tendência sustentável."
            )
        else:
            return (
                f"🧑‍🌾 **ATENÇÃO PRODUTOR:**\n"
                f"   Preço caindo. Se não precisa vender agora, aguarde — "
                f"movimentos assim costumam ser pontuais.\n"
                f"   📍 Clima e safra continuam sendo seus melhores indicadores."
            )
    return (
        f"🧑‍🌾 **PARA O PRODUTOR:**\n"
        f"   Mercado em movimento. Fique de olho nos próximos dias "
        f"para decidir a melhor janela de venda da sua produção."
    )


def _interpretar_fisico(titulo, ativo, direcao, confianca, mercado, explicacao):
    vol, forca = _vol_forca(mercado, ativo)
    preco = _preco_mercado(mercado, ativo)

    if vol > 100_000 and forca > 60:
        return (
            f"📦 **LEITURA FÍSICO:**\n"
            f"   Mercado comprador forte! Volume de {vol:,} contratos com "
            f"{forca}% das negociações em subida.\n"
            f"   🎯 Se tem boi/milho pra vender no físico, esse é um bom "
            f"momento de buscar negociação."
        )
    elif forca < 40:
        return (
            f"📦 **LEITURA FÍSICO:**\n"
            f"   Pressão vendedora predominante ({100-forca}% das negociações).\n"
            f"   🎯 Se vai comprar físico, pode encontrar bons preços. "
            f"Se vai vender, talvez valha aguardar."
        )
    return (
        f"📦 **LEITURA FÍSICO:**\n"
        f"   Mercado com liquidez normal. Preço referência em R$ {preco} "
        f"no físico. Acompanhe a tendência dos próximos dias."
    )


def _interpretar_swinger(titulo, ativo, direcao, confianca, mercado, explicacao):
    vol, forca = _vol_forca(mercado, ativo)
    preco = _preco_mercado(mercado, ativo)

    if confianca == "alta" and forca > 55:
        return (
            f"📈 **SETUP SWINGER B3:**\n"
            f"   Tendência confirmada por volume ({forca}% comprador). "
            f"Movimento tem sustentação para os próximos dias.\n"
            f"   📍 Estratégia: buscar entrada na correção. "
            f"Stop abaixo da mínida mais recente.\n"
            f"   ⏳ Suporte para posição de {vol:,} contratos no dia."
        )
    elif forca > 50:
        return (
            f"📈 **SETUP SWINGER B3:**\n"
            f"   Leve favoritismo comprador ({forca}%). Movimento ainda "
            f"sem confirmação total.\n"
            f"   📍 Aguardar rompimento da máxima com volume para entrar. "
            f"Não antecipar."
        )
    return (
        f"📈 **SETUP SWINGER B3:**\n"
        f"   Volume ({vol:,}) mostra mercado ativo. "
        f"força compradora em {forca}%.\n"
        f"   📍 Acompanhar para confirmar tendência. "
        f"Não forçar entrada sem volume favorável."
    )


def _interpretar_daytrade(titulo, ativo, direcao, confianca, mercado, explicacao):
    vol, forca = _vol_forca(mercado, ativo)
    preco = _preco_mercado(mercado, ativo)

    if vol > 150_000:
        return (
            f"⚡ **FLASH DAY TRADE:**\n"
            f"   Alta liquidez! {vol:,} contratos negociados. "
            f"Ponto de entrada com volume.\n"
            f"   📍 Resistência: máxima do dia. "
            f"Suporte: mínima do dia.\n"
            f"   🎯 Realizar parcial rápido — tendência diária favorável "
            f"mas realização pode vir."
        )
    elif vol > 80_000:
        return (
            f"⚡ **FLASH DAY TRADE:**\n"
            f"   Liquidez moderada ({vol:,} contratos). "
            f"Movimento com {forca}% de força compradora.\n"
            f"   📍 Operar com stop curto. "
            f"Não adicionar em posição perdedora."
        )
    return (
        f"⚡ **FLASH DAY TRADE:**\n"
        f"   Volume baixo hoje ({vol:,} contratos). "
        f"Evitar forçar entrada — sem confirmação.\n"
        f"   📍 Aguardar aumento de liquidez para operar."
    )


def _interpretar_hedger(titulo, ativo, direcao, confianca, mercado, explicacao):
    vol, forca = _vol_forca(mercado, ativo)
    preco = _preco_mercado(mercado, ativo)

    if confianca == "alta" and direcao in ("alta", "compra"):
        return (
            f"🛡️ **HEDGE INTELLIGENCE:**\n"
            f"   Mercado em alta com fundamento. Se você tem exposição "
            f"comprada (produção), está protegido.\n"
            f"   📍 Se precisa comprar (indústria), avaliar hedge parcial "
            f"agora — pode subir mais."
        )
    elif confianca == "alta" and direcao in ("baixa", "venda"):
        return (
            f"🛡️ **HEDGE INTELLIGENCE:**\n"
            f"   Pressão baixista. Se tem exposição vendida (compromisso "
            f"de compra futura), avaliar hedge.\n"
            f"   📍 Acompanhar relação boi/milho e dólar para decisão."
        )
    return (
        f"🛡️ **HEDGE INTELLIGENCE:**\n"
        f"   Mercado dentro da normalidade. Acompanhar para identificar "
        f"janelas de hedge com bom custo-benefício."
    )


# ─── Formatação principal ────────────────────────────────────

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


def formatar_alerta_whatsapp(alerta: dict, ao_vivo: dict | None = None,
                             perfil: str | None = None) -> str:
    """
    Monta a mensagem formatada pro WhatsApp.
    Se `perfil` for informado, inclui a lente interpretativa.
    """
    emoji_ativos = {"milho": "🌽", "boi": "🐄", "ambos": "📊",
                    "cbot": "🌽", "dolar": "💵"}

    if alerta.get("confianca") == "alta":
        header = "🔴🔴 ALERTA PRIORITÁRIO"
    elif alerta.get("confianca") == "media":
        header = "🟡 ATENÇÃO"
    else:
        header = "ℹ️ INFORMATIVO"

    ativo = alerta.get("ativo", "ambos")
    emoji = emoji_ativos.get(ativo, "📊")

    # Dados AO VIVO
    if ao_vivo:
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

    # Lente do perfil
    lente = ""
    if perfil:
        texto_lente = _interpretar_para_perfil(alerta, ao_vivo, perfil)
        if texto_lente:
            lente = f"\n\n{texto_lente}"

    msg = f"""{header}

{emoji} {alerta['titulo']}

📌 Sinal: {alerta.get('valor', '')}
📊 Confiança: {alerta['confianca'].upper()}
⏱️ Prazo: {alerta.get('prazo', 'não definido')}
{mercado_linha}
🔎 Por que:
{alerta.get('explicacao', '')}{lente}"""
    return msg.strip()


def formatar_resumo_diario(precos: dict, clima: list,
                           alertas: list, trades_abertos: list,
                           ao_vivo: dict | None = None,
                           perfil: str | None = None) -> str:
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

    # Lente do perfil no resumo
    lente = ""
    if perfil:
        # Cria um alerta genérico contextual pra gerar a lente
        alerta_ctx = {
            "titulo": "Resumo do dia",
            "ativo": "ambos",
            "confianca": "media",
            "direcao": "",
            "explicacao": "Acompanhamento diário do mercado.",
        }
        texto_lente = _interpretar_para_perfil(alerta_ctx, ao_vivo, perfil)
        if texto_lente:
            lente = f"\n\n{texto_lente}"

    msg = f"""🌅 RESUMO DO DIA — {__import__('datetime').date.today()}

💵 Dólar: {dolar}
🌽 CBOT: {cbot}
{linha_clima}
{linha_alerta}
{linha_ao_vivo}{lente}"""
    return msg.strip()
