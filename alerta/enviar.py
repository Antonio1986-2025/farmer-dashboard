"""Envio de mensagens via OpenWA (WhatsApp API Gateway).

OpenWA: https://github.com/rmyndharis/OpenWA
"""
import requests
from config import OPENWA_API_URL, OPENWA_API_KEY, OPENWA_SESSION, SEU_NUMERO


def _formatar_chatid(numero: str) -> str:
    """Formata o número para o formato aceito pelo OpenWA: 553199999999@c.us"""
    numero = numero.replace("+", "").replace("-", "").replace(" ", "")
    return f"{numero}@c.us"


def enviar_mensagem(texto: str, numero: str = None) -> bool:
    """Envia mensagem via OpenWA.

    Args:
        texto: Mensagem a ser enviada.
        numero: Número no formato 5511999999999 (padrão: config.SEU_NUMERO)

    Returns:
        True se enviou com sucesso, False caso contrário.
    """
    if OPENWA_API_KEY == "":
        print("  ⚠️ WhatsApp: OpenWA não configurado (OPENWA_API_KEY)")
        print(f"  📝 Mensagem que seria enviada:\n{texto}\n")
        return False

    chat_id = _formatar_chatid(numero or SEU_NUMERO)

    url = f"{OPENWA_API_URL}/api/sessions/{OPENWA_SESSION}/messages/send-text"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": OPENWA_API_KEY,
    }
    payload = {
        "chatId": chat_id,
        "text": texto,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        print(f"  ✅ WhatsApp: mensagem enviada com sucesso")
        return True

    except requests.exceptions.ConnectionError:
        print(f"  ❌ WhatsApp: OpenWA não está rodando em {OPENWA_API_URL}")
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
