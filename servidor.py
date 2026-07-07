"""Servidor web FastAPI do AgroSinal."""
import asyncio
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from config import PASTA_PROJETO, PLANOS
from dados import banco
from coletores import precos, cepaea, fisicos, clima, yahoo as coletor_yahoo
from coletores.datagro import coletar_boi as coletar_datagro_boi
from analise import regras
from autenticacao import hash_senha, verificar_senha, criar_token, pegar_usuario_atual

app = FastAPI(title="AgroSinal", version="1.0")

cache = {"dados_precos": {}, "dados_cepea": {}, "dados_clima": [], "alertas": [], "dados_datagro": {}}
startup_ok = False

# ─── Landing page ───────────────────────────────────────────

LANDING = Path(__file__).parent / "landing.html"
PRICING = Path(__file__).parent / "precos.html"
DASHBOARD_HTML = Path(__file__).parent / "dashboard" / "index.html"


def _ler_html(caminho: Path) -> str:
    if caminho.exists():
        return caminho.read_text(encoding="utf-8")
    return "<h1>Página não encontrada</h1>"


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    token = request.cookies.get("token")
    if token:
        try:
            from autenticacao import _decodificar
            _decodificar(token)
            return RedirectResponse(url="/dashboard")
        except Exception:
            pass
    return _ler_html(LANDING)


@app.get("/precos", response_class=HTMLResponse)
async def precos_page():
    return _ler_html(PRICING)

APRESENTACAO = Path(__file__).parent / "apresentacao.html"

@app.get("/apresentacao", response_class=HTMLResponse)
async def apresentacao_page():
    return _ler_html(APRESENTACAO)


# ─── Coleta de dados ────────────────────────────────────────

async def coleta_completa() -> dict:
    banco.criar_tabelas()

    # ─── 1. DATAGRO (prioritário, rápido e confiável) ─────────────
    datagro_boi = None
    try:
        datagro_boi = await asyncio.wait_for(
            asyncio.to_thread(coletar_datagro_boi), timeout=20
        )
        if datagro_boi:
            banco.salvar_precos_datagro(datagro_boi, "boi")
            print(f"    ✅ DATAGRO: {len(datagro_boi)-2} estados coletados")
    except Exception as e:
        print(f"    ⚠️ DATAGRO: {e}")

    # ─── 2. Demais coletores (com timeout individual) ─────────────
    precos_yahoo = {}
    precos_futuros = {}
    fisicos_dados = {}
    cepea_dados = {}
    clima_dados = []

    # Yahoo + Investing + Físicos (rodam em paralelo com timeout)
    async def _coletar_yahoo():
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(coletor_yahoo.coletar_todos), timeout=25
            )
        except Exception as e:
            print(f"    ⚠️ Yahoo: {e}")
            return {}

    async def _coletar_investing():
        try:
            return await asyncio.wait_for(precos.coletar_todos(), timeout=25)
        except Exception as e:
            print(f"    ⚠️ Investing: {e}")
            return {}

    async def _coletar_fisicos(cbot_brl):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(fisicos.coletar_fisicos, cbot_brl), timeout=20
            )
        except Exception as e:
            print(f"    ⚠️ Físicos: {e}")
            return {}

    async def _coletar_cepea():
        try:
            return await asyncio.wait_for(cepaea.coletar_cepea(), timeout=20)
        except Exception as e:
            print(f"    ⚠️ CEPEA: {e}")
            return {}

    # Yahoo + Investing em paralelo
    yahoo_task = asyncio.create_task(_coletar_yahoo())
    investing_task = asyncio.create_task(_coletar_investing())
    precos_yahoo = await yahoo_task
    precos_futuros = await investing_task

    # Físicos (precisa do CBOT do Yahoo)
    cbot_brl = precos_yahoo.get("cbot_brl")
    fisicos_dados = await _coletar_fisicos(cbot_brl)

    # CEPEA
    cepea_dados = await _coletar_cepea()

    # Clima
    try:
        clima_dados = clima.coletar_todas_regioes()
    except Exception as e:
        print(f"    ⚠️ Clima: {e}")

    # ─── 3. Mescla tudo ──────────────────────────────────────────
    dados_precos = {}
    # Yahoo tem prioridade
    if precos_yahoo:
        dados_precos.update(precos_yahoo)
    # Investing complementa
    if precos_futuros:
        for k in ("milho_b3", "boi_b3", "cbot", "dolar"):
            if k not in dados_precos or not dados_precos.get(k):
                dados_precos[k] = precos_futuros.get(k)
    # Físicos complementam CEPEA
    milho_cepea_val = fisicos_dados.get("milho_cepea") or cepea_dados.get("milho_cepea")
    if milho_cepea_val:
        dados_precos["milho_cepea"] = milho_cepea_val

    # DATAGRO como fonte principal do boi
    media_nacional = datagro_boi.get("_media_nacional") if datagro_boi else None
    arroba_cepea_val = media_nacional or fisicos_dados.get("arroba_cepea") or cepea_dados.get("arroba_cepea")
    if arroba_cepea_val:
        dados_precos["arroba_cepea"] = arroba_cepea_val

    # ─── 4. Salva no banco ───────────────────────────────────────
    banco.salvar_precos(
        milho_b3=dados_precos.get("milho_b3"),
        boi_b3=dados_precos.get("boi_b3"),
        cbot=dados_precos.get("cbot_brl") or dados_precos.get("cbot"),
        dolar=dados_precos.get("dolar"),
        milho_cepea=milho_cepea_val,
        arroba_cepea=arroba_cepea_val,
    )
    for c in clima_dados:
        banco.salvar_clima(c["regiao"], c["temperatura"], c["chuva_mm"], c["umidade"])
    # Análise multi-indicador
    alertas = regras.avaliar_todas(dados_precos, cepea_dados, clima_dados)
    for a in alertas:
        banco.salvar_sinal(
            usuario_id=None, tipo=a["tipo"], ativo=a.get("ativo", "ambos"),
            direcao=a.get("direcao", ""), confianca=a.get("confianca", "media"),
            prazo_estimado=a.get("prazo", ""), explicacao=a["explicacao"],
            preco_alvo=a.get("valor"), preco_atual=None,
        )
    # Envia alertas prioritários para cada usuário com WhatsApp
    from alerta import enviar
    from alerta.formatar import formatar_alerta_whatsapp
    usuarios_wa = banco.pegar_usuarios_com_whatsapp()
    for a in (a for a in alertas if a.get("confianca") == "alta"):
        msg = formatar_alerta_whatsapp(a)
        # Sempre envia pro número fixo (admin)
        enviar.enviar_mensagem(msg)
        # Envia pra cada usuário que tem WhatsApp
        for uid, unome, uwa, uplano in usuarios_wa:
            plano_config = PLANOS.get(uplano, PLANOS["gratis"])
            if plano_config.get("whatsapp") and uwa:
                enviar.enviar_mensagem(msg, uwa)
    cache["dados_precos"] = dados_precos
    cache["dados_cepea"] = cepea_dados
    cache["dados_fisicos"] = fisicos_dados
    cache["dados_clima"] = clima_dados
    cache["alertas"] = alertas
    cache["dados_datagro"] = datagro_boi or {}
    return {"precos": dados_precos, "cepea": cepea_dados, "clima": clima_dados, "alertas": alertas, "datagro": datagro_boi}


