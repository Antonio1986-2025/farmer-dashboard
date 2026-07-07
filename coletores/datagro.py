"""Coleta preços do Indicador do Boi DATAGRO — referência oficial da B3.

API: https://precos.api.datagro.com/quadros/
Usa o client_id público do site indicadordoboi.com.br
"""
import requests
from datetime import date

# Client ID público do site indicadordoboi.com.br
DATAGRO_CLIENTE = "a81574eb-06c1-11ed-bcba-02ebefa3b928"
DATAGRO_URL = "https://precos.api.datagro.com/quadros/"

# Códigos dos ativos: Indicador do Boi por estado (B3 + DATAGRO)
ATIVOS_BOI = {
    "SP": "D_PEPR_SP_BR",
    "GO": "D_PEPR_GO_BR",
    "MG": "D_PEPR_MG_BR",
    "MS": "D_PEPR_MS_BR",
    "MT": "D_PEPR_MT_BR",
    "PA": "D_PEPR_PA_BR",
    "RO": "D_PEPR_RO_BR",
    "TO": "D_PEPR_TO_BR",
    "BA": "D_PEPR_BA_BR",
}

# Códigos para outros produtos (vaca, novilha, reposição)
ATIVOS_VACA = {
    "SP": "D_PEPV_SP_BR",
    "GO": "D_PEPV_GO_BR",
    "MG": "D_PEPV_MG_BR",
    "MS": "D_PEPV_MS_BR",
    "MT": "D_PEPV_MT_BR",
    "PA": "D_PEPV_PA_BR",
    "RO": "D_PEPV_RO_BR",
    "TO": "D_PEPV_TO_BR",
    "BA": "D_PEPV_BA_BR",
}

ATIVOS_NOVILHA = {
    "SP": "D_PEPN_SP_BR",
    "GO": "D_PEPN_GO_BR",
    "MG": "D_PEPN_MG_BR",
    "MS": "D_PEPN_MS_BR",
    "MT": "D_PEPN_MT_BR",
    "PA": "D_PEPN_PA_BR",
    "RO": "D_PEPN_RO_BR",
    "TO": "D_PEPN_TO_BR",
    "BA": "D_PEPN_BA_BR",
}


def _montar_url(ativos: dict) -> str:
    """Monta URL da API com os ativos desejados."""
    codigos = ",".join(ativos.values())
    return f"{DATAGRO_URL}?ativos={codigos}&idioma=pt-br&cliente={DATAGRO_CLIENTE}"


def _parse_resposta(resp_json: dict, ativos: dict) -> dict:
    """Converte resposta da API em dict {estado: {dados}}."""
    resultado = {}
    for item in resp_json.get("ativos", []):
        cod = item["cod"]
        dados = item.get("dados", {})
        # Descobre qual estado é esse código
        for estado, cod_ativo in ativos.items():
            if cod == cod_ativo:
                resultado[estado] = {
                    "preco": float(dados.get("ult", 0)),
                    "variacao": float(dados.get("var", 0)) if dados.get("var") else 0,
                    "data": dados.get("dia", str(date.today())),
                    "nome": dados.get("nome", f"Boi {estado}"),
                    "maxima": float(dados["maxi"]) if dados.get("maxi") else None,
                    "minima": float(dados["mini"]) if dados.get("mini") else None,
                }
                break
    return resultado


def coletar_boi() -> dict:
    """Coleta Indicador do Boi DATAGRO para todos os estados.

    Returns:
        dict: {estado: {preco, variacao, data, nome}} ou dict vazio se falhar.
    """
    print("  📡 Coletando Indicador do Boi DATAGRO (referência B3)...")
    try:
        url = _montar_url(ATIVOS_BOI)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dados = _parse_resposta(resp.json(), ATIVOS_BOI)

        if dados:
            # Calcula média nacional (simples)
            precos = [d["preco"] for d in dados.values() if d["preco"]]
            media_nacional = round(sum(precos) / len(precos), 2) if precos else None

            for estado in sorted(dados.keys()):
                d = dados[estado]
                sinal = "🔺" if d["variacao"] > 0 else ("🔻" if d["variacao"] < 0 else "➡️")
                print(f"    {sinal} {estado}: R$ {d['preco']:.2f}/@ ({d['variacao']:+.2f}%)")

            if media_nacional:
                print(f"    📊 Média nacional: R$ {media_nacional:.2f}/@")

            dados["_media_nacional"] = media_nacional
            dados["_data"] = list(dados.values())[0]["data"]
        else:
            print("    ❌ DATAGRO: sem dados disponíveis")

        return dados

    except requests.exceptions.Timeout:
        print("    ⏰ DATAGRO: timeout na requisição")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"    ⚠️ DATAGRO: erro na requisição: {e}")
        return {}
    except Exception as e:
        print(f"    ⚠️ DATAGRO: erro inesperado: {e}")
        return {}


def coletar_vaca() -> dict:
    """Coleta Indicador da Vaca DATAGRO."""
    try:
        url = _montar_url(ATIVOS_VACA)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return _parse_resposta(resp.json(), ATIVOS_VACA)
    except Exception:
        return {}


def coletar_novilha() -> dict:
    """Coleta Indicador da Novilha DATAGRO."""
    try:
        url = _montar_url(ATIVOS_NOVILHA)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return _parse_resposta(resp.json(), ATIVOS_NOVILHA)
    except Exception:
        return {}


def coletar_todos() -> dict:
    """Coleta todos os indicadores DATAGRO (boi, vaca, novilha).

    Returns:
        dict com {boi, vaca, novilha} cada um sendo {estado: {dados}}
    """
    return {
        "boi": coletar_boi(),
        "vaca": coletar_vaca(),
        "novilha": coletar_novilha(),
    }
