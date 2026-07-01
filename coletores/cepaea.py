"""Coleta indicadores do CEPEA usando Scrapling (StealthFetcher)."""
import asyncio
from config import URL_CEPEA_MILHO, URL_CEPEA_BOI


async def _coletar_cepea(url: str, nome: str) -> float | None:
    """Tenta extrair o indicador do CEPEA rodando StealthFetcher em thread separada."""
    try:
        from scrapling.fetchers import StealthyFetcher

        def _fetch():
            return StealthyFetcher.fetch(url, headless=True, network_idle=True, solve_cloudflare=True)

        page = await asyncio.to_thread(_fetch)
        texto = page.body.decode()

        import re

        # Tabela: <td>data</td> <td>valor R$</td>
        matches = re.findall(
            r"<td[^>]*>\s*(\d{2}/\d{2}/\d{4})\s*</td>\s*"
            r"<td[^>]*>\s*([\d.,]+)\s*</td>\s*"
            r"<td[^>]*>\s*([-.\d,]+%)",
            texto,
        )
        if matches:
            valor = matches[0][1].replace(".", "").replace(",", ".")
            return float(valor)

        return None

    except Exception as e:
        print(f"  ⚠️ Erro ao acessar CEPEA ({nome}): {e}")
        return None


async def coletar_cepea() -> dict:
    """Coleta indicadores de milho físico e boi gordo do CEPEA."""
    print("  📡 Coletando indicadores CEPEA...")

    milho = await _coletar_cepea(URL_CEPEA_MILHO, "Milho CEPEA")
    if milho:
        print(f"    🌽 Milho CEPEA: R$ {milho:.2f}/saca")
    else:
        print("    🌽 Milho CEPEA: ❌ bloqueado ou indisponível")

    boi = await _coletar_cepea(URL_CEPEA_BOI, "Boi CEPEA")
    if boi:
        print(f"    🐄 Arroba CEPEA: R$ {boi:.2f}/@")
    else:
        print("    🐄 Arroba CEPEA: ❌ bloqueado ou indisponível")

    return {"milho_cepea": milho, "arroba_cepea": boi}