# ─── Modelos ─────────────────────────────────────────────────

class TradeEntrada(BaseModel):
    sinal_id: int | None = None
    ativo: str
    tipo: str
    preco: float

class TradeSaida(BaseModel):
    preco_saida: float
    observacao: str = ""

class AuthRegistro(BaseModel):
    email: str
    nome: str
    senha: str

class AuthLogin(BaseModel):
    email: str
    senha: str


# ─── Auth ────────────────────────────────────────────────────

@app.post("/api/auth/registrar")
async def registrar(dados: AuthRegistro, response: Response):
    if banco.pegar_usuario_por_email(dados.email):
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    usuario_id = banco.criar_usuario(dados.email, dados.nome, hash_senha(dados.senha))
    if not usuario_id:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    token = criar_token(usuario_id)
    response.set_cookie(key="token", value=token, max_age=30*24*3600, httponly=True)
    return {"token": token, "usuario": {"id": usuario_id, "email": dados.email, "nome": dados.nome, "plano": "gratis"}}

@app.post("/api/auth/login")
async def login(dados: AuthLogin, response: Response):
    usuario = banco.pegar_usuario_por_email(dados.email)
    if not usuario or not verificar_senha(dados.senha, usuario[3]):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    banco.atualizar_ultimo_login(usuario[0])
    token = criar_token(usuario[0])
    response.set_cookie(key="token", value=token, max_age=30*24*3600, httponly=True)
    return {"token": token, "usuario": {"id": usuario[0], "email": usuario[1], "nome": usuario[2], "plano": usuario[4]}}

@app.get("/api/auth/perfil")
async def perfil(usuario=Depends(pegar_usuario_atual)):
    return {
        "id": usuario[0], "email": usuario[1], "nome": usuario[2],
        "plano": usuario[4], "whatsapp": usuario[6] or "",
        "limites": PLANOS.get(usuario[4], PLANOS["gratis"]),
    }

