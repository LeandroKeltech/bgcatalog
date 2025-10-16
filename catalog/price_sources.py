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
    def _fetch_boardgameprices_uk(bgg_id):
        """Fetch from BoardGamePrices.co.uk"""
        try:
            print(f"[BoardGamePrices] Fetching for BGG ID: {bgg_id}")
            
            # Try scraping the page
            url = f"https://boardgameprices.co.uk/item/{bgg_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                import re
                # Look for prices in EUR or GBP
                eur_prices = re.findall(r'€(\d+\.?\d*)', response.text)
                gbp_prices = re.findall(r'£(\d+\.?\d*)', response.text)
                
                if eur_prices:
                    price_eur = float(eur_prices[0])
                    return {
                        'source': 'BoardGamePrices.co.uk',
                        'source_url': url,
                        'store_name': 'Various (aggregated)',
                        'store_url': url,
                        'price_eur': price_eur,
                        'price_original': price_eur,
                        'currency_original': 'EUR',
                        'stock_status': 'unknown',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'shipping_to_ie': True,
                    }
                elif gbp_prices:
                    price_gbp = float(gbp_prices[0])
                    price_eur = round(price_gbp * PriceSourceService.GBP_TO_EUR_RATE, 2)
                    return {
                        'source': 'BoardGamePrices.co.uk',
                        'source_url': url,
                        'store_name': 'Various (aggregated)',
                        'store_url': url,
                        'price_eur': price_eur,
                        'price_original': price_gbp,
                        'currency_original': 'GBP',
                        'stock_status': 'unknown',
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'shipping_to_ie': True,
                    }
            
            print(f"[BoardGamePrices] No prices found")
            return None
            
        except Exception as e:
            print(f"[BoardGamePrices] Error: {e}")
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
