"""Dashboard da Forca Compradora — metodo de leitura do Emerson.
Mostra contratos em aberto vs preco, posicionamento por participante,
e indicador de sustencao do movimento."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
from dados import banco


def gerar_grafico_forca(registros: list) -> str:
    """Grafico 2 linhas: contratos em aberto vs preco de fechamento."""
    if not registros:
        return "<div style='padding:20px;color:#888;'>⏳ Nenhum dado de forca compradora ainda.</div>"

    datas = []
    contratos = []
    precos = []
    direcoes = []
    sustencoes = []

    for r in registros:
        if len(r) < 16:
            continue
        datas.append(r[1])
        contratos.append(r[4])  # diferenca_contratos
        precos.append(r[6])     # preco_fechamento
        direcoes.append(r[14])  # direcao
        sustencoes.append(r[15])# sustencao

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("📊 Contratos em Aberto (diferença compra-venda)",
                        "🌽 Preço do Milho (R$/saca)"),
        vertical_spacing=0.15,
        shared_xaxes=True,
        row_heights=[0.4, 0.6],
    )

    # Cores para direcao
    cores_contrato = []
    for d in direcoes:
        if d == 'alta':
            cores_contrato.append('#2ecc71')
        elif d == 'baixa':
            cores_contrato.append('#e74c3c')
        else:
            cores_contrato.append('#f39c12')

    fig.add_trace(go.Bar(
        x=datas, y=contratos,
        marker_color=cores_contrato,
        name="Diferença (Compra - Venda)",
        hovertemplate="%{x}<br>Diferença: %{y:+,} contratos<br>%{text}",
        text=[f'Direcao: {d}' for d in direcoes],
    ), row=1, col=1)

    # Linha de zero
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

    if precos:
        fig.add_trace(go.Scatter(
            x=datas, y=precos,
            mode="lines+markers",
            name="Preço Fechamento",
            line=dict(color="#2980b9", width=2),
            marker=dict(size=8),
            hovertemplate="%{x}<br>Preço: R$ %{y:.2f}<br>%{text}",
            text=[f'Sustencao: {s}' for s in sustencoes],
        ), row=2, col=1)

    fig.update_layout(
        height=500,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    fig.update_yaxes(title_text="Contratos", row=1, col=1)
    fig.update_yaxes(title_text="R$/saca", row=2, col=1)

    return fig.to_html(full_html=False, include_plotlyjs=False)


def gerar_grafico_posicionamento(registros: list) -> str:
    """Grafico de barras: posicionamento por participante."""
    if not registros:
        return ""

    participantes = []
    compra = []
    venda = []
    liquido = []

    CATEGORIAS = {
        'PF': 'Pessoa Física (Produtor)',
        'PJ_FIN': 'PJ Financeira (Bancos/Fundos)',
        'PJ_NAO_FIN': 'PJ Não-Financeira (Indústria)',
        'INST': 'Institucional',
        'NAO_RES': 'Não-Residente (Gringo)',
    }

    for r in registros:
        part = r[2]
        participantes.append(CATEGORIAS.get(part, part))
        compra.append(r[3])
        venda.append(r[4])
        liquido.append(r[5])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=participantes, y=compra,
        name="Comprados",
        marker_color="#2ecc71",
        hovertemplate="%{x}<br>Comprados: %{y:+,} contratos",
    ))

    fig.add_trace(go.Bar(
        x=participantes, y=venda,
        name="Vendidos",
        marker_color="#e74c3c",
        hovertemplate="%{x}<br>Vendidos: %{y:+,} contratos",
    ))

    fig.add_trace(go.Scatter(
        x=participantes, y=liquido,
        name="Líquido",
        mode="lines+markers",
        line=dict(color="#f39c12", width=3),
        marker=dict(size=10, symbol="diamond"),
        hovertemplate="%{x}<br>Líquido: %{y:+,} contratos",
    ))

    fig.update_layout(
        barmode="group",
        height=350,
        template="plotly_white",
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=40, r=40, t=40, b=60),
    )
    fig.update_yaxes(title_text="Contratos")

    return fig.to_html(full_html=False, include_plotlyjs=False)


def gerar_resumo_forca(ultimo: tuple) -> str:
    """Cards com resumo do ultimo dia."""
    if not ultimo or len(ultimo) < 15:
        return ""

    data = ultimo[1]
    contratos_compra = ultimo[2]
    contratos_venda = ultimo[3]
    total = ultimo[4]
    diferenca = ultimo[5]
    preco_fech = ultimo[6]
    direcao = ultimo[14]
    sustencao = ultimo[15]

    if direcao == 'alta':
        dir_emoji = '🟢'
        dir_text = "VIÉS DE ALTA"
        dir_color = "#2ecc71"
    elif direcao == 'baixa':
        dir_emoji = '🔴'
        dir_text = "VIÉS DE BAIXA"
        dir_color = "#e74c3c"
    else:
        dir_emoji = '🟡'
        dir_text = "LATERAL"
        dir_color = "#f39c12"

    if sustencao == 'forte':
        sus_emoji = '💪'
        sus_text = "Com sustento"
        sus_color = "#27ae60"
    elif sustencao == 'fraca':
        sus_emoji = '🪶'
        sus_text = "Sem sustento"
        sus_color = "#e67e22"
    else:
        sus_emoji = '⚖️'
        sus_text = "Neutro"
        sus_color = "#95a5a6"

    return f'''
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;">
        <div style="background:{dir_color};border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:28px;margin-bottom:4px;">{dir_emoji}</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.8);">DIREÇÃO</div>
            <div style="font-size:18px;font-weight:700;color:#fff;">{dir_text}</div>
        </div>
        <div style="background:#2c3e50;border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:12px;color:#95a5a6;">CONTRATOS EM ABERTO</div>
            <div style="font-size:22px;font-weight:700;color:#ecf0f1;">{total:,}</div>
            <div style="font-size:11px;color:#95a5a6;">Compra {contratos_compra:,} • Venda {contratos_venda:,}</div>
        </div>
        <div style="background:#2c3e50;border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:12px;color:#95a5a6;">DIFERENÇA</div>
            <div style="font-size:22px;font-weight:700;color:{'#2ecc71' if diferenca > 0 else '#e74c3c'};">{diferenca:+,}</div>
            <div style="font-size:11px;color:#95a5a6;">contratos líquidos</div>
        </div>
        <div style="background:{'#27ae60' if preco_fech and preco_fech > 0 else '#2c3e50'};border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:12px;color:rgba(255,255,255,0.7);">PREÇO</div>
            <div style="font-size:22px;font-weight:700;color:#fff;">R$ {preco_fech:.2f}</div>
            <div style="font-size:11px;color:rgba(255,255,255,0.7);">Fechamento</div>
        </div>
        <div style="background:{sus_color};border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:24px;margin-bottom:4px;">{sus_emoji}</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.8);">SUSTENTAÇÃO</div>
            <div style="font-size:16px;font-weight:700;color:#fff;">{sus_text}</div>
        </div>
        <div style="background:#2c3e50;border-radius:10px;padding:16px;text-align:center;">
            <div style="font-size:12px;color:#95a5a6;">DATA</div>
            <div style="font-size:18px;font-weight:600;color:#ecf0f1;">{data}</div>
            <div style="font-size:11px;color:#95a5a6;">Última atualização</div>
        </div>
    </div>
    '''


def gerar_tabela_posicionamento(registros: list) -> str:
    """Tabela de posicionamento com cores e alertas."""
    if not registros:
        return ""

    linhas = []
    EDGE = 'PF'  # Pessoa fisica = produtor = edge

    for r in registros:
        part = r[2]
        nome = {
            'PF': 'Pessoa Física 🧑‍🌾',
            'PJ_FIN': 'PJ Financeira 🏦',
            'PJ_NAO_FIN': 'PJ Não-Financeira 🏭',
            'INST': 'Institucional 🏛️',
            'NAO_RES': 'Não-Residente 🌎',
        }.get(part, part)

        compra = r[3]
        venda = r[4]
        liq = r[5]
        var_comp = r[6]
        var_vend = r[7]

        # Produtor Edge: se PF está comprada = alerta
        if part == EDGE and compra > venda:
            alerta = '🚨 <span style="color:#e74c3c;font-weight:700;">PRODUTOR COMPRADO</span><br><span style="font-size:10px;color:#888;">Especulando — sinal contrário</span>'
        elif part == EDGE:
            alerta = '✅ Hedging normal'
        elif compra > venda and abs(liq) > 1000:
            alerta = '💪 Força compradora'
        elif venda > compra and abs(liq) > 1000:
            alerta = '⬇️ Força vendedora'
        else:
            alerta = '⚖️ Equilibrado'

        liq_color = '#2ecc71' if liq > 0 else ('#e74c3c' if liq < 0 else '#95a5a6')

        linhas.append(f'''<tr>
            <td style="padding:8px;border-bottom:1px solid #333;font-weight:600;">{nome}</td>
            <td style="padding:8px;border-bottom:1px solid #333;text-align:right;color:#2ecc71;">{compra:,}</td>
            <td style="padding:8px;border-bottom:1px solid #333;text-align:right;color:#e74c3c;">{venda:,}</td>
            <td style="padding:8px;border-bottom:1px solid #333;text-align:right;color:{liq_color};font-weight:700;">{liq:+,}</td>
            <td style="padding:8px;border-bottom:1px solid #333;font-size:11px;">{alerta}</td>
        </tr>''')

    return f'''<table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr style="background:#1a1a2e;">
            <th style="padding:10px;text-align:left;color:#f39c12;">Participante</th>
            <th style="padding:10px;text-align:right;color:#f39c12;">Compra</th>
            <th style="padding:10px;text-align:right;color:#f39c12;">Venda</th>
            <th style="padding:10px;text-align:right;color:#f39c12;">Líquido</th>
            <th style="padding:10px;text-align:left;color:#f39c12;">Análise</th>
        </tr>
        {''.join(linhas)}
    </table>'''


def gerar_dashboard_forca() -> str:
    """Gera o dashboard completo da Forca Compradora."""
    registros = banco.pegar_forca_compradora(dias=30)
    posicionamento = banco.pegar_posicionamento()
    ultimo = banco.pegar_ultima_forca()

    grafico_forca = gerar_grafico_forca(registros)
    resumo = gerar_resumo_forca(ultimo)
    grafico_posic = gerar_grafico_posicionamento(posicionamento)
    tabela_posic = gerar_tabela_posicionamento(posicionamento)

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgroSinal — Força Compradora</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',sans-serif; background:#0d0d1a; color:#e0e0e0; padding:20px; }}
h1 {{ font-size:22px; color:#f39c12; margin-bottom:20px; }}
h2 {{ font-size:16px; color:#ecf0f1; margin:24px 0 12px; border-left:3px solid #f39c12; padding-left:10px; }}
.grafico {{ background:#1a1a2e; border-radius:10px; padding:15px; margin-bottom:20px; }}
.tabela {{ background:#1a1a2e; border-radius:10px; padding:15px; margin-bottom:20px; overflow-x:auto; }}
.legenda {{ font-size:12px; color:#888; margin-bottom:20px; text-align:center; }}
</style>
</head>
<body>
<h1>📊 Força Compradora</h1>
<p style="color:#888;margin-bottom:20px;">
    Método de leitura baseado na análise de Emerson — <strong>rastro do dinheiro vs preço</strong>.
    Movimento com sustento = contratos aumentam na mesma direção do preço.
</p>

{resumo}

<div class="grafico">
<h2>Contratos em Aberto vs Preço</h2>
{grafico_forca}
</div>

<div class="tabela">
<h2>Posicionamento por Participante (COT)</h2>
<p style="color:#888;font-size:12px;margin-bottom:10px;">
    Dados do relatório semanal — categorias de participantes com suas posições compradas/vendidas.
</p>
{tabela_posic}
</div>

<div class="grafico">
<h2>Queda de Braço por Participante</h2>
{grafico_posic}
</div>

<div class="legenda">
    🟢 Mais compra que venda = viés de alta &nbsp;|&nbsp; 🔴 Mais venda que compra = viés de baixa<br>
    💪 Contratos aumentando + preço na direção = movimento com sustento<br>
    🪶 Contratos diminuindo = movimento sem sustentação<br>
    🚨 Produtor (PF) comprado = sinal contrário (edge)
</div>

<p style="text-align:center;color:#555;font-size:11px;margin-top:20px;">
    AgroSinal — Análise de Força Compradora | Dados de posicionamento: relatório semanal da corretora
</p>
</body>
</html>'''