class SenhaAlterar(BaseModel):
    senha: str

@app.post("/api/auth/alterar-senha")
async def alterar_senha(dados: SenhaAlterar, usuario=Depends(pegar_usuario_atual)):
    if len(dados.senha) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    from autenticacao import hash_senha
    banco.alterar_senha(usuario[0], hash_senha(dados.senha))
    return {"status": "ok"}


# ─── WhatsApp ───────────────────────────────────────────────

@app.get("/api/auth/whatsapp/status")
async def whatsapp_status(usuario=Depends(pegar_usuario_atual)):
    """Retorna status da sessão OpenWA e URL do QR code."""
    from config import OPENWA_API_URL, OPENWA_API_KEY, OPENWA_SESSION
    import requests
    resp = {"conectado": False, "qr_url": None, "painel_url": None, "erro": None}
    if not OPENWA_API_KEY:
        resp["erro"] = "OpenWA não configurado"
        return resp
    try:
        r = requests.get(
            f"{OPENWA_API_URL}/api/sessions",
            headers={"X-API-Key": OPENWA_API_KEY},
            timeout=10,
        )
        if r.status_code == 200:
            sessions = r.json()
            sessao = None
            for s in sessions:
                if s.get("name") == OPENWA_SESSION:
                    sessao = s
                    break
            if sessao:
                st = sessao.get("status", "")
                resp["conectado"] = st in ("connected", "active")
                if st == "qr_ready":
                    resp["qr_url"] = f"{OPENWA_API_URL}/session/{sessao.get('id', OPENWA_SESSION)}"
                    resp["painel_url"] = f"{OPENWA_API_URL}/sessions"
            else:
                resp["erro"] = f"Sessão '{OPENWA_SESSION}' não encontrada"
        else:
            resp["erro"] = f"OpenWA retornou {r.status_code}"
    except requests.ConnectionError:
        resp["erro"] = "OpenWA offline"
    return {**resp, "numero": usuario[6] or ""}


@app.post("/api/auth/whatsapp")
async def whatsapp_salvar(dados: dict, usuario=Depends(pegar_usuario_atual)):
    """Salva o número de WhatsApp do usuário."""
    numero = dados.get("numero", "").strip()
    import re
    numero = re.sub(r"[^\d]", "", numero)
    if len(numero) < 10 or len(numero) > 13:
        raise HTTPException(status_code=400, detail="Número inválido. Use DDD + número (ex: 5511999999999)")
    banco.atualizar_whatsapp(usuario[0], numero)
    return {"status": "ok", "numero": numero}


@app.post("/api/auth/whatsapp/testar")
async def whatsapp_testar(usuario=Depends(pegar_usuario_atual)):
    """Envia mensagem teste para o WhatsApp do usuário."""
    numero = usuario[6]
    if not numero:
        raise HTTPException(status_code=400, detail="Nenhum número cadastrado")
    from alerta.enviar import enviar_mensagem
    from alerta.formatar import formatar_alerta_whatsapp
    alerta_teste = {
        "titulo": "🧪 Teste AgroSinal",
        "confianca": "alta",
        "explicacao": "Se você recebeu esta mensagem, seu WhatsApp está configurado corretamente!",
        "sinal": "📡",
        "valor": None,
        "prazo": "",
        "ativo": "ambos",
        "direcao": "",
    }
    msg = formatar_alerta_whatsapp(alerta_teste)
    ok = enviar_mensagem(msg, numero)
    return {"status": "ok" if ok else "erro"}


# ─── Minha Conta (página de perfil/configurações) ──────────

@app.get("/minha-conta", response_class=HTMLResponse)
async def minha_conta(usuario=Depends(pegar_usuario_atual)):
    caminho = Path(__file__).parent / "perfil.html"
    if caminho.exists():
        return caminho.read_text(encoding="utf-8")
    return "<h1>Página não encontrada</h1>"


# ─── Dashboard protegido ────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(usuario=Depends(pegar_usuario_atual)):
    from dashboard import gerar
    html = gerar.gerar_dashboard(
        cache["dados_precos"], cache["dados_cepea"],
        cache["dados_clima"], cache["alertas"],
        output_path=str(DASHBOARD_HTML),
        usuario_id=usuario[0],
        dados_datagro=cache.get("dados_datagro"),
    )
    # Adiciona link pro histórico no HTML final
    link_hist = '<a href="/dashboard/historico" style="color:white;font-size:12px;text-decoration:none;padding:5px 10px;border-radius:20px;background:rgba(255,255,255,0.12);">📜 Histórico</a>'
    html = html.replace('← Sair</a>', f'← Sair</a>{link_hist}')
    return html


