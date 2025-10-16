"""
Multiple Price Source Integration for Board Games
Fetches prices from various APIs and allows user to select the best option
"""

import requests
from decimal import Decimal
from datetime import datetime, timezone
import time
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PriceSourceService:
    """Service to fetch prices from multiple sources"""
    
    GBP_TO_EUR_RATE = 1.17
    REGION = "IE"
    CURRENCY = "EUR"
    
    @staticmethod
    def fetch_all_prices(bgg_id, game_name):
        """
        Fetch prices from all available sources
        
        Args:
            bgg_id (int): BGG game ID
            game_name (str): Game name for search
            
        Returns:
            list: List of price dictionaries from different sources
        """
        print(f"[PriceSources] Fetching prices for BGG ID: {bgg_id}, Name: {game_name}")
        
        prices = []
        
        # 1. BoardGameOracle
        oracle_price = PriceSourceService._fetch_boardgameoracle(bgg_id)
        if oracle_price:
            prices.append(oracle_price)
        
        # 2. BoardGamePrices.co.uk
        bgp_price = PriceSourceService._fetch_boardgameprices_uk(bgg_id)
        if bgp_price:
            prices.append(bgp_price)
        
        # 3. Zatu Games (UK Store)
        zatu_price = PriceSourceService._fetch_zatu(game_name)
        if zatu_price:
            prices.append(zatu_price)
        
        # 4. Magic Madhouse (UK Store)
        mm_price = PriceSourceService._fetch_magic_madhouse(game_name)
        if mm_price:
            prices.append(mm_price)
        
        # 5. 365Games (UK Store)
        games365_price = PriceSourceService._fetch_365games(game_name)
        if games365_price:
            prices.append(games365_price)
        
        # 6. Philibert (French Store - ships to Ireland)
        philibert_price = PriceSourceService._fetch_philibert(game_name)
        if philibert_price:
            prices.append(philibert_price)
        
        # Sort by price (lowest first)
        prices.sort(key=lambda x: x.get('price_eur', float('inf')))
        
        print(f"[PriceSources] Found {len(prices)} prices total")
        return prices
    
    @staticmethod
    def _fetch_boardgameoracle(bgg_id):
        """Fetch from BoardGameOracle API"""
        try:
            print(f"[BoardGameOracle] Fetching for BGG ID: {bgg_id}")
            
            # BoardGameOracle API endpoint
            url = f"https://www.boardgameoracle.com/api/game/{bgg_id}/prices"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                offers = data.get('offers', [])
                
                # Filter for EU/UK stores that deliver to Ireland
                eu_offers = [o for o in offers if o.get('country') in ['UK', 'DE', 'FR', 'IE', 'NL', 'ES', 'IT']]
                
                if eu_offers:
                    lowest = min(eu_offers, key=lambda x: x.get('price', float('inf')))
                    price_gbp = lowest.get('price')
                    
                    if price_gbp:
                        price_eur = round(price_gbp * PriceSourceService.GBP_TO_EUR_RATE, 2)
                        return {
                            'source': 'BoardGameOracle',
                            'source_url': f"https://www.boardgameoracle.com/game/{bgg_id}",
                            'store_name': lowest.get('store', 'Unknown Store'),
                            'store_url': lowest.get('url', ''),
                            'price_eur': price_eur,
                            'price_original': price_gbp,
                            'currency_original': 'GBP',
                            'stock_status': 'in_stock' if lowest.get('availability') == 'In Stock' else 'unknown',
                            'last_updated': datetime.now(timezone.utc).isoformat(),
                            'shipping_to_ie': True,
                        }
            
            print(f"[BoardGameOracle] No prices found")
            return None
            
        except Exception as e:
            print(f"[BoardGameOracle] Error: {e}")
            return None
    
    @staticmethod
    def _fetch_boardgameprices_uk(bgg_id, *,
                                  sitename="https://bgcatalog.fly.dev",
                                  currency="EUR",
                                  destination=None,                # ex.: "GB", "DE", "US", "DK", "SE" ou None
                                  preferred_language="GB",         # prioriza edição em inglês
                                  timeout=12):
        """
        Busca preços no BoardGamePrices.co.uk usando o BGG ID (eid).
        Retorna o menor preço em stock, priorizando a moeda pedida (EUR) e, na falta, GBP.
        """
        try:
            print(f"[BoardGamePrices] Fetching (api/info) for BGG ID: {bgg_id}")

            # monta query
            params = {
                "eid": str(bgg_id),
                "currency": currency,              # "EUR" recomendado p/ IE/UE
                "sort": "SMART",
                "locale": "en",
                "preferred_language": preferred_language,
                "sitename": sitename
            }
            # destination é opcional; usar apenas valores suportados. Se não souber, deixe None.
            if destination:
                params["destination"] = destination

            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; BGCatalog/1.0; +https://bgcatalog.fly.dev)"
            }

            url = "https://boardgameprices.co.uk/api/info"
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                print(f"[BoardGamePrices] HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json() or {}
            # a API normalmente retorna {"items": [...]} – mas seja resiliente
            items = data.get("items") or data.get("results") or []
            if not isinstance(items, list) or not items:
                print("[BoardGamePrices] Nenhum item retornado pelo endpoint.")
                return None

            # coleta todas as ofertas de todas as edições/itens retornados
            all_offers = []
            for it in items:
                # algumas respostas usam 'prices', outras 'offers'
                prices = it.get("prices") or it.get("offers") or []
                for p in prices:
                    # campos que variam na prática: "price", "price_value", "value"
                    raw_price = (
                        p.get("price_value")
                        or p.get("price")
                        or p.get("value")
                    )
                    # moeda pode vir como "currency" ou "currency_code"
                    curr = p.get("currency") or p.get("currency_code") or data.get("currency") or currency

                    # estoque costuma vir como "stock" (Y/N) ou "in_stock" (bool) ou "availability"
                    stock = p.get("in_stock")
                    if stock is None:
                        s = (p.get("stock") or "").strip().upper()
                        stock = (s == "Y") or ("IN STOCK" in s)
                    if stock is None:
                        stock = "in" in str(p.get("availability", "")).lower()

                    # urls e nomes de loja
                    store_url = p.get("url") or p.get("link") or p.get("shop_url")
                    store_name = (p.get("store") or p.get("shop") or p.get("retailer") or "").strip() or "Unknown store"

                    # sanity checks
                    try:
                        price_float = float(raw_price)
                    except (TypeError, ValueError):
                        continue

                    all_offers.append({
                        "price": price_float,
                        "currency": curr,
                        "stock": bool(stock),
                        "store_name": store_name,
                        "store_url": store_url
                    })

            if not all_offers:
                print("[BoardGamePrices] Nenhuma oferta encontrada nos itens retornados.")
                return None

            # filtra ofertas em stock
            in_stock = [o for o in all_offers if o["stock"]]
            offers_use = in_stock if in_stock else all_offers  # se nada em stock, cai para qualquer

            # prioriza moeda solicitada (EUR). Se não houver, aceita GBP e converte.
            def is_requested_currency(o):
                return (o["currency"] or "").upper() == currency.upper()

            # menor preço na moeda pedida
            offers_requested = [o for o in offers_use if is_requested_currency(o)]
            if offers_requested:
                best = min(offers_requested, key=lambda o: o["price"])
                price_eur = best["price"] if currency.upper() == "EUR" else None
                # conversão se a moeda pedida não for EUR (situação rara no nosso uso)
                if price_eur is None:
                    if currency.upper() == "GBP":
                        # converte para EUR se necessário para preencher 'price_eur'
                        price_eur = round(best["price"] * PriceSourceService.GBP_TO_EUR_RATE, 2)
                    else:
                        # sem conversão conhecida -> retorna price_eur = None de forma honesta
                        price_eur = None

                return {
                    "source": "BoardGamePrices.co.uk",
                    "source_url": url,
                    "store_name": best["store_name"],
                    "store_url": best["store_url"],
                    "price_eur": price_eur,
                    "price_original": best["price"],
                    "currency_original": best["currency"],
                    "stock_status": "in_stock" if best["stock"] else "unknown",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "shipping_to_ie": True
                }

            # caso não exista oferta na moeda pedida, tenta GBP e converte para EUR
            offers_gbp = [o for o in offers_use if (o["currency"] or "").upper() == "GBP"]
            if offers_gbp:
                best = min(offers_gbp, key=lambda o: o["price"])
                price_eur = round(best["price"] * PriceSourceService.GBP_TO_EUR_RATE, 2)

                return {
                    "source": "BoardGamePrices.co.uk",
                    "source_url": url,
                    "store_name": best["store_name"],
                    "store_url": best["store_url"],
                    "price_eur": price_eur,
                    "price_original": best["price"],
                    "currency_original": "GBP",
                    "stock_status": "in_stock" if best["stock"] else "unknown",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "shipping_to_ie": True
                }

            # fallback: pega qualquer moeda (sem conversão)
            best_any = min(offers_use, key=lambda o: o["price"])
            return {
                "source": "BoardGamePrices.co.uk",
                "source_url": url,
                "store_name": best_any["store_name"],
                "store_url": best_any["store_url"],
                "price_eur": None,  # não convertemos por falta de taxa
                "price_original": best_any["price"],
                "currency_original": best_any["currency"],
                "stock_status": "in_stock" if best_any["stock"] else "unknown",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "shipping_to_ie": True
            }

        except Exception as e:
            print(f"[BoardGamePrices] Error: {e}")
            import traceback
            print(f"[BoardGamePrices] Traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def _fetch_zatu(game_name):
        """Fetch from Zatu Games (UK)"""
        try:
            print(f"[Zatu] Searching for: {game_name}")
            
            # Zatu search
            search_url = "https://www.board-game.co.uk/search/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            params = {'q': game_name}
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                import re
                # Simple scraping for price
                prices = re.findall(r'£(\d+\.?\d*)', response.text)
                if prices:
                    price_gbp = float(prices[0])
                    price_eur = round(price_gbp * PriceSourceService.GBP_TO_EUR_RATE, 2)
                    return {
                        'source': 'Zatu Games',
                        'source_url': 'https://www.board-game.co.uk/',
                        'store_name': 'Zatu Games',
                        'store_url': search_url + f"?q={game_name}",
                        'price_eur': price_eur,
                        'price_original': price_gbp,
                        'currency_original': 'GBP',
                        'stock_status': 'unknown',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'shipping_to_ie': True,
                    }
            
            print(f"[Zatu] No prices found")
            return None
            
        except Exception as e:
            print(f"[Zatu] Error: {e}")
            return None
    
    @staticmethod
    def _fetch_magic_madhouse(game_name):
        """Fetch from Magic Madhouse (UK)"""
        try:
            print(f"[MagicMadhouse] Searching for: {game_name}")
            
            search_url = "https://www.magicmadhouse.co.uk/search"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            params = {'q': game_name}
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                import re
                prices = re.findall(r'£(\d+\.?\d*)', response.text)
                if prices:
                    price_gbp = float(prices[0])
                    price_eur = round(price_gbp * PriceSourceService.GBP_TO_EUR_RATE, 2)
                    return {
                        'source': 'Magic Madhouse',
                        'source_url': 'https://www.magicmadhouse.co.uk/',
                        'store_name': 'Magic Madhouse',
                        'store_url': search_url + f"?q={game_name}",
                        'price_eur': price_eur,
                        'price_original': price_gbp,
                        'currency_original': 'GBP',
                        'stock_status': 'unknown',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'shipping_to_ie': True,
                    }
            
            print(f"[MagicMadhouse] No prices found")
            return None
            
        except Exception as e:
            print(f"[MagicMadhouse] Error: {e}")
            return None
    
    @staticmethod
    def _fetch_365games(game_name):
        """Fetch from 365Games (UK)"""
        try:
            print(f"[365Games] Searching for: {game_name}")
            
            search_url = "https://www.365games.co.uk/search"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            params = {'q': game_name}
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                import re
                prices = re.findall(r'£(\d+\.?\d*)', response.text)
                if prices:
                    price_gbp = float(prices[0])
                    price_eur = round(price_gbp * PriceSourceService.GBP_TO_EUR_RATE, 2)
                    return {
                        'source': '365Games',
                        'source_url': 'https://www.365games.co.uk/',
                        'store_name': '365Games',
                        'store_url': search_url + f"?q={game_name}",
                        'price_eur': price_eur,
                        'price_original': price_gbp,
                        'currency_original': 'GBP',
                        'stock_status': 'unknown',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'shipping_to_ie': True,
                    }
            
            print(f"[365Games] No prices found")
            return None
            
        except Exception as e:
            print(f"[365Games] Error: {e}")
            return None
    
    @staticmethod
    def _fetch_philibert(game_name):
        """Fetch from Philibert (France - ships to Ireland)"""
        try:
            print(f"[Philibert] Searching for: {game_name}")
            
            search_url = "https://www.philibertnet.com/en/search"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            params = {'q': game_name}
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                import re
                prices = re.findall(r'€(\d+\.?\d*)', response.text)
                if prices:
                    price_eur = float(prices[0])
                    return {
                        'source': 'Philibert',
                        'source_url': 'https://www.philibertnet.com/',
                        'store_name': 'Philibert',
                        'store_url': search_url + f"?q={game_name}",
                        'price_eur': price_eur,
                        'price_original': price_eur,
                        'currency_original': 'EUR',
                        'stock_status': 'unknown',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'shipping_to_ie': True,
                    }
            
            print(f"[Philibert] No prices found")
            return None
            
        except Exception as e:
            print(f"[Philibert] Error: {e}")
            return None
