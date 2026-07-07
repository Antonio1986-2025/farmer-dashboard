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
        <div style="background:#f8f9fa;border-radius:10px;padding:15px;flex:1;min-width:150px;">
            <div style="font-size:14px;color:#666;">{regiao}</div>
            <div style="font-size:24px;font-weight:bold;">{emoji_temp} {temp}°C</div>
            <div style="font-size:13px;color:#888;">💧 {chuva}mm | 🌫️ {umid}%</div>
        </div>""")

    return f'<div style="display:flex;gap:10px;flex-wrap:wrap;">{"".join(cards)}</div>'


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
    badge_oficial = '<span style="background:#2e86de;color:white;font-size:10px;padding:2px 8px;border-radius:8px;margin-left:6px;">CEPEA</span>'
    badge_estimado = '<span style="background:#f39c12;color:white;font-size:10px;padding:2px 8px;border-radius:8px;margin-left:6px;">ESTIMADO</span>'
    badge_datagro = '<span style="background:#27ae60;color:white;font-size:10px;padding:2px 8px;border-radius:8px;margin-left:6px;">DATAGRO ✓ B3</span>'

    alerta_count = len(alertas)
    alerta_count_prioritario = len([a for a in alertas if a.get("confianca") == "alta"])

    if alerta_count_prioritario > 0:
        alerta_badge = f'<span style="background:#e74c3c;color:white;padding:3px 12px;border-radius:12px;font-size:14px;">🔴 {alerta_count_prioritario} prioritário(s)</span>'
    else:
        alerta_badge = '<span style="background:#2ecc71;color:white;padding:3px 12px;border-radius:12px;font-size:14px;">✅ Sem alertas críticos</span>'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgroSinal — {hoje}</title>
    <meta name="theme-color" content="#1a472a">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background:#f0f2f5; color:#333; }}
        .container {{ max-width:1200px; margin:0 auto; padding:12px; }}
        .header {{ background: linear-gradient(135deg, #1a472a, #2d6a4f);
                   color:white; padding:16px 20px; border-radius:12px; margin-bottom:12px;
                   display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:8px; }}
        .header h1 {{ font-size:20px; }}
        .header span {{ font-size:12px; opacity:0.8; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px; margin-bottom:12px; }}
        .card {{ background:white; border-radius:10px; padding:14px; box-shadow:0 1px 4px rgba(0,0,0,0.06); }}
        .card h3 {{ font-size:12px; color:#888; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px; }}
        .card .valor {{ font-size:24px; font-weight:bold; }}
        .card .variacao {{ font-size:12px; margin-top:3px; }}
        .card .resumo {{ font-size:12px; color:#666; margin-top:6px; padding-top:6px; border-top:1px solid #eee; }}
        .card-full {{ grid-column: 1 / -1; }}
        .green {{ color:#2ecc71; }} .red {{ color:#e74c3c; }} .orange {{ color:#f39c12; }}
        .footer {{ text-align:center; padding:16px; color:#888; font-size:12px; }}
        table {{ width:100%; border-collapse:collapse; font-size:13px; }}
        th, td {{ padding:8px 6px; text-align:left; border-bottom:1px solid #eee; }}
        th {{ background:#f5f5f5; font-weight:600; }}
        .table-wrap {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
        @media(min-width:768px) {{
            body {{ padding:20px; }}
            .container {{ padding:0; }}
            .header {{ padding:25px 30px; }}
            .header h1 {{ font-size:28px; }}
            .card {{ padding:20px; }}
            .card .valor {{ font-size:32px; }}
            .grid {{ grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:15px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🌱 AgroSinal</h1>
                <span>{hoje}</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
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

        <div class="card card-full">
            <h3>📊 Alertas e Sinais do Dia</h3>
            {tabela_alertas}
        </div>

        <div class="card card-full" style="margin-top:15px;">
            <h3>📊 Comparativo Histórico (10 anos)</h3>
            <div style="display:flex;gap:10px;flex-wrap:wrap;">
                {card_cbot}
                {card_dolar}
            </div>
            <div style="margin-top:8px;font-size:11px;color:#888;">
                O gráfico abaixo mostra onde o preço atual se posiciona na faixa dos últimos 10 anos. Ponto ● = preço atual.
            </div>
        </div>

        <div class="card card-full" style="margin-top:15px;">
            <h3>🌤️ Clima — Regiões Relevantes</h3>
            {resumo_clima}
            <div style="margin-top:10px;font-size:12px;color:#888;">
                Regiões monitoradas: Sorriso-MT (milho), Campo Grande-MS (milho+boi), Uberaba-MG, Rio Verde-GO
            </div>
        </div>

        <div class="card card-full" style="margin-top:15px;">
            <h3>🐄 Indicador do Boi DATAGRO — Preços por Estado</h3>
            {tabela_datagro}
            <div style="margin-top:10px;font-size:12px;color:#888;">
                O <strong>Indicador do Boi DATAGRO</strong> é a referência oficial da B3 para liquidação dos contratos futuros de pecuária. Aprovado pela CVM.
            </div>
        </div>

        <div class="card card-full" style="margin-top:15px;">
            <h3>📈 Evolução dos Preços</h3>
            {grafico}
        </div>

        <div class="card card-full" style="margin-top:15px;">
            <h3>📋 Minha Carteira</h3>
            {resumo_trades}
        </div>

        <div class="card card-full" style="margin-top:15px;">
            <h3>🎯 Taxa de Acerto por Padrão</h3>
            {tabela_stats}
        </div>

        <div class="card card-full" style="margin-top:15px;">
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