@app.get("/dashboard/historico", response_class=HTMLResponse)
async def historico_sinais(
    pagina: int = 1, tipo: str | None = None, status: str | None = None,
    usuario=Depends(pegar_usuario_atual),
):
    from dashboard import gerar
    sinais_data = api_listar_sinais(limite=50, pagina=pagina, tipo=tipo, status=status, usuario=usuario)
    stats = api_estatisticas_sinais(usuario=usuario)
    html = gerar.gerar_historico_sinais(sinais_data, stats, pagina, tipo, status,
                                         nome=usuario[2], plano=usuario[4])
    return html


# ─── API pública ─────────────────────────────────────────────

@app.get("/api/dados")
async def api_dados():
    ultimo = banco.pegar_ultimo_preco()
    clima_hoje = banco.pegar_clima_hoje()
    cepea = cache["dados_cepea"] or {}
    fisicos = cache.get("dados_fisicos", {})
    datagro_cache = cache.get("dados_datagro", {})
    # Determina fonte: "datagro" se disponível, senão "oficial" (CEPEA), senão "estimado"
    fonte_boi = "datagro" if datagro_cache else ("oficial" if cepea.get("arroba_cepea") else ("estimado" if fisicos.get("arroba_cepea") else "indisponivel"))
    fonte_milho = "oficial" if cepea.get("milho_cepea") else ("estimado" if fisicos.get("milho_cepea") else "indisponivel")
    return {
        "data": str(date.today()),
        "precos": {
            "dolar": ultimo[5] if ultimo else None,
            "cbot": ultimo[4] if ultimo else None,
            "milho_b3": ultimo[2] if ultimo else None,
            "boi_b3": ultimo[3] if ultimo else None,
            "milho_cepea": ultimo[6] if ultimo else None,
            "arroba_cepea": datagro_cache.get("_media_nacional") if datagro_cache else (ultimo[7] if ultimo else None),
            "relacao_boi_milho": ultimo[8] if ultimo else None,
            "fonte_milho": fonte_milho,
            "fonte_boi": fonte_boi,
        } if ultimo else {},
        "clima": [{"regiao": c[2], "temp": c[3], "chuva": c[4], "umidade": c[5]} for c in clima_hoje],
        "alertas": cache["alertas"],
        "datagro": {
            "boi": {k: v for k, v in datagro_cache.items() if k != "_data" and k != "_media_nacional"} if datagro_cache else {},
            "media_nacional": datagro_cache.get("_media_nacional") if datagro_cache else None,
            "data": datagro_cache.get("_data") if datagro_cache else None,
        } if datagro_cache else {},
    }


@app.get("/api/datagro")
async def api_datagro():
    """Retorna dados completos do Indicador do Boi DATAGRO."""
    datagro_cache = cache.get("dados_datagro", {})
    if datagro_cache:
        return {
            "data": datagro_cache.get("_data"),
            "media_nacional": datagro_cache.get("_media_nacional"),
            "estados": {k: v for k, v in datagro_cache.items() if k not in ("_data", "_media_nacional")},
        }
    # Fallback: busca do banco de dados
    precos_hoje = banco.pegar_precos_datagro_hoje("boi")
    if precos_hoje:
        precos_lista = [v["preco"] for v in precos_hoje.values() if v.get("preco")]
        media = round(sum(precos_lista) / len(precos_lista), 2) if precos_lista else None
        return {
            "data": str(date.today()),
            "media_nacional": media,
            "estados": {k: v for k, v in precos_hoje.items()},
        }
    return {"data": None, "media_nacional": None, "estados": {}}

@app.post("/api/coletar")
async def api_coletar():
    """Dispara coleta em background e retorna imediatamente."""
    asyncio.create_task(coleta_completa_async())
    return {"status": "coletando", "mensagem": "Coleta iniciada em segundo plano. Aguarde ~90s."}


async def coleta_completa_async():
    """Wrapper async que roda coleta_completa tratando erros."""
    try:
        await asyncio.wait_for(coleta_completa(), timeout=180)
        print(f"  ✅ Coleta concluída: {len(cache['alertas'])} alertas")
    except asyncio.TimeoutError:
        print("  ⏰ Coleta excedeu tempo limite")
    except Exception as e:
        print(f"  ⚠️ Coleta: {e}")

@app.get("/api/health")
async def health():
    if startup_ok or banco.pegar_ultimo_preco():
        return {"status": "ok"}
    return JSONResponse({"status": "starting"}, status_code=503)


