"""Coleta preços físicos (milho saca, boi @) do CEPEA com bypass Cloudflare.

Usa Scrapling StealthyFetcher (Playwright headless) para contornar Cloudflare.
Fallback: estimativa via CBOT.
"""
import re

from config import URL_CEPEA_MILHO, URL_CEPEA_BOI


def _extrair_tabela_cepea(url: str) -> float | None:
    """Acessa página CEPEA com StealthyFetcher e extrai o último preço."""
    try:
        from scrapling.fetchers import StealthyFetcher

        p = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            solve_cloudflare=True,
            timeout=30,
        )
        txt = str(p.body, "utf-8", errors="replace")

        # Tabela: <td>data</td> <td>valor R$</td> <td>var./dia</td>
        # Ex: <td>26/06/2026</td>\n<td>63,45</td>\n<td>0,28%</td>
        matches = re.findall(
            r"<td[^>]*>\s*(\d{2}/\d{2}/\d{4})\s*</td>\s*"
            r"<td[^>]*>\s*([\d.,]+)\s*</td>\s*"
            r"<td[^>]*>\s*([-.\d,]+%)",
            txt,
        )
        if not matches:
            return None

        data, valor_str, _ = matches[0]
        valor = float(valor_str.replace(".", "").replace(",", "."))
        return valor
    except Exception as e:
        print(f"    ⚠️ Erro {url.split('/')[-1].split('.')[0]}: {e}")
        return None


def _estimar_via_cbot(cbot_brl: float) -> tuple:
    """Estimativa via CBOT: milho = CBOT -10%, boi = milho × 4."""
    milho = round(cbot_brl * 0.90, 2)
    boi = round(milho * 4.0, 2)
    return milho, boi


def coletar_fisicos(cbot_brl: float = None) -> dict:
    """Coleta preços físicos do CEPEA (com bypass Cloudflare).

    Args:
        cbot_brl: CBOT em R$/saca (fallback se CEPEA falhar)

    Returns:
        dict com milho_cepea e arroba_cepea (ou None)
    """
    print("  📡 Coletando preços físicos (milho/boi)...")

    resultado = {"milho_cepea": None, "arroba_cepea": None}

    # Fonte 1: CEPEA via StealthyFetcher (bate Cloudflare)
    try:
        milho = _extrair_tabela_cepea(URL_CEPEA_MILHO)
        if milho:
            resultado["milho_cepea"] = milho
            print(f"    🌽 Milho CEPEA: R$ {milho:.2f}/saca")

        boi = _extrair_tabela_cepea(URL_CEPEA_BOI)
        if boi:
            resultado["arroba_cepea"] = boi
            print(f"    🐄 Boi CEPEA: R$ {boi:.2f}/@")
    except Exception as e:
        print(f"    ⚠️  Erro StealthyFetcher: {e}")

    # Fonte 2: Estimativa CBOT (fallback)
    if (not resultado["milho_cepea"] or not resultado["arroba_cepea"]) and cbot_brl:
        milho_est, boi_est = _estimar_via_cbot(cbot_brl)
        if not resultado["milho_cepea"]:
            resultado["milho_cepea"] = milho_est
            print(f"    🌽 Milho físico: R$ {milho_est:.2f} (estimado CBOT)")
        if not resultado["arroba_cepea"]:
            resultado["arroba_cepea"] = boi_est
            print(f"    🐄 Boi físico: R$ {boi_est:.2f} (@) (estimado relação 4:1)")

    if not resultado["milho_cepea"] and not resultado["arroba_cepea"]:
        print("    ❌ Preços físicos indisponíveis")

    return resultado
