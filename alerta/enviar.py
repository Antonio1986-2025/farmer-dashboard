"""Envio de mensagens via Evolution API (WhatsApp).

Evolution API é uma API brasileira open-source baseada no Baileys.
Documentação: https://github.com/evolution-api/evolution-api
"""
import requests
import json
from config import EVO_API_URL, EVO_API_KEY, EVO_INSTANCE, SEU_NUMERO


def _formatar_numero(numero: str) -> str:
    """Garante que o número está no formato correto (553199999999)."""
    return numero.replace("+", "").replace("-", "").replace(" ", "")


def enviar_mensagem(texto: str, numero: str = None) -> bool:
    """Envia mensagem via Evolution API.

    Args:
        texto: Mensagem a ser enviada.
        numero: Número no formato 5511999999999 (padrão: config.SEU_NUMERO)

    Returns:
        True se enviou com sucesso, False caso contrário.
    """
    if EVO_API_URL == "http://localhost:8080" and EVO_API_KEY == "":
        print("  ⚠️ WhatsApp: Evolution API não configurada (config.py)")
        print(f"  📝 Mensagem que seria enviada:\n{texto}\n")
        return False

    numero = _formatar_numero(numero or SEU_NUMERO)

    url = f"{EVO_API_URL}/message/sendText/{EVO_INSTANCE}"
    headers = {
        "Content-Type": "application/json",
        "apikey": EVO_API_KEY,
    }
    payload = {
        "number": numero,
        "text": texto,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        print(f"  ✅ WhatsApp: mensagem enviada com sucesso")
        return True

    except requests.exceptions.ConnectionError:
        print(f"  ❌ WhatsApp: Evolution API não está rodando em {EVO_API_URL}")
        print(f"  📝 Mensagem que seria enviada:\n{texto}\n")
        return False
    except Exception as e:
        print(f"  ❌ WhatsApp: erro ao enviar ({e})")
        print(f"  📝 Mensagem que seria enviada:\n{texto}\n")
        return False


def enviar_alerta(alerta: dict) -> bool:
    """Formata e envia um alerta via WhatsApp."""
    from alerta.formatar import formatar_alerta_whatsapp
    msg = formatar_alerta_whatsapp(alerta)
    return enviar_mensagem(msg)
