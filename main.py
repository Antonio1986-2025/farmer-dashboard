#!/usr/bin/env python3
"""Farmer Dashboard — Sistema de monitoramento e alertas para milho e boi.

Modos de uso:
    python main.py              → coleta, analisa, gera dashboard e alerta
    python main.py --entrar     → registra manualmente uma entrada (trade)
    python main.py --sair       → fecha um trade aberto
    python main.py --trades     → mostra trades abertos
    python main.py --dashboard  → só gera o HTML (sem nova coleta)
"""
import sys
import asyncio
import json
from pathlib import Path
from datetime import date

from config import PASTA_PROJETO
from dados import banco
from coletores import precos, cepaea, clima
from coletores.datagro import coletar_boi as coletar_datagro_boi
from analise import regras
from alerta import enviar, formatar
from dashboard import gerar


async def coletar_tudo() -> tuple:
    """Roda todos os coletores em paralelo e retorna os dados."""
    print("🌾 Farmer Dashboard — Coletando dados...\n")

    banco.criar_tabelas()

    # Coletores rodam em paralelo (usando asyncio.gather)
    precos_futuros, cepea_dados = await asyncio.gather(
        precos.coletar_todos(),
        cepaea.coletar_cepea(),
    )
    clima_dados = clima.coletar_todas_regioes()

    # DATAGRO: referência oficial B3 para boi
    datagro_boi = await asyncio.to_thread(coletar_datagro_boi)
    if datagro_boi:
        banco.salvar_precos_datagro(datagro_boi, "boi")

    print("\n📊 Salvando no banco de dados...")
    # Usa DATAGRO como preço principal do boi
    arroba_usar = datagro_boi.get("_media_nacional") if datagro_boi else cepea_dados.get("arroba_cepea")
    banco.salvar_precos(
        milho_b3=precos_futuros.get("milho_b3"),
        boi_b3=precos_futuros.get("boi_b3"),
        cbot=precos_futuros.get("cbot"),
        dolar=precos_futuros.get("dolar"),
        milho_cepea=cepea_dados.get("milho_cepea"),
        arroba_cepea=arroba_usar or cepea_dados.get("arroba_cepea"),
    )

    for c in clima_dados:
        banco.salvar_clima(c["regiao"], c["temperatura"], c["chuva_mm"], c["umidade"])

    return precos_futuros, cepea_dados, clima_dados, datagro_boi


def processar_alertas(dados_precos: dict, dados_cepea: dict, dados_clima: list) -> list:
    """Processa regras de alerta e salva os sinais no banco."""
    print("\n🤖 Analisando indicadores...")
    alertas = regras.avaliar_todas(dados_precos, dados_cepea, dados_clima)

    if alertas:
        print(f"\n⚠️  {len(alertas)} alerta(s) gerado(s):")
        for a in alertas:
            conf = a.get("confianca", "media")
            icone = {"alta": "🔴", "media": "🟡", "baixa": "ℹ️"}.get(conf, "📊")
            print(f"   {icone} [{conf.upper()}] {a['titulo']}")
            print(f"      {a['explicacao'][:100]}...\n")

            # Salva sinal no banco
            banco.salvar_sinal(
                tipo=a["tipo"],
                ativo=a.get("ativo", "ambos"),
                direcao=a.get("direcao", ""),
                confianca=conf,
                prazo_estimado=a.get("prazo", ""),
                explicacao=a["explicacao"],
                preco_alvo=a.get("valor"),
                preco_atual=None,
            )

        # Envia alertas prioritários via WhatsApp
        prioritarios = [a for a in alertas if a.get("confianca") == "alta"]
        if prioritarios:
            print("\n📱 Enviando alertas WhatsApp...")
            for alerta in prioritarios:
                enviar.enviar_alerta(alerta)
    else:
        print("\n✅ Nenhum alerta no momento. Mercado estável.")

    return alertas


def gerar_e_abrir_dashboard(dados_precos: dict, dados_cepea: dict,
                            dados_clima: list, alertas: list,
                            dados_datagro: dict = None):
    """Gera o HTML e abre no navegador."""
    print("\n📄 Gerando dashboard...")
    output_path = PASTA_PROJETO / "dashboard" / "index.html"
    gerar.gerar_dashboard(
        dados_precos, dados_cepea, dados_clima, alertas,
        output_path=str(output_path),
        dados_datagro=dados_datagro,
    )

    import webbrowser
    webbrowser.open(f"file:///{output_path}")
    print(f"   ✅ Dashboard salvo e aberto: {output_path}")


