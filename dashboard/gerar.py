"""Gera o dashboard HTML com gráficos usando Plotly."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
from dados import banco


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
    <table style="width:100%;border-collapse:collapse;">
        <thead>
            <tr style="background:#f8f9fa;">
                <th style="padding:10px;text-align:left;width:40px;">Sinal</th>
                <th style="padding:10px;text-align:left;">Alerta</th>
                <th style="padding:10px;text-align:center;">Confiança</th>
                <th style="padding:10px;text-align:center;">Prazo</th>
            </tr>
        </thead>
        <tbody>{''.join(linhas)}</tbody>
    </table>"""


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


def gerar_resumo_trades() -> str:
    """Gera HTML com resumo dos trades."""
    resumo = banco.pegar_resumo_trades()
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
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
            <tr style="background:#f8f9fa;">
                <th style="padding:8px;text-align:left;">Padrão</th>
                <th style="padding:8px;text-align:left;">Direção</th>
                <th style="padding:8px;text-align:center;">Taxa de Acerto</th>
                <th style="padding:8px;text-align:center;">Acertos/Total</th>
            </tr>
        </thead>
        <tbody>{''.join(linhas)}</tbody>
    </table>"""


def gerar_dashboard(dados_precos: dict, dados_cepea: dict,
                    dados_clima: list, alertas: list,
                    output_path: str = None) -> str:
    """Gera o dashboard HTML completo."""
    hoje = date.today().strftime("%d/%m/%Y")
    registros = banco.pegar_ultimos_precos(60)

    grafico = gerar_grafico_precos(registros)
    tabela_alertas = gerar_tabela_alertas(alertas)
    resumo_clima = gerar_resumo_clima(dados_clima)
    resumo_trades = gerar_resumo_trades()
    tabela_stats = gerar_tabela_estatisticas_sinais()

    # Card de destaque
    dolar = dados_precos.get("dolar", "—")
    cbot = dados_precos.get("cbot", "—")
    cepea_milho = dados_cepea.get("milho_cepea", "—")
    cepea_boi = dados_cepea.get("arroba_cepea", "—")

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
    <title>Farmer Dashboard — {hoje}</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background:#f0f2f5; color:#333; padding:20px; }}
        .container {{ max-width:1200px; margin:0 auto; }}
        .header {{ background: linear-gradient(135deg, #1a472a, #2d6a4f);
                   color:white; padding:25px 30px; border-radius:15px; margin-bottom:20px;
                   display:flex; justify-content:space-between; align-items:center; }}
        .header h1 {{ font-size:28px; }}
        .header span {{ font-size:14px; opacity:0.8; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:15px; margin-bottom:20px; }}
        .card {{ background:white; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
        .card h3 {{ font-size:14px; color:#888; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px; }}
        .card .valor {{ font-size:32px; font-weight:bold; }}
        .card .variacao {{ font-size:14px; margin-top:4px; }}
        .card .resumo {{ font-size:13px; color:#666; margin-top:8px; padding-top:8px; border-top:1px solid #eee; }}
        .card-full {{ grid-column: 1 / -1; }}
        .green {{ color:#2ecc71; }}
        .red {{ color:#e74c3c; }}
        .orange {{ color:#f39c12; }}
        .footer {{ text-align:center; padding:20px; color:#888; font-size:13px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🌾 Farmer Dashboard</h1>
                <span>{hoje} — Coletado automaticamente</span>
            </div>
            <div>{alerta_badge}</div>
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
                <h3>🌽 Milho CEPEA</h3>
                <div class="valor">{'R$ ' + str(cepea_milho) if cepea_milho != '—' else '—'}</div>
                <div class="variacao orange">Físico (R$/saca)</div>
                <div class="resumo">{'Indicador ESALQ/B3' if cepea_milho != '—' else 'Indisponível hoje'}</div>
            </div>
            <div class="card">
                <h3>🐄 Boi CEPEA</h3>
                <div class="valor">{'R$ ' + str(cepea_boi) if cepea_boi != '—' else '—'}</div>
                <div class="variacao green">Físico (R$/@)</div>
                <div class="resumo">{'Indicador ESALQ/B3' if cepea_boi != '—' else 'Indisponível hoje'}</div>
            </div>
        </div>

        <div class="card card-full">
            <h3>📊 Alertas e Sinais do Dia</h3>
            {tabela_alertas}
        </div>

        <div class="card card-full" style="margin-top:15px;">
            <h3>🌤️ Clima — Regiões Relevantes</h3>
            {resumo_clima}
            <div style="margin-top:10px;font-size:12px;color:#888;">
                Regiões monitoradas: Sorriso-MT (milho), Campo Grande-MS (milho+boi), Uberaba-MG, Rio Verde-GO
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

        <div class="footer">
            Farmer Dashboard v1.0 — Dados coletados com Scrapling
        </div>
    </div>
</body>
</html>"""

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html
