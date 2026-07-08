"""Gera o dashboard HTML com gráficos usando Plotly."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
from dados import banco
from dados.historico import pegar_estatisticas_historicas
from analise import acertos


def gerar_grafico_precos(registros: list) -> str:
    """Gera HTML com gráfico de evolução dos preços."""
    if not registros:
        return "<div style='padding:20px;color:#888;'>⏳ Nenhum dado histórico ainda. Volte amanhã!</div>"

    # Inverte pra ordem cronológica
    registros = list(reversed(registros))
    colunas = ["data", "milho_b3", "boi_b3", "cbot", "dolar", "milho_cepea", "arroba_cepea", "relacao_boi_milho"]
    datas = []
    milho_vals = []
    boi_vals = []
    cbot_vals = []
    dolar_vals = []
    relacao_vals = []

    for r in registros:
        if len(r) < 9:
            continue
        datas.append(r[1])
        if r[2]: milho_vals.append((r[1], r[2]))
        if r[3]: boi_vals.append((r[1], r[3]))
        if r[4]: cbot_vals.append((r[1], r[4]))
        if r[5]: dolar_vals.append((r[1], r[5]))
        if r[8]: relacao_vals.append((r[1], r[8]))

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("🌽 Milho B3 (R$/saca)", "🐄 Boi Gordo (R$/@)",
                        "💵 Dólar (USD/BRL)", "📊 Relação Boi/Milho"),
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )

    if milho_vals:
        fig.add_trace(go.Scatter(
            x=[v[0] for v in milho_vals], y=[v[1] for v in milho_vals],
            mode="lines+markers", name="Milho B3",
            line=dict(color="#f39c12", width=2),
            marker=dict(size=6),
        ), row=1, col=1)
        fig.update_yaxes(title_text="R$/saca", row=1, col=1)

    if boi_vals:
        fig.add_trace(go.Scatter(
            x=[v[0] for v in boi_vals], y=[v[1] for v in boi_vals],
            mode="lines+markers", name="Boi Gordo",
            line=dict(color="#e74c3c", width=2),
            marker=dict(size=6),
        ), row=1, col=2)
        fig.update_yaxes(title_text="R$/@", row=1, col=2)

    if dolar_vals:
        fig.add_trace(go.Scatter(
            x=[v[0] for v in dolar_vals], y=[v[1] for v in dolar_vals],
            mode="lines+markers", name="Dólar",
            line=dict(color="#2ecc71", width=2),
            marker=dict(size=6),
        ), row=2, col=1)

    if relacao_vals:
        fig.add_trace(go.Scatter(
            x=[v[0] for v in relacao_vals], y=[v[1] for v in relacao_vals],
            mode="lines+markers", name="Relação",
            line=dict(color="#9b59b6", width=2),
            marker=dict(size=6),
        ), row=2, col=2)
        fig.add_hline(y=4.0, line_dash="dash", line_color="gray",
                      annotation_text="Média hist. 4,0", row=2, col=2)

    fig.update_layout(
        height=600,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    fig.update_xaxes(tickangle=45)
    for i in range(1, 3):
        for j in range(1, 3):
            fig.update_yaxes(gridcolor="#eee", row=i, col=j)

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def gerar_tabela_alertas(alertas: list) -> str:
    """Gera HTML da tabela de alertas do dia."""
    if not alertas:
        return "<div style='padding:15px;color:#888;'>✅ Nenhum alerta gerado hoje</div>"

    linhas = []
    for a in alertas:
        conf = a.get("confianca", "media")
        cor_conf = {"alta": "#e74c3c", "media": "#f39c12", "baixa": "#3498db"}.get(conf, "#888")

        emoji_dir = {"compra": "🟢", "venda": "🔴"}.get(a.get("direcao", ""), "📊")

        linhas.append(f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;font-size:18px;">{a.get('sinal', '📊')}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">
                <strong>{a.get('titulo', '')}</strong><br>
                <span style="color:#666;font-size:13px;">{a.get('explicacao', '')[:100]}</span>
            </td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;">
                <span style="background:{cor_conf};color:white;padding:3px 10px;border-radius:12px;font-size:12px;">
                    {conf.upper()}
                </span>
            </td>
            <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;">
                {emoji_dir} {a.get('prazo', '—')}
            </td>
        </tr>""")

    return f"""
    <div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>Sinal</th>
                <th>Alerta</th>
                <th>Confiança</th>
                <th>Prazo</th>
            </tr>
        </thead>
        <tbody>{''.join(linhas)}</tbody>
    </table>
    </div>"""


def gerar_resumo_clima(dados_clima: list) -> str:
    """Gera HTML com cards de clima."""
    if not dados_clima:
        return "<div style='padding:15px;color:#888;'>🌤️ Configure a OPENWEATHER_API_KEY no config.py</div>"

    cards = []
    for c in dados_clima:
        if isinstance(c, tuple):
            _, _, regiao, temp, chuva, umid = c
        else:
            regiao = c.get("regiao", "—")
            temp = c.get("temperatura", "—")
            chuva = c.get("chuva_mm", "—")
            umid = c.get("umidade", "—")

        emoji_temp = "☀️" if (isinstance(temp, (int, float)) and temp > 30) else "⛅" if (isinstance(temp, (int, float)) and temp > 20) else "🌧️"
        cards.append(f"""
        <div class="clima-card">
            <div class="regiao">{regiao}</div>
            <div class="temp">{emoji_temp} {temp}°C</div>
            <div class="detalhes">💧 {chuva}mm | 🌫️ {umid}%</div>
        </div>""")

    return f'<div class="clima-grid">{"".join(cards)}</div>'


