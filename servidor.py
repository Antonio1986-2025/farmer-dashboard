"""Servidor web FastAPI para o Farmer Dashboard.

Fornece:
- GET  /          → Dashboard HTML
- GET  /api/dados → JSON com dados do dia
- POST /api/coletar → Dispara coleta manual
- POST /api/trade → Registra um trade
- PUT  /api/trade/{id} → Fecha um trade
"""
import asyncio
import json
from pathlib import Path
from datetime import date, datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config import PASTA_PROJETO
from dados import banco
from coletores import precos, cepaea, clima
from analise import regras
from alerta import enviar, formatar
from dashboard import gerar

app = FastAPI(title="Farmer Dashboard", version="1.0")

# ─── Dados em cache (evita coletar a toda requisição) ─────
cache = {"dados_precos": {}, "dados_cepea": {}, "dados_clima": [], "alertas": []}


async def coleta_completa() -> dict:
    """Roda coleta, análise e retorna tudo."""
    banco.criar_tabelas()

    precos_futuros, cepea_dados = await asyncio.gather(
        precos.coletar_todos(),
        cepaea.coletar_cepea(),
    )
    clima_dados = clima.coletar_todas_regioes()

    banco.salvar_precos(
        milho_b3=precos_futuros.get("milho_b3"),
        boi_b3=precos_futuros.get("boi_b3"),
        cbot=precos_futuros.get("cbot"),
        dolar=precos_futuros.get("dolar"),
        milho_cepea=cepea_dados.get("milho_cepea"),
        arroba_cepea=cepea_dados.get("arroba_cepea"),
    )

    for c in clima_dados:
        banco.salvar_clima(c["regiao"], c["temperatura"], c["chuva_mm"], c["umidade"])

    alertas = regras.avaliar_todas(precos_futuros, cepea_dados, clima_dados)
    for a in alertas:
        banco.salvar_sinal(
            tipo=a["tipo"], ativo=a.get("ativo", "ambos"),
            direcao=a.get("direcao", ""), confianca=a.get("confianca", "media"),
            prazo_estimado=a.get("prazo", ""), explicacao=a["explicacao"],
            preco_alvo=a.get("valor"), preco_atual=None,
        )

    # Envia alertas prioritários
    prioritarios = [a for a in alertas if a.get("confianca") == "alta"]
    for a in prioritarios:
        enviar.enviar_alerta(a)

    # Atualiza cache
    cache["dados_precos"] = precos_futuros
    cache["dados_cepea"] = cepea_dados
    cache["dados_clima"] = clima_dados
    cache["alertas"] = alertas

    return {"precos": precos_futuros, "cepea": cepea_dados, "clima": clima_dados, "alertas": alertas}


# ─── Modelos Pydantic ──────────────────────────────────────

class TradeEntrada(BaseModel):
    sinal_id: int | None = None
    ativo: str
    tipo: str
    preco: float

class TradeSaida(BaseModel):
    preco_saida: float
    observacao: str = ""


# ─── Rotas ─────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Página principal com o dashboard."""
    if not cache["alertas"]:
        await coleta_completa()

    html = gerar.gerar_dashboard(
        cache["dados_precos"], cache["dados_cepea"],
        cache["dados_clima"], cache["alertas"],
        output_path=str(PASTA_PROJETO / "dashboard" / "index.html"),
    )
    return html


@app.get("/api/dados")
async def api_dados():
    """Retorna dados do dia em JSON."""
    ultimo = banco.pegar_ultimo_preco()
    clima_hoje = banco.pegar_clima_hoje()
    sinais = banco.pegar_sinais_hoje()
    trades_abertos = banco.pegar_trades_abertos()
    estatisticas = banco.pegar_resumo_trades()

    return {
        "data": str(date.today()),
        "precos": {
            "dolar": ultimo[5] if ultimo else None,
            "cbot": ultimo[4] if ultimo else None,
            "milho_b3": ultimo[2] if ultimo else None,
            "boi_b3": ultimo[3] if ultimo else None,
            "milho_cepea": ultimo[6] if ultimo else None,
            "arroba_cepea": ultimo[7] if ultimo else None,
            "relacao_boi_milho": ultimo[8] if ultimo else None,
        } if ultimo else {},
        "clima": [{"regiao": c[3], "temp": c[4], "chuva": c[5]} for c in clima_hoje],
        "alertas": cache["alertas"],
        "trades_abertos": len(trades_abertos),
        "estatisticas": {
            "total": estatisticas[0] if estatisticas else 0,
            "taxa_acerto": (
                round(estatisticas[1] / estatisticas[0] * 100, 1)
                if estatisticas and estatisticas[0] > 0 else 0
            ),
            "saldo": round(
                (estatisticas[3] or 0) + (estatisticas[4] or 0), 2
            ) if estatisticas else 0,
        } if estatisticas else {},
    }


@app.post("/api/coletar")
async def api_coletar():
    """Dispara coleta manual."""
    try:
        resultado = await coleta_completa()
        return {"status": "ok", "alertas": len(cache["alertas"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trade")
async def api_registrar_trade(trade: TradeEntrada):
    """Registra uma entrada."""
    trade_id = banco.registrar_trade(trade.sinal_id, trade.ativo, trade.tipo, trade.preco)
    return {"status": "ok", "trade_id": trade_id}


@app.put("/api/trade/{trade_id}")
async def api_fechar_trade(trade_id: int, saida: TradeSaida):
    """Fecha um trade."""
    banco.fechar_trade(trade_id, saida.preco_saida, saida.observacao)
    return {"status": "ok", "trade_id": trade_id}


@app.on_event("startup")
async def startup():
    """Roda a primeira coleta ao iniciar."""
    print("🚀 Iniciando primeira coleta...")
    try:
        await coleta_completa()
        print(f"✅ Coleta inicial concluída — {len(cache['alertas'])} alertas")
    except Exception as e:
        print(f"⚠️ Coleta inicial falhou: {e}")
