"""Sistema de acurácia — acompanha acertos/erros por tipo de sinal.

Gera relatórios de performance que ajudam a calibrar as regras.
"""
from dados import banco
from datetime import date, timedelta


def relatorio_acertos(dias: int = 90) -> dict:
    """Gera relatório de acurácia dos sinais nos últimos N dias."""
    stats = banco.pegar_estatisticas_sinais()
    hoje = date.today()

    total_sinais = 0
    total_acertos = 0
    total_erros = 0
    total_pendentes = 0
    por_tipo = {}

    for row in stats:
        tipo, direcao, total, acertos, erros, pendentes = row
        if tipo not in por_tipo:
            por_tipo[tipo] = {"total": 0, "acertos": 0, "erros": 0, "pendentes": 0, "taxa": 0}
        por_tipo[tipo]["total"] += total
        por_tipo[tipo]["acertos"] += acertos
        por_tipo[tipo]["erros"] += erros
        por_tipo[tipo]["pendentes"] += pendentes
        por_tipo[tipo]["taxa"] = round(acertos / (acertos + erros) * 100, 1) if (acertos + erros) > 0 else 0
        total_sinais += total
        total_acertos += acertos
        total_erros += erros
        total_pendentes += pendentes

    taxa_geral = round(total_acertos / (total_acertos + total_erros) * 100, 1) if (total_acertos + total_erros) > 0 else 0

    # Sinais pendentes (sem desfecho) há mais de 30 dias
    pendentes_velhos = banco.pegar_sinais_pendentes(30)

    return {
        "periodo": f"{dias} dias",
        "total_sinais": total_sinais,
        "total_acertos": total_acertos,
        "total_erros": total_erros,
        "total_pendentes": total_pendentes,
        "taxa_acerto_geral": taxa_geral,
        "por_tipo": por_tipo,
        "pendentes_sem_desfecho": len(pendentes_velhos),
        "data": str(hoje),
    }


def resumo_para_dashboard() -> str:
    """Gera HTML com resumo de acertos para o dashboard."""
    try:
        rel = relatorio_acertos(90)
    except Exception:
        return "<div style='padding:15px;color:#888;'>📊 Estatísticas em construção</div>"

    if rel["total_sinais"] == 0:
        return "<div style='padding:15px;color:#888;'>📊 Nenhum sinal com desfecho ainda</div>"

    html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:15px;">
        <div style="background:#f8f9fa;border-radius:10px;padding:15px;text-align:center;">
            <div style="font-size:12px;color:#888;">Taxa de Acerto Geral</div>
            <div style="font-size:28px;font-weight:bold;">{rel['taxa_acerto_geral']}%</div>
            <div style="font-size:12px;color:#888;">{rel['total_acertos']}A / {rel['total_erros']}E</div>
        </div>
        <div style="background:#f8f9fa;border-radius:10px;padding:15px;text-align:center;">
            <div style="font-size:12px;color:#888;">Total de Sinais</div>
            <div style="font-size:28px;font-weight:bold;">{rel['total_sinais']}</div>
            <div style="font-size:12px;color:#888;">{rel['total_pendentes']} pendentes</div>
        </div>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr style="background:#f0f0f0;">
            <th style="padding:8px;text-align:left;">Tipo</th>
            <th style="padding:8px;text-align:center;">Total</th>
            <th style="padding:8px;text-align:center;">Acertos</th>
            <th style="padding:8px;text-align:center;">Erros</th>
            <th style="padding:8px;text-align:center;">Taxa</th>
        </tr>"""

    for tipo, dados in sorted(rel["por_tipo"].items()):
        cor = "#2ecc71" if dados["taxa"] >= 60 else "#f39c12" if dados["taxa"] >= 40 else "#e74c3c"
        html += f"""
        <tr>
            <td style="padding:6px 8px;">{tipo}</td>
            <td style="padding:6px 8px;text-align:center;">{dados['total']}</td>
            <td style="padding:6px 8px;text-align:center;color:#2ecc71;">{dados['acertos']}</td>
            <td style="padding:6px 8px;text-align:center;color:#e74c3c;">{dados['erros']}</td>
            <td style="padding:6px 8px;text-align:center;font-weight:bold;color:{cor};">{dados['taxa']}%</td>
        </tr>"""

    html += "</table>"
    return html