def gerar_resumo_trades(usuario_id: int | None = None) -> str:
    """Gera HTML com resumo dos trades."""
    resumo = banco.pegar_resumo_trades(usuario_id)
    if not resumo or resumo[0] is None or resumo[0] == 0:
        return """
        <div style="padding:15px;color:#888;">
            📋 Nenhum trade registrado ainda.<br>
            <span style="font-size:13px;">Use: python main.py --entrar COMPRA MILHO 65.00</span>
        </div>"""

    total, vitorias, derrotas, lucro, prejuizo, dias_medio = resumo
    taxa = round(vitorias / total * 100, 1) if total > 0 else 0
    saldo = round((lucro or 0) + (prejuizo or 0), 2)
    emoji = "🟢" if saldo > 0 else "🔴" if saldo < 0 else "⚪"

    return f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
        <div style="background:#f8f9fa;border-radius:10px;padding:15px;text-align:center;">
            <div style="font-size:12px;color:#888;">Taxa de Acerto</div>
            <div style="font-size:28px;font-weight:bold;">{taxa}%</div>
            <div style="font-size:12px;color:#888;">{int(vitorias or 0)}V / {int(derrotas or 0)}D</div>
        </div>
        <div style="background:#f8f9fa;border-radius:10px;padding:15px;text-align:center;">
            <div style="font-size:12px;color:#888;">Saldo Acumulado</div>
            <div style="font-size:28px;font-weight:bold;">{emoji} R$ {saldo:.2f}</div>
        </div>
        <div style="background:#f8f9fa;border-radius:10px;padding:15px;text-align:center;">
            <div style="font-size:12px;color:#888;">Tempo Médio</div>
            <div style="font-size:28px;font-weight:bold;">{round(dias_medio or 0)} dias</div>
            <div style="font-size:12px;color:#888;">{int(total)} trades no total</div>
        </div>
    </div>"""


def gerar_tabela_estatisticas_sinais() -> str:
    """Gera HTML com taxa de acerto por tipo de sinal."""
    stats = banco.pegar_estatisticas_sinais()
    if not stats:
        return "<div style='padding:15px;color:#888;'>📊 Estatísticas aparecerão conforme você registrar trades</div>"

    linhas = []
    for s in stats:
        tipo, direcao, total, acertos, erros, pendentes = s
        taxa = round(acertos / total * 100, 1) if total > 0 else 0
        emoji = "🔥" if taxa >= 75 else "📊" if taxa >= 50 else "⚠️"
        linhas.append(f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;">{tipo.replace('_', ' ').title()}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{direcao.replace('_', ' ')}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{emoji} {taxa}%</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{int(acertos)}/{int(total)}</td>
        </tr>""")

    return f"""
    <div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>Padrão</th>
                <th>Direção</th>
                <th>Taxa de Acerto</th>
                <th>Acertos/Total</th>
            </tr>
        </thead>
        <tbody>{''.join(linhas)}</tbody>
    </table>
    </div>"""