def cmd_entrada():
    """Registra manualmente uma entrada."""
    print("\n📝 Registrar entrada no trade")
    ativo = input("   Ativo (milho/boi): ").strip().lower()
    tipo = input("   Tipo (compra/venda): ").strip().lower()
    preco = float(input("   Preço de entrada (R$): ").strip().replace(",", "."))
    sinal_id = input("   ID do sinal (opcional, Enter pular): ").strip()

    trade_id = banco.registrar_trade(
        sinal_id=int(sinal_id) if sinal_id else None,
        ativo=ativo,
        tipo=tipo,
        preco_entrada=preco,
    )
    print(f"\n✅ Trade #{trade_id} registrado: {tipo.upper()} {ativo.upper()} a R$ {preco:.2f}")


def cmd_saida():
    """Fecha um trade aberto."""
    trades = banco.pegar_trades_abertos()
    if not trades:
        print("\n✅ Nenhum trade aberto.")
        return

    print("\n📋 Trades abertos:")
    for t in trades:
        trade_id, sinal_id, ativo, tipo, preco_entrada, *_ = t
        print(f"   #{trade_id} — {tipo.upper()} {ativo.upper()} — Entrada: R$ {preco_entrada}")

    trade_id = int(input("\n   ID do trade a fechar: "))
    preco_saida = float(input("   Preço de saída (R$): ").strip().replace(",", "."))
    obs = input("   Observação (opcional): ").strip()

    banco.fechar_trade(trade_id, preco_saida, obs)
    print(f"\n✅ Trade #{trade_id} fechado a R$ {preco_saida:.2f}")


def cmd_trades():
    """Mostra trades abertos e resumo."""
    trades = banco.pegar_trades_abertos()
    if trades:
        print("\n📋 TRADES ABERTOS:")
        for t in trades:
            trade_id, sinal_id, ativo, tipo, preco_entrada, *_ = t
            print(f"   #{trade_id} — {tipo.upper()} {ativo.upper()} — R$ {preco_entrada:.2f}")

    resumo = banco.pegar_resumo_trades()
    if resumo and resumo[0]:
        total, vitorias, derrotas, lucro, prejuizo, dias_medio = resumo
        taxa = round(vitorias / total * 100, 1) if total > 0 else 0
        saldo = round((lucro or 0) + (prejuizo or 0), 2)
        print(f"\n📊 RESUMO: {taxa}% acerto ({int(vitorias)}V/{int(derrotas)}D)")
        print(f"   Saldo: R$ {saldo:.2f} | Tempo médio: {round(dias_medio or 0)} dias")


async def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--entrar":
            cmd_entrada()
        elif cmd == "--sair":
            cmd_saida()
        elif cmd == "--trades":
            cmd_trades()
        elif cmd == "--dashboard":
            # Gera dashboard com dados existentes (sem coleta)
            registros = banco.pegar_ultimos_precos(1)
            banco.criar_tabelas()
            dados_precos = {}
            dados_cepea = {}
            dados_clima = banco.pegar_clima_hoje()
            alertas = []
            gerar_e_abrir_dashboard(dados_precos, dados_cepea, dados_clima, alertas)
        else:
            print(f"❌ Comando desconhecido: {cmd}")
            print(__doc__)
        return

    # ─── Fluxo completo ─────────────────────────────────────
    print("╔══════════════════════════════════════╗")
    print("║     🌾 FARMER DASHBOARD v1.0         ║")
    print("╚══════════════════════════════════════╝")

    dados_precos, dados_cepea, dados_clima, dados_datagro = await coletar_tudo()
    alertas = processar_alertas(dados_precos, dados_cepea, dados_clima)
    gerar_e_abrir_dashboard(dados_precos, dados_cepea, dados_clima, alertas, dados_datagro=dados_datagro)

    print("\n✅ Ciclo completo!")


if __name__ == "__main__":
    asyncio.run(main())