# ─── API protegida (sinais) ─────────────────────────────────

@app.get("/api/sinais")
async def api_listar_sinais(
    limite: int = 30, pagina: int = 1,
    tipo: str | None = None, status: str | None = None,
    usuario=Depends(pegar_usuario_atual),
):
    """Lista sinais com paginação e filtros."""
    offset = (pagina - 1) * limite
    sinais_raw = banco.pegar_sinais(usuario[0], limite, offset, tipo, status)
    total = banco.pegar_sinais_count(usuario[0], tipo, status)
    sinais = []
    for s in sinais_raw:
        sinais.append({
            "id": s[0], "data": s[1], "tipo": s[2], "ativo": s[3],
            "direcao": s[4], "confianca": s[5], "prazo": s[6],
            "explicacao": s[7], "preco_alvo": s[8], "preco_atual": s[9],
            "acertou": s[10], "data_desfecho": s[11], "created_at": s[12],
        })
    return {
        "sinais": sinais, "total": total,
        "pagina": pagina, "total_paginas": max(1, (total + limite - 1) // limite),
    }

@app.post("/api/sinais/{sinal_id}/avaliar")
async def api_avaliar_sinal(sinal_id: int, dados: dict, usuario=Depends(pegar_usuario_atual)):
    """Marca sinal como acertou/errou manualmente."""
    acertou = dados.get("acertou")
    if acertou not in ("sim", "nao"):
        raise HTTPException(status_code=400, detail="Valor inválido. Use 'sim' ou 'nao'")
    with banco.conectar() as conn:
        conn.execute("UPDATE sinais SET acertou = ?, data_desfecho = date('now','localtime') WHERE id = ?",
                     (acertou, sinal_id))
    return {"status": "ok", "sinal_id": sinal_id, "acertou": acertou}

@app.get("/api/sinais/estatisticas")
async def api_estatisticas_sinais(usuario=Depends(pegar_usuario_atual)):
    """Estatísticas gerais e por tipo de sinal."""
    resumo = banco.pegar_resumo_sinais()
    por_tipo = banco.pegar_estatisticas_sinais()
    tipos = []
    for t in por_tipo:
        total_t = t[2] or 0
        acertos_t = t[3] or 0
        taxa = round(acertos_t / total_t * 100, 1) if total_t > 0 else 0
        tipos.append({
            "tipo": t[0], "direcao": t[1],
            "total": total_t, "acertos": acertos_t,
            "erros": t[4] or 0, "pendentes": t[5] or 0,
            "taxa_acerto": taxa,
        })
    total_avaliados = resumo["acertos"] + resumo["erros"]
    resumo["taxa_acerto"] = round(resumo["acertos"] / total_avaliados * 100, 1) if total_avaliados > 0 else 0
    resumo["total_avaliados"] = total_avaliados
    return {"resumo": resumo, "por_tipo": tipos}


# ─── API protegida (trades) ─────────────────────────────────

@app.post("/api/trade")
async def api_registrar_trade(trade: TradeEntrada, usuario=Depends(pegar_usuario_atual)):
    plano = PLANOS.get(usuario[4], PLANOS["gratis"])
    ativos = banco.listar_ativos_usuario(usuario[0])
    if trade.ativo not in ativos:
        if len(ativos) >= plano["max_ativos"]:
            raise HTTPException(status_code=402, detail=f"Limite de {plano['max_ativos']} ativos. Faça upgrade!")
    trade_id = banco.registrar_trade(usuario[0], trade.sinal_id, trade.ativo, trade.tipo, trade.preco)
    return {"status": "ok", "trade_id": trade_id}

@app.put("/api/trade/{trade_id}")
async def api_fechar_trade(trade_id: int, saida: TradeSaida, usuario=Depends(pegar_usuario_atual)):
    banco.fechar_trade(usuario[0], trade_id, saida.preco_saida, saida.observacao)
    return {"status": "ok", "trade_id": trade_id}

@app.get("/api/trades")
async def api_listar_trades(usuario=Depends(pegar_usuario_atual)):
    trades = banco.pegar_trades_abertos(usuario[0])
    return {"trades": trades}


# ─── Startup ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    asyncio.create_task(_background_startup())

async def _background_startup():
    global startup_ok
    banco.criar_tabelas()
    try:
        from dados.historico import carregar_historico_startup
        await asyncio.to_thread(carregar_historico_startup)
    except Exception as e:
        print(f"  ⚠️ Histórico inicial: {e}")
    # Coleta dados na inicialização
    print("  📡 Coletando dados na inicialização...")
    asyncio.create_task(coleta_completa_async())
    startup_ok = True