def gerar_tabela_datagro(dados_datagro: dict) -> str:
    """Gera tabela com preços DATAGRO por estado."""
    if not dados_datagro:
        return "<div style='padding:15px;color:#888;'>📡 Dados DATAGRO indisponíveis no momento</div>"

    # Filtra só os estados (remove metadados)
    estados = {k: v for k, v in dados_datagro.items()
               if k not in ("_data", "_media_nacional") and isinstance(v, dict) and v.get("preco")}

    if not estados:
        return "<div style='padding:15px;color:#888;'>📡 Dados DATAGRO indisponíveis no momento</div>"

    data_ref = dados_datagro.get("_data", "—")
    media = dados_datagro.get("_media_nacional")

    # Ordena estados: maiores preços primeiro
    sorted_estados = sorted(estados.items(), key=lambda x: x[1]["preco"], reverse=True)

    linhas = []
    for estado, dados in sorted_estados:
        preco = dados["preco"]
        var = dados.get("variacao", 0)
        sinal = "🔺" if var > 0 else ("🔻" if var < 0 else "➡️")
        cor_var = "#e74c3c" if var > 0 else ("#2ecc71" if var < 0 else "#888")

        # Destaque visual para o maior e menor
        destaque = ""
        if estado == sorted_estados[0][0]:
            destaque = ' 🏆'
        elif estado == sorted_estados[-1][0]:
            destaque = ' ⬇️'

        linhas.append(f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;font-weight:600;">{estado}{destaque}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;font-weight:bold;">R$ {preco:.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;color:{cor_var};">
                {sinal} {var:+.2f}%
            </td>
        </tr>""")

    media_html = ""
    if media:
        media_html = f"""
        <tr style="background:#e8f5e9;">
            <td style="padding:8px;font-weight:700;">📊 Média Nacional</td>
            <td style="padding:8px;text-align:right;font-weight:700;font-size:16px;">R$ {media:.2f}</td>
            <td style="padding:8px;text-align:right;"></td>
        </tr>"""

    return f"""
    <div style="font-size:12px;color:#888;margin-bottom:8px;">
        📅 Dados de {data_ref} — Fonte oficial: <strong>Indicador do Boi DATAGRO</strong> (referência B3)
    </div>
    <div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>Estado</th>
                <th style="text-align:right;">Preço (R$/@)</th>
                <th style="text-align:right;">Variação</th>
            </tr>
        </thead>
        <tbody>
            {''.join(linhas)}
            {media_html}
        </tbody>
    </table>
    </div>"""


def gerar_dashboard(dados_precos: dict, dados_cepea: dict,
                    dados_clima: list, alertas: list,
                    output_path: str = None,
                    usuario_id: int | None = None,
                    dados_datagro: dict | None = None) -> str:
    """Gera o dashboard HTML completo."""
    hoje = date.today().strftime("%d/%m/%Y")
    registros = banco.pegar_ultimos_precos(60)

    grafico = gerar_grafico_precos(registros)
    tabela_alertas = gerar_tabela_alertas(alertas)
    resumo_clima = gerar_resumo_clima(dados_clima)
    resumo_trades = gerar_resumo_trades(usuario_id)
    tabela_stats = gerar_tabela_estatisticas_sinais()
    tabela_acertos = acertos.resumo_para_dashboard()
    tabela_datagro = gerar_tabela_datagro(dados_datagro or {})
    historico = pegar_estatisticas_historicas()

    def _card_historico(ativo: str, rotulo: str, dados_hist: dict, unidade: str) -> str:
        if not dados_hist:
            return ""
        var = dados_hist.get("variacao_media", 0)
        pct = dados_hist.get("percentil", 50)
        atual = dados_hist.get("atual", 0)
        media = dados_hist.get("media", 0)
        minimo = dados_hist.get("minimo", 0)
        maximo = dados_hist.get("maximo", 0)
        seta = "▲" if var > 0 else "▼"
        cor = "#e74c3c" if var > 10 else ("#2ecc71" if var < -10 else "#f39c12")
        largura_barra = 120
        pos = max(0, min(largura_barra, (atual - minimo) / (maximo - minimo + 0.01) * largura_barra))
        return f"""
        <div style="background:#f8f9fa;border-radius:10px;padding:14px;flex:1;min-width:200px;">
            <div style="font-size:12px;color:#888;margin-bottom:6px;">{rotulo} <strong>{unidade}</strong></div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;">
                <span style="font-size:22px;font-weight:bold;">{atual:.2f}</span>
                <span style="font-size:13px;color:{cor};font-weight:600;">{seta} {abs(var):.1f}%</span>
            </div>
            <div style="font-size:11px;color:#999;margin-top:4px;">Média 10a: {media:.2f} | P{pct}</div>
            <div style="margin-top:6px;height:6px;background:#eee;border-radius:3px;position:relative;">
                <div style="position:absolute;left:0;top:0;height:6px;border-radius:3px;background:linear-gradient(90deg,#2ecc71,#f39c12,#e74c3c);width:{largura_barra}px;"></div>
                <div style="position:absolute;left:{pos}px;top:-3px;width:12px;height:12px;background:#333;border-radius:50%;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.3);"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:10px;color:#bbb;margin-top:2px;">
                <span>{minimo:.1f}</span>
                <span>{maximo:.1f}</span>
            </div>
            <div style="font-size:11px;color:#666;margin-top:6px;">{pct:.0f}% das vezes esteve mais barato</div>
        </div>"""

    card_cbot = _card_historico("cbot", "🌽 CBOT", historico.get("cbot", {}), "¢/bushel")
    card_dolar = _card_historico("dolar", "💵 Dólar", historico.get("dolar", {}), "R$/USD")

    # Card de destaque
    dolar = dados_precos.get("dolar", "—")
    cbot = dados_precos.get("cbot", "—")
    cepea_milho = dados_cepea.get("milho_cepea", "—")
    cepea_boi = dados_cepea.get("arroba_cepea", "—")
    # Verifica se tem DATAGRO
    tem_datagro = dados_datagro and dados_datagro.get("_media_nacional")
    if tem_datagro:
        cepea_boi = f'{dados_datagro["_media_nacional"]:.2f}'
    fonte_milho = "oficial" if dados_cepea.get("milho_cepea") else "estimado"
    badge_oficial = '<span class="badge badge-cepea">CEPEA</span>'
    badge_estimado = '<span class="badge badge-estimado">ESTIMADO</span>'
    badge_datagro = '<span class="badge badge-datagro">DATAGRO ✓ B3</span>'

    alerta_count = len(alertas)
    alerta_count_prioritario = len([a for a in alertas if a.get("confianca") == "alta"])

    if alerta_count_prioritario > 0:
        alerta_badge = f'<span class="alerta-badge alerta-badge-critico">🔴 {alerta_count_prioritario} prioritário(s)</span>'
    else:
        alerta_badge = '<span class="alerta-badge alerta-badge-ok">✅ Sem alertas críticos</span>'

    # ─── AO VIVO: OHLC + Volume (Yahoo intraday) ──────────────
    b3_atualizado = "—"
    cbot_ohlc = {"abertura":"—","maxima":"—","minima":"—","atual":"—","sinal_variacao":"―","variacao":None}
    cbot_vol = "—"
    cbot_forca = 50
    dolar_ohlc = {"abertura":"—","maxima":"—","minima":"—","atual":"—","sinal_variacao":"―","variacao":None}
    dolar_vol = "—"
    dolar_forca = 50
    try:
        from coletores import b3_ao_vivo
        b3 = b3_ao_vivo.coletar_todos()
        b3_atualizado = b3.get("atualizado_em","")
        if b3.get("cbot",{}).get("disponivel"):
            cbot_ohlc = b3["cbot"]
            cv = b3["cbot"].get("volume_total",0)
            cbot_vol = f"{cv:,}" if cv else "—"
            cbot_forca = b3["cbot"].get("forca_compradora",50)
        if b3.get("dolar",{}).get("disponivel"):
            dolar_ohlc = b3["dolar"]
            dv = b3["dolar"].get("volume_total",0)
            dolar_vol = f"{dv:,}" if dv else "—"
            dolar_forca = b3["dolar"].get("forca_compradora",50)
    except Exception as e:
        pass

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgroSinal — {hoje}</title>
    <meta name="theme-color" content="#1a472a">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background:#f0f2f5; color:#333; padding:0;
            -webkit-font-smoothing:antialiased;
        }}
        .container {{ max-width:1200px; margin:0 auto; padding:8px; }}
        .header {{
            background: linear-gradient(135deg, #1a472a, #2d6a4f);
            color:white; padding:14px 16px; border-radius:14px; margin-bottom:10px;
            display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:6px;
            position:relative; overflow:hidden;
        }}
        .header::after {{
            content:''; position:absolute; top:-50%; right:-30%;
            width:120px; height:120px; background:rgba(255,255,255,0.04); border-radius:50%;
        }}
        .header-left {{ display:flex; flex-direction:column; }}
        .header h1 {{ font-size:18px; line-height:1.3; }}
        .header .data {{ font-size:11px; opacity:0.75; margin-top:1px; }}
        .header-actions {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
        .header-actions a {{
            color:white; font-size:12px; text-decoration:none;
            padding:5px 10px; border-radius:20px; background:rgba(255,255,255,0.12);
            transition:all .2s; white-space:nowrap;
        }}
        .header-actions a:active {{ background:rgba(255,255,255,0.25); }}
        .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px; }}
        .card {{
            background:white; border-radius:12px; padding:12px;
            box-shadow:0 1px 3px rgba(0,0,0,0.05);
            transition:transform .15s, box-shadow .15s;
        }}
        .card:active {{ transform:scale(.97); }}
        .card h3 {{
            font-size:10px; color:#888; margin-bottom:4px;
            text-transform:uppercase; letter-spacing:0.3px; font-weight:600;
        }}
        .card .valor {{ font-size:20px; font-weight:700; line-height:1.2; }}
        .card .variacao {{ font-size:10px; margin-top:2px; }}
        .card .resumo {{ font-size:10px; color:#666; margin-top:4px; padding-top:4px; border-top:1px solid #eee; line-height:1.4; }}
        .card-full {{ grid-column:1/-1; }}
        .badge {{ display:inline-block; font-size:8px; padding:2px 7px; border-radius:10px; font-weight:600; vertical-align:middle; margin-left:4px; }}
        .badge-datagro {{ background:#27ae60; color:white; }}
        .badge-cepea {{ background:#2e86de; color:white; }}
        .badge-estimado {{ background:#f39c12; color:white; }}
        .alerta-badge {{ display:inline-block; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600; }}
        .alerta-badge-critico {{ background:#e74c3c; color:white; }}
        .alerta-badge-ok {{ background:#2ecc71; color:white; }}
        .table-wrap {{ overflow-x:auto; -webkit-overflow-scrolling:touch; margin:0 -4px; padding:0 4px; }}
        .table-wrap::-webkit-scrollbar {{ height:3px; }}
        .table-wrap::-webkit-scrollbar-thumb {{ background:#ddd; border-radius:3px; }}
        table {{ width:100%; border-collapse:collapse; font-size:12px; min-width:400px; }}
        th, td {{ padding:7px 5px; text-align:left; border-bottom:1px solid #f0f0f0; }}
        th {{ background:#f8f9fa; font-weight:600; font-size:11px; color:#666; white-space:nowrap; }}
        tr:active {{ background:#f8f9fa; }}
        .clima-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
        .clima-card {{ background:#f8f9fa; border-radius:10px; padding:10px; text-align:center; }}
        .clima-card .regiao {{ font-size:11px; color:#666; margin-bottom:2px; }}
        .clima-card .temp {{ font-size:20px; font-weight:700; margin:2px 0; }}
        .clima-card .detalhes {{ font-size:10px; color:#888; }}
        .footer {{ text-align:center; padding:14px 8px; color:#aaa; font-size:11px; }}
        @media(min-width:768px) {{
            body {{ padding:16px; }}
            .container {{ padding:0; }}
            .header {{ padding:22px 28px; border-radius:16px; margin-bottom:16px; }}
            .header h1 {{ font-size:26px; }}
            .header .data {{ font-size:13px; }}
            .header-actions a {{ font-size:13px; padding:6px 14px; }}
            .grid {{ grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin-bottom:16px; }}
            .card {{ padding:18px; border-radius:14px; }}
            .card h3 {{ font-size:11px; }}
            .card .valor {{ font-size:28px; }}
            .card .variacao {{ font-size:12px; }}
            .card .resumo {{ font-size:12px; }}
            .card-full {{ padding:20px; }}
            table {{ font-size:13px; }}
            th, td {{ padding:9px 8px; }}
            .clima-grid {{ grid-template-columns:repeat(4,1fr); gap:12px; }}
            .clima-card {{ padding:14px; }}
            .clima-card .temp {{ font-size:24px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>🌱 AgroSinal</h1>
                <span class="data">{hoje}</span>
            </div>
            <div class="header-actions">
                {alerta_badge}
                <a href="/minha-conta" style="color:white;font-size:13px;text-decoration:none;opacity:.9;">⚙️ Conta</a>
                <a href="/" style="color:white;font-size:13px;text-decoration:none;opacity:.8;">← Sair</a>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>💵 Dólar</h3>
                <div class="valor">{dolar if dolar != '—' else '—'}</div>
                <div class="variacao green">Referência pré-mercado</div>
                <div class="resumo">Dólar impacta milho e boi diretamente (exportação)</div>
            </div>
            <div class="card">
                <h3>🌽 CBOT Chicago</h3>
                <div class="valor">{cbot if cbot != '—' else '—'}</div>
                <div class="variacao orange">Referência internacional</div>
                <div class="resumo">CBOT é o preço global do milho — B3 segue</div>
            </div>
            <div class="card">
                <h3>🌽 Milho CEPEA {badge_oficial if fonte_milho == 'oficial' else badge_estimado}</h3>
                <div class="valor">{'R$ ' + str(cepea_milho) if cepea_milho != '—' else '—'}</div>
                <div class="variacao orange">Físico (R$/saca)</div>
                <div class="resumo">{'Indicador ESALQ/B3' if cepea_milho != '—' else 'Indisponível hoje'}</div>
            </div>
            <div class="card">
                <h3>🐄 Boi Gordo {badge_datagro if tem_datagro else (badge_oficial if fonte_milho == 'oficial' else badge_estimado)}</h3>
                <div class="valor">{'R$ ' + cepea_boi if cepea_boi != '—' else '—'}</div>
                <div class="variacao green">Físico (R$/@) — Média nacional</div>
                <div class="resumo">{'Indicador do Boi DATAGRO — referência oficial da B3' if tem_datagro else 'Indisponível hoje'}</div>
            </div>
        </div>

        <!-- 🔴 AO VIVO — CBOT Milho -->
        <div class="card" style="border-left:3px solid #e74c3c;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <h3 style="text-transform:none;letter-spacing:0;">🔴 AO VIVO — CBOT Milho</h3>
                <span style="font-size:10px;color:#999;">▲ sobe ▼ desce</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:6px;">
                <div><span style="font-size:9px;color:#888;">Abertura</span><div style="font-size:16px;font-weight:700;">{cbot_ohlc.get("abertura","—")}</div></div>
                <div><span style="font-size:9px;color:#888;">Máxima</span><div style="font-size:16px;font-weight:700;color:#e74c3c;">{cbot_ohlc.get("maxima","—")}</div></div>
                <div><span style="font-size:9px;color:#888;">Mínima</span><div style="font-size:16px;font-weight:700;color:#2ecc71;">{cbot_ohlc.get("minima","—")}</div></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;padding-top:6px;border-top:1px solid #eee;">
                <div>
                    <span style="font-size:9px;color:#888;">Atual</span>
                    <div style="font-size:18px;font-weight:800;">{cbot_ohlc.get("atual","—")} <span style="font-size:12px;color:{'#e74c3c' if str(cbot_ohlc.get('sinal_variacao','')) == '▲' else '#2ecc71' if str(cbot_ohlc.get('sinal_variacao','')) == '▼' else '#888'};"}}>{cbot_ohlc.get("sinal_variacao","―")} {cbot_ohlc.get("variacao","")}{'%' if cbot_ohlc.get("variacao") is not None else ''}</span></div>
                </div>
                <div>
                    <span style="font-size:9px;color:#888;">Volume</span>
                    <div style="font-size:16px;font-weight:700;">{cbot_vol}</div>
                </div>
            </div>
            <div style="font-size:10px;color:#999;margin-top:6px;padding-top:4px;border-top:1px solid #eee;">
                ▲ subida: {cbot_ohlc.get("volume_subida","0")} contratos &nbsp;|&nbsp; ▼ descida: {cbot_ohlc.get("volume_descida","0")} contratos
                <span style="float:right;">🕐 {cbot_ohlc.get("atualizado_em","")}</span>
            </div>
            <div style="margin-top:4px;height:4px;background:#eee;border-radius:2px;">
                <div style="height:4px;border-radius:2px;background:linear-gradient(90deg,#2ecc71,#f39c12,#e74c3c);width:{cbot_forca}%;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:9px;color:#999;margin-top:2px;">
                <span>100% venda</span>
                <span style="font-weight:600;">Força: {cbot_forca}%</span>
                <span>100% compra</span>
            </div>
        </div>

        <!-- 🔴 AO VIVO — Dólar -->
        <div class="card" style="border-left:3px solid #e74c3c;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <h3 style="text-transform:none;letter-spacing:0;">🔴 AO VIVO — Dólar</h3>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:6px;">
                <div><span style="font-size:9px;color:#888;">Abertura</span><div style="font-size:16px;font-weight:700;">{dolar_ohlc.get("abertura","—")}</div></div>
                <div><span style="font-size:9px;color:#888;">Máxima</span><div style="font-size:16px;font-weight:700;color:#e74c3c;">{dolar_ohlc.get("maxima","—")}</div></div>
                <div><span style="font-size:9px;color:#888;">Mínima</span><div style="font-size:16px;font-weight:700;color:#2ecc71;">{dolar_ohlc.get("minima","—")}</div></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;padding-top:6px;border-top:1px solid #eee;">
                <div>
                    <span style="font-size:9px;color:#888;">Atual</span>
                    <div style="font-size:18px;font-weight:800;">{dolar_ohlc.get("atual","—")} <span style="font-size:12px;color:{'#e74c3c' if str(dolar_ohlc.get('sinal_variacao','')) == '▲' else '#2ecc71' if str(dolar_ohlc.get('sinal_variacao','')) == '▼' else '#888'};"}}>{dolar_ohlc.get("sinal_variacao","―")} {dolar_ohlc.get("variacao","")}{'%' if dolar_ohlc.get("variacao") is not None else ''}</span></div>
                </div>
                <div>
                    <span style="font-size:9px;color:#888;">Volume</span>
                    <div style="font-size:16px;font-weight:700;">{dolar_vol}</div>
                </div>
            </div>
            <div style="font-size:10px;color:#999;margin-top:6px;padding-top:4px;border-top:1px solid #eee;">
                ▲ subida: {dolar_ohlc.get("volume_subida","0")} &nbsp;|&nbsp; ▼ descida: {dolar_ohlc.get("volume_descida","0")}
                <span style="float:right;">🕐 {dolar_ohlc.get("atualizado_em","")}</span>
            </div>
            <div style="margin-top:4px;height:4px;background:#eee;border-radius:2px;">
                <div style="height:4px;border-radius:2px;background:linear-gradient(90deg,#2ecc71,#f39c12,#e74c3c);width:{dolar_forca}%;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:9px;color:#999;margin-top:2px;">
                <span>100% queda</span>
                <span style="font-weight:600;">Força: {dolar_forca}%</span>
                <span>100% alta</span>
            </div>
        </div>

        <!-- 🔴 AO VIVO — Legenda -->
        <div class="card card-full" style="border-left:3px solid #e74c3c;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <h3 style="text-transform:none;letter-spacing:0;">🔴 AO VIVO — Resumo</h3>
                <span style="font-size:10px;color:#999;">🕐 {b3_atualizado}</span>
            </div>
            <div style="font-size:10px;color:#888;line-height:1.5;">
                🔄 Dados com ~15 min de atraso (Yahoo Finance). Volume = contratos negociados.
                Força compradora mostra % do volume total que ocorreu em candles de <strong>subida</strong>.
                &gt;60% = pressão compradora. &lt;40% = pressão vendedora.
            </div>
        </div>

        <div class="card card-full">
            <h3>📊 Alertas e Sinais do Dia</h3>
            {tabela_alertas}
        </div>

        <div class="card card-full">
            <h3>📊 Comparativo Histórico (10 anos)</h3>
            <div style="display:flex;gap:10px;flex-wrap:wrap;">
                {card_cbot}
                {card_dolar}
            </div>
            <div style="margin-top:8px;font-size:11px;color:#888;">
                O gráfico abaixo mostra onde o preço atual se posiciona na faixa dos últimos 10 anos. Ponto ● = preço atual.
            </div>
        </div>

        <div class="card card-full">
            <h3>🌤️ Clima — Regiões Relevantes</h3>
            {resumo_clima}
            <div style="margin-top:10px;font-size:12px;color:#888;">
                Regiões monitoradas: Sorriso-MT (milho), Campo Grande-MS (milho+boi), Uberaba-MG, Rio Verde-GO
            </div>
        </div>

        <div class="card card-full">
            <h3>🐄 Indicador do Boi DATAGRO — Preços por Estado</h3>
            {tabela_datagro}
            <div style="margin-top:10px;font-size:12px;color:#888;">
                O <strong>Indicador do Boi DATAGRO</strong> é a referência oficial da B3 para liquidação dos contratos futuros de pecuária. Aprovado pela CVM.
            </div>
        </div>

        <div class="card card-full">
            <h3>📈 Evolução dos Preços</h3>
            {grafico}
        </div>

        <div class="card card-full">
            <h3>📋 Minha Carteira</h3>
            {resumo_trades}
        </div>

        <div class="card card-full">
            <h3>🎯 Taxa de Acerto por Padrão</h3>
            {tabela_stats}
        </div>

        <div class="card card-full">
            <h3>📈 Performance dos Sinais (90 dias)</h3>
            {tabela_acertos}
        </div>

        <div class="footer">
            AgroSinal v2.0 — Análise multi-indicador com dados Yahoo Finance + CEPEA + Clima
        </div>
    </div>
</body>
</html>"""

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html


# ─── Histórico de Sinais ────────────────────────────────────

def gerar_historico_sinais(sinais_data: dict, stats: dict, pagina: int,
                            tipo: str | None, status: str | None,
                            nome: str = "Usuário", plano: str = "gratis") -> str:
    """Gera página HTML com histórico completo de sinais."""
    hoje = date.today().strftime("%d/%m/%Y")
    resumo = stats.get("resumo", {})
    por_tipo = stats.get("por_tipo", [])
    sinais = sinais_data.get("sinais", [])
    total = sinais_data.get("total", 0)

    # Estatísticas
    total_sinais = resumo.get("total", 0)
    acertos = resumo.get("acertos", 0)
    erros = resumo.get("erros", 0)
    pendentes = resumo.get("pendentes", 0)
    taxa = resumo.get("taxa_acerto", 0)

    # Monta tabela de tipos
    linhas_tipos = ""
    for t in por_tipo:
        emoji = "🟢" if t["taxa_acerto"] >= 60 else "🟡" if t["taxa_acerto"] >= 40 else "🔴"
        linhas_tipos += f"<tr><td>{t['tipo']}</td><td>{t['direcao']}</td><td>{t['total']}</td><td>{t['acertos']}</td><td>{t['erros']}</td><td>{emoji} {t['taxa_acerto']}%</td></tr>"

    # Filtro select
    opcoes_tipo = {"": "Todos", "cbot": "CBOT", "analise_milho": "Milho", "analise_boi": "Boi",
                  "relacao_boi_milho": "Relação B/M", "dolar": "Dólar", "combinado_milho": "Sinais Fortes",
                  "historico_cbot": "Hist. CBOT", "historico_dolar": "Hist. Dólar",
                  "sazonalidade_milho": "Saz. Milho", "sazonalidade_boi": "Saz. Boi"}
    filtro_tipo_html = "".join(
        f'<option value="{k}" {"selected" if tipo == k or (not tipo and not k) else ""}>{v}</option>'
        for k, v in opcoes_tipo.items()
    )

    # Tabela de sinais
    linhas_sinais = ""
    for s in sinais:
        sid = s["id"]
        emoji_conf = {"alta": "🔴", "media": "🟡", "baixa": "⚪"}.get(s["confianca"], "⚪")
        status_emoji = "✅" if s["acertou"] == "sim" else "❌" if s["acertou"] == "nao" else "⏳"
        preco_exibir = f"R$ {s['preco_alvo']}" if s.get("preco_alvo") else "-"
        botoes = ""
        if s["acertou"] is None:
            botoes = f'''
            <div style="display:flex;gap:4px;">
                <button class="btn-acerto" onclick="avaliar({sid},'sim')">✅</button>
                <button class="btn-erro" onclick="avaliar({sid},'nao')">❌</button>
                <button class="btn-entrar" onclick="entrar({sid})" style="background:#27ae60;color:white;border:none;padding:4px 10px;border-radius:8px;font-size:11px;cursor:pointer;">ENTRAR</button>
            </div>'''
        else:
            botoes = status_emoji

        explicacao_curta = (s.get("explicacao", "") or "")[:60]
        linhas_sinais += f"""<tr>
            <td>#{sid}</td>
            <td>{s['data']}</td>
            <td>{s['tipo']}</td>
            <td>{s['ativo']}</td>
            <td>{s['direcao'][:12]}</td>
            <td>{emoji_conf} {s['confianca']}</td>
            <td>{preco_exibir}</td>
            <td>{botoes}</td>
            <td style="font-size:11px;color:#888;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{explicacao_curta}...</td>
        </tr>"""

    # Monta HTML completo
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📜 Histórico de Sinais — AgroSinal</title>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background:#f0f2f5; color:#333; padding:8px;
    }}
    .container {{ max-width:1100px; margin:0 auto; }}
    .header {{
        background: linear-gradient(135deg, #1a472a, #2d6a4f);
        color:white; padding:14px 16px; border-radius:14px; margin-bottom:12px;
        display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;
    }}
    .header h1 {{ font-size:18px; }}
    .header a {{ color:white; text-decoration:none; font-size:12px; padding:5px 10px; border-radius:20px; background:rgba(255,255,255,0.12); }}
    .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(140px,1fr)); gap:8px; margin-bottom:12px; }}
    .stat-card {{ background:white; border-radius:12px; padding:12px; text-align:center; }}
    .stat-card .numero {{ font-size:24px; font-weight:700; }}
    .stat-card .label {{ font-size:10px; color:#888; text-transform:uppercase; margin-top:2px; }}
    .verde {{ color:#27ae60; }}
    .vermelho {{ color:#e74c3c; }}
    .amarelo {{ color:#f39c12; }}
    .filtros {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; align-items:center; }}
    .filtros select {{
        padding:8px 12px; border-radius:10px; border:1px solid #ddd; font-size:13px;
        background:white;
    }}
    .table-wrap {{ overflow-x:auto; margin-bottom:12px; }}
    table {{ width:100%; border-collapse:collapse; font-size:11px; }}
    th, td {{ padding:7px 5px; text-align:left; border-bottom:1px solid #f0f0f0; }}
    th {{ background:#f8f9fa; font-weight:600; color:#666; font-size:10px; white-space:nowrap; }}
    .btn-acerto, .btn-erro {{
        border:none; padding:4px 8px; border-radius:8px; cursor:pointer;
        font-size:14px; transition:transform .1s;
    }}
    .btn-acerto:active, .btn-erro:active {{ transform:scale(.9); }}
    .toast {{
        position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
        background:#333; color:white; padding:10px 20px; border-radius:12px;
        font-size:13px; display:none; z-index:999;
    }}
    .modal {{
        position:fixed; top:0; left:0; width:100%; height:100%;
        background:rgba(0,0,0,0.5); display:none; justify-content:center;
        align-items:center; z-index:1000;
    }}
    .modal-content {{
        background:white; border-radius:14px; padding:20px; max-width:380px;
        width:90%; box-shadow:0 4px 20px rgba(0,0,0,0.2);
    }}
    .modal-content h3 {{ margin-bottom:10px; font-size:16px; }}
    .modal-content label {{ font-size:12px; color:#555; display:block; margin-top:8px; }}
    .modal-content input {{
        width:100%; padding:8px 10px; border:1px solid #ddd; border-radius:8px;
        font-size:14px; margin-top:3px;
    }}
    .modal-content button {{
        margin-top:14px; width:100%; padding:10px; border:none; border-radius:10px;
        font-size:14px; cursor:pointer;
    }}
    .btn-confirm {{ background:#27ae60; color:white; }}
    .btn-cancel {{ background:#eee; color:#666; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📜 Histórico de Sinais</h1>
        <div style="display:flex;gap:8px;">
            <a href="/dashboard">← Dashboard</a>
            <a href="/dashboard/performance">🏆 Performance</a>
            <a href="/">Sair</a>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="numero">{total_sinais}</div>
            <div class="label">Total de Sinais</div>
        </div>
        <div class="stat-card">
            <div class="numero verde">{acertos}</div>
            <div class="label">✅ Acertos</div>
        </div>
        <div class="stat-card">
            <div class="numero vermelho">{erros}</div>
            <div class="label">❌ Erros</div>
        </div>
        <div class="stat-card">
            <div class="numero amarelo">{pendentes}</div>
            <div class="label">⏳ Pendentes</div>
        </div>
        <div class="stat-card">
            <div class="numero verde" style="font-size:28px;">{taxa}%</div>
            <div class="label">📊 Taxa de Acerto</div>
        </div>
    </div>

    <div class="table-wrap" style="margin-bottom:12px;">
        <table>
            <tr><th>Tipo</th><th>Direção</th><th>Total</th><th>Acertos</th><th>Erros</th><th>Taxa</th></tr>
            {linhas_tipos if linhas_tipos else "<tr><td colspan='6' style='text-align:center;color:#999;padding:20px;'>Nenhum sinal avaliado ainda</td></tr>"}
        </table>
    </div>

    <div class="filtros">
        <select onchange="window.location='/dashboard/historico?tipo='+this.value+'&status='+document.getElementById('filtro-status').value">
            {filtro_tipo_html}
        </select>
        <select id="filtro-status" onchange="window.location='/dashboard/historico?status='+this.value+'&tipo='+document.getElementById('filtro-tipo').value">
            <option value="" {"selected" if not status else ""}>Todos os status</option>
            <option value="aberto" {"selected" if status=="aberto" else ""}>⏳ Pendentes</option>
            <option value="acertou" {"selected" if status=="acertou" else ""}>✅ Acertou</option>
            <option value="errou" {"selected" if status=="errou" else ""}>❌ Errou</option>
        </select>
        <span style="color:#888;font-size:12px;">{total} sinais</span>
    </div>

    <div class="table-wrap">
        <table>
            <tr>
                <th>#</th><th>Data</th><th>Tipo</th><th>Ativo</th><th>Direção</th>
                <th>Confiança</th><th>Preço</th><th>Ação</th><th>Explicação</th>
            </tr>
            {linhas_sinais if linhas_sinais else "<tr><td colspan='9' style='text-align:center;color:#999;padding:30px;'>Nenhum sinal encontrado. Os sinais são gerados automaticamente pela análise do sistema.</td></tr>"}
        </table>
    </div>

    <div style="text-align:center;padding:12px;color:#aaa;font-size:11px;">
        AgroSinal — Histórico de Sinais | {hoje}
    </div>
</div>

<!-- Modal de Entrada -->
<div id="modal-entrar" class="modal">
    <div class="modal-content">
        <h3>🚀 Entrar neste Sinal</h3>
        <p id="modal-desc" style="font-size:12px;color:#888;margin-bottom:10px;">Sinal #<span id="modal-sid"></span></p>
        <label>💰 Preço de Entrada (R$)</label>
        <input type="number" id="preco-entrada" step="0.01" placeholder="Ex: 65.50">
        <label>📦 Quantidade (sacas/@)</label>
        <input type="number" id="quantidade" step="0.1" value="1.0" placeholder="1">
        <button class="btn-confirm" onclick="confirmarEntrada()">✅ Confirmar Entrada</button>
        <button class="btn-cancel" onclick="fecharModal()">Cancelar</button>
    </div>
</div>

<div id="toast" class="toast"></div>

<script>
var sinalAtualId = null;

function toast(msg, cor) {{
    var t = document.getElementById('toast');
    t.textContent = msg; t.style.display = 'block';
    t.style.background = cor || '#333';
    setTimeout(function() {{ t.style.display = 'none'; }}, 3000);
}}

function avaliar(id, resultado) {{
    fetch('/api/sinais/' + id + '/avaliar', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ 'acertou': resultado }})
    }})
    .then(r => r.json())
    .then(d => {{
        toast(resultado === 'sim' ? '✅ Sinal #' + id + ' marcado como ACERTOU!' : '❌ Sinal #' + id + ' marcado como ERROU!', '#27ae60');
        setTimeout(function() {{ location.reload(); }}, 1000);
    }})
    .catch(e => toast('Erro ao avaliar sinal', '#e74c3c'));
}}

function entrar(id) {{
    sinalAtualId = id;
    document.getElementById('modal-sid').textContent = id;
    document.getElementById('modal-entrar').style.display = 'flex';
}}

function fecharModal() {{
    document.getElementById('modal-entrar').style.display = 'none';
    sinalAtualId = null;
}}

function confirmarEntrada() {{
    var preco = parseFloat(document.getElementById('preco-entrada').value);
    var qtd = parseFloat(document.getElementById('quantidade').value) || 1.0;
    if (!preco || preco <= 0) {{
        toast('⚠️ Informe um preço de entrada válido', '#f39c12');
        return;
    }}
    fetch('/api/operacoes/entrar', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ sinal_id: sinalAtualId, preco_entrada: preco, quantidade: qtd }})
    }})
    .then(r => r.json())
    .then(d => {{
        fecharModal();
        if (d.status === 'ok') {{
            toast(d.mensagem + ' 🎯', '#27ae60');
            setTimeout(function() {{ location.reload(); }}, 1500);
        }} else {{
            toast('⚠️ ' + (d.detail || 'Erro'), '#e74c3c');
        }}
    }})
    .catch(e => toast('Erro ao entrar no sinal', '#e74c3c'));
}}
</script>
</body>
</html>"""
    return html


# ─── Página de Performance ──────────────────────────────────

def gerar_performance_usuario(perf: dict, operacoes_raw: list, geral: dict,
                               nome: str = "Usuário", plano: str = "gratis") -> str:
    """Gera página HTML com performance completa do usuário."""
    hoje = date.today().strftime("%d/%m/%Y")
    p = perf

    emoji_taxa = "🔥" if p["taxa_acerto"] >= 70 else ("📊" if p["taxa_acerto"] >= 50 else "⚠️")
    emoji_lucro = "🟢" if p["lucro_total"] > 0 else ("🔴" if p["lucro_total"] < 0 else "⚪")
    emoji_maior = "🏆" if p["maior_lucro"] > 0 else "💀"

    # ─── Tabela de operações ───
    linhas_ops = ""
    for t in operacoes_raw:
        tid, sinal_id, ativo, tipo_op = t[0], t[1], t[2], t[3]
        preco_ent, preco_sai, data_ent, data_sai = t[4], t[5], t[6], t[7]
        resultado, pnl_val, dias = t[8], t[9], t[10]
        qtd = t[14] if len(t) > 14 else 1.0
        sinal_expl = t[15] if len(t) > 15 else ""

        if resultado == "aberto":
            pnl_exibir = '<span style="color:#f39c12;">⏳ Aberto</span>'
        elif resultado == "lucro":
            pnl_exibir = '<span style="color:#27ae60;">+R$ ' + str(round(pnl_val or 0, 2)) + '</span>'
        else:
            pnl_exibir = '<span style="color:#e74c3c;">-R$ ' + str(abs(round(pnl_val or 0, 2))) + '</span>'

        seta_dir = "🟢" if tipo_op == "compra" else "🔴"
        linhas_ops += """<tr>
            <td>#""" + str(tid) + """</td>
            <td>""" + (data_ent or "-") + """</td>
            <td>""" + (data_sai or "⏳") + """</td>
            <td>""" + seta_dir + " " + tipo_op[:10] + """</td>
            <td>""" + ativo + """</td>
            <td>""" + str(qtd) + """</td>
            <td>R$ """ + str(round(preco_ent, 2)) + """</td>
            <td>""" + ("R$ " + str(round(preco_sai, 2)) if preco_sai else "⏳") + """</td>
            <td>""" + pnl_exibir + """</td>
            <td>""" + (str(dias) if dias else "-") + """d</td>
            <td style="font-size:10px;color:#888;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">""" + (sinal_expl[:40] or "-") + """</td>
        </tr>"""

    # ─── Por Ativo ───
    linhas_ativos = ""
    for a in p.get("por_ativo", []):
        emoji_a = "🟢" if a["taxa"] >= 60 else ("🟡" if a["taxa"] >= 40 else "🔴")
        linhas_ativos += "<tr><td>" + a['ativo'] + "</td><td>" + str(a['total']) + "</td><td>" + str(a['vitorias']) + "V/" + str(a['derrotas']) + "D</td><td>" + emoji_a + " " + str(a['taxa']) + "%</td><td>R$ " + str(a['lucro']) + "</td></tr>"

    # ─── Mensal ───
    linhas_mensal = ""
    for m in p.get("mensal", []):
        emoji_m = "🟢" if m["resultado"] > 0 else "🔴"
        linhas_mensal += "<tr><td>" + m['mes'] + "</td><td>" + str(m['total']) + " ops</td><td>" + emoji_m + " R$ " + str(m['resultado']) + "</td></tr>"

    # ─── Geral (visão admin) ───
    g = geral
    taxa_geral = g.get("taxa_acerto_geral", 0)

    lucro_total = p["lucro_total"]
    classe_lucro = "verde" if lucro_total >= 0 else "vermelho"

    html_parts = []
    html_parts.append('''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏆 Minha Performance — AgroSinal</title>
<style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background:#f0f2f5; color:#333; padding:8px;
    }
    .container { max-width:1100px; margin:0 auto; }
    .header {
        background: linear-gradient(135deg, #1a472a, #2d6a4f);
        color:white; padding:14px 16px; border-radius:14px; margin-bottom:12px;
        display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;
    }
    .header h1 { font-size:18px; }
    .header a { color:white; text-decoration:none; font-size:12px; padding:5px 10px; border-radius:20px; background:rgba(255,255,255,0.12); }
    .perf-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:8px; margin-bottom:12px; }
    .perf-card { background:white; border-radius:12px; padding:14px; text-align:center; }
    .perf-card .big { font-size:28px; font-weight:700; }
    .perf-card .label { font-size:10px; color:#888; text-transform:uppercase; margin-top:2px; }
    .perf-card .sub { font-size:11px; color:#666; margin-top:4px; }
    .verde { color:#27ae60; } .vermelho { color:#e74c3c; } .amarelo { color:#f39c12; }
    .card { background:white; border-radius:12px; padding:14px; margin-bottom:12px; }
    .card h3 { font-size:12px; color:#555; text-transform:uppercase; margin-bottom:10px; }
    .table-wrap { overflow-x:auto; margin-bottom:8px; }
    table { width:100%; border-collapse:collapse; font-size:11px; }
    th, td { padding:7px 5px; text-align:left; border-bottom:1px solid #f0f0f0; }
    th { background:#f8f9fa; font-weight:600; color:#666; font-size:10px; white-space:nowrap; }
    .geral-banner {
        background: linear-gradient(135deg, #2d6a4f, #1a472a);
        color:white; border-radius:12px; padding:16px; margin-bottom:12px; text-align:center;
    }
    .geral-banner h2 { font-size:22px; }
    .geral-banner p { font-size:13px; opacity:0.9; margin-top:4px; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🏆 Minha Performance</h1>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <a href="/dashboard">← Dashboard</a>
            <a href="/dashboard/historico">📜 Histórico</a>
            <a href="/">Sair</a>
        </div>
    </div>

    <div class="perf-grid">
        <div class="perf-card">
            <div class="big">''' + emoji_taxa + ' ' + str(p['taxa_acerto']) + '''%</div>
            <div class="label">📊 Taxa de Acerto</div>
            <div class="sub">''' + str(p['vitorias']) + 'V / ' + str(p['derrotas']) + '''D</div>
        </div>
        <div class="perf-card">
            <div class="big ''' + classe_lucro + '''">''' + emoji_lucro + ' R$ ' + f'{lucro_total:.2f}' + '''</div>
            <div class="label">💰 Lucro Total</div>
            <div class="sub">''' + str(p['total']) + ''' operações fechadas</div>
        </div>
        <div class="perf-card">
            <div class="big">''' + str(p['abertos']) + '''</div>
            <div class="label">⏳ Operações Abertas</div>
            <div class="sub">R$ ''' + f"{p['capital_aberto']:.2f}" + ''' em risco</div>
        </div>
        <div class="perf-card">
            <div class="big verde">''' + emoji_maior + ' R$ ' + f"{p['maior_lucro']:.2f}" + '''</div>
            <div class="label">🏆 Maior Lucro</div>
            <div class="sub">💀 Pior: R$ ''' + f"{p['maior_prejuizo']:.2f}" + '''</div>
        </div>
        <div class="perf-card">
            <div class="big">''' + str(p['dias_medio']) + '''</div>
            <div class="label">📅 Dias Médio/Operação</div>
            <div class="sub">Tempo médio para atingir o alvo</div>
        </div>
    </div>

    <div class="geral-banner">
        <h2>🌱 AgroSinal em Números</h2>
        <p>
            👥 ''' + str(g['total_usuarios']) + ''' usuários | 📊 ''' + str(g['total_operacoes']) + ''' operações |
            🎯 Taxa de acerto geral: <strong>''' + str(taxa_geral) + '''%</strong> |
            💰 P&L total: <strong>R$ ''' + f"{g['pnl_total']:.2f}" + '''</strong>
        </p>
    </div>

    <div class="card">
        <h3>📊 Performance por Ativo</h3>
        <div class="table-wrap">
            <table>
                <tr><th>Ativo</th><th>Total</th><th>V/D</th><th>Taxa</th><th>Lucro</th></tr>
                ''' + (linhas_ativos if linhas_ativos else '<tr><td colspan="5" style="text-align:center;color:#999;padding:20px;">Nenhuma operação fechada ainda</td></tr>') + '''
            </table>
        </div>
    </div>

    <div class="card">
        <h3>📈 Resultado Mensal</h3>
        <div class="table-wrap">
            <table>
                <tr><th>Mês</th><th>Operações</th><th>Resultado</th></tr>
                ''' + (linhas_mensal if linhas_mensal else '<tr><td colspan="3" style="text-align:center;color:#999;padding:20px;">Nenhum resultado mensal ainda</td></tr>') + '''
            </table>
        </div>
    </div>

    <div class="card">
        <h3>📋 Todas as Minhas Operações</h3>
        <div class="table-wrap">
            <table>
                <tr>
                    <th>#</th><th>Entrada</th><th>Saída</th><th>Direção</th><th>Ativo</th>
                    <th>Qtd</th><th>Preço Ent.</th><th>Preço Sai.</th><th>P&L</th><th>Dias</th><th>Sinal</th>
                </tr>
                ''' + (linhas_ops if linhas_ops else '<tr><td colspan="11" style="text-align:center;color:#999;padding:30px;">Você ainda não fez nenhuma operação.<br>Vá no <strong>histórico de sinais</strong> e clique em "ENTRAR" num sinal!</td></tr>') + '''
            </table>
        </div>
    </div>

    <div style="text-align:center;padding:14px;color:#aaa;font-size:11px;">
        AgroSinal — Minha Performance | ''' + hoje + '''
    </div>
</div>
</body>
</html>''')

    return ''.join(html_parts)
