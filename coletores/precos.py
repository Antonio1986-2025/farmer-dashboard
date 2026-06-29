"""Coleta preços do Investing.com usando Scrapling."""
from scrapling.fetchers import AsyncFetcher
import re
from config import URL_DOLAR, URL_CBOT

async def _extrair_preco(url: str, nome: str) -> float | None:
    """Tenta extrair o preço atual de uma página do Investing.com."""
    try:
        fetcher = AsyncFetcher()
        page = await fetcher.get(url, stealthy_headers=True)
        html = page.body

        # Investing.com coloca o preço em elementos específicos.
        # Padrão comum: um span com a classe contendo "last" ou "text-2xl"
        # ou um atributo data-test="instrument-price-last"
        padroes = [
            r'data-test="instrument-price-last">\s*([\d.,]+)',
            r'class="[^"]*text-2xl[^"]*"[^>]*>([\d.,]+)',
            r'class="[^"]*last_[^"]*"[^>]*>([\d.,]+)',
            r'class="[^"]*price[^"]*"[^>]*>([\d.,]+)',
            r'<span[^>]*>([\d.,]+)</span>\s*</div>\s*</div>\s*<div[^>]*dayRange',
        ]

        for padrao in padroes:
            match = re.search(padrao, html)
            if match:
                valor = match.group(1).replace(",", "")
                return float(valor)

        return None

    except Exception as e:
        print(f"  ⚠️ Erro ao coletar {nome}: {e}")
        return None


async def coletar_todos() -> dict:
    """Coleta todos os preços do Investing.com."""
    print("  📡 Coletando preços do Investing.com...")

    dolar = await _extrair_preco(URL_DOLAR, "Dólar")
    print(f"    💵 Dólar: {'R$ ' + str(dolar) if dolar else '❌ indisponível'}")

    cbot = await _extrair_preco(URL_CBOT, "CBOT Milho")
    print(f"    🌽 CBOT: {'US$ ' + str(cbot) if cbot else '❌ indisponível'}")

    return {
        "dolar": dolar,
        "cbot": cbot,
        "milho_b3": None,
        "boi_b3": None,
    }
