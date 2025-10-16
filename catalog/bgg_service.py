"""
BoardGameGeek (BGG) XML API Integration Service
Documentation: https://boardgamegeek.com/wiki/page/BGG_XML_API2
"""

import requests
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime, timezone
import time
import urllib3

# Suppress SSL warnings for development (when verify=False is used)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BGGService:
    """Service to interact with BoardGameGeek XML API"""
    
    BASE_URL = "https://boardgamegeek.com/xmlapi2"
    
    # Headers to mimic a real browser
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    @staticmethod
    def search_games(query, exact=False):
        """
        Search for board games by name
        
        Args:
            query (str): Game name to search for
            exact (bool): Whether to search for exact match
            
        Returns:
            list: List of dictionaries with game search results
        """
        try:
            params = {
                'query': query,
                'type': 'boardgame',
            }
            if exact:
                params['exact'] = 1
            
            response = requests.get(
                f"{BGGService.BASE_URL}/search", 
                params=params, 
                headers=BGGService.HEADERS,
                timeout=10,
                verify=True  # Verify SSL certificates
            )
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            results = []
            
            for item in root.findall('item'):
                game_id = item.get('id')
                name_elem = item.find('name')
                year_elem = item.find('yearpublished')
                
                results.append({
                    'id': int(game_id) if game_id else None,
                    'name': name_elem.get('value') if name_elem is not None else 'Unknown',
                    'year': int(year_elem.get('value')) if year_elem is not None and year_elem.get('value') else None,
                })
            
            return results
        
        except requests.exceptions.SSLError as e:
            print(f"SSL Error connecting to BGG: {e}")
            print("Retrying without SSL verification (development only)...")
            try:
                # Retry without SSL verification (DEVELOPMENT ONLY)
                response = requests.get(
                    f"{BGGService.BASE_URL}/search", 
                    params=params, 
                    headers=BGGService.HEADERS,
                    timeout=10,
                    verify=False  # Skip SSL verification
                )
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                results = []
                
                for item in root.findall('item'):
                    game_id = item.get('id')
                    name_elem = item.find('name')
                    year_elem = item.find('yearpublished')
                    
                    results.append({
                        'id': int(game_id) if game_id else None,
                        'name': name_elem.get('value') if name_elem is not None else 'Unknown',
                        'year': int(year_elem.get('value')) if year_elem is not None and year_elem.get('value') else None,
                    })
                
                return results
            except Exception as retry_error:
                print(f"Retry also failed: {retry_error}")
                return []
        except requests.RequestException as e:
            print(f"Error searching BGG: {e}")
            return []
        except ET.ParseError as e:
            print(f"Error parsing BGG response: {e}")
            return []
    
    @staticmethod
    def get_game_details(game_id):
        """
        Get detailed information about a specific board game
        
        Args:
            game_id (int): BGG game ID
            
        Returns:
            dict: Dictionary with detailed game information
        """
        try:
            params = {
                'id': game_id,
                'stats': 1,  # Include statistics
            }
            
            response = requests.get(
                f"{BGGService.BASE_URL}/thing", 
                params=params, 
                headers=BGGService.HEADERS,
                timeout=10,
                verify=True
            )
            response.raise_for_status()
            
            # BGG API sometimes needs a retry
            root = ET.fromstring(response.content)
            
            # Check if we got a valid response
            if root.find('item') is None:
                time.sleep(1)  # Wait and retry
                response = requests.get(
                    f"{BGGService.BASE_URL}/thing", 
                    params=params, 
                    headers=BGGService.HEADERS,
                    timeout=10,
                    verify=True
                )
                root = ET.fromstring(response.content)
            
            item = root.find('item')
            if item is None:
                return None
            
            # Extract basic information
            game_data = {
                'bgg_id': int(game_id),
                'name': None,
                'description': None,
                'year_published': None,
                'min_players': None,
                'max_players': None,
                'min_playtime': None,
                'max_playtime': None,
                'min_age': None,
                'designer': [],
                'artist': [],
                'publisher': [],
                'categories': [],
                'mechanics': [],
                'images': [],
                'thumbnail_url': None,
                'msrp_price': None,
                'rating': None,
                'weight': None,
            }
            
            # Primary name
            primary_name = item.find("name[@type='primary']")
            if primary_name is not None:
                game_data['name'] = primary_name.get('value')
            
            # Description
            description = item.find('description')
            if description is not None and description.text:
                game_data['description'] = description.text.strip()
            
            # Year published
            year = item.find('yearpublished')
            if year is not None and year.get('value'):
                try:
                    game_data['year_published'] = int(year.get('value'))
                except (ValueError, TypeError):
                    pass
            
            # Player count
            min_players = item.find('minplayers')
            max_players = item.find('maxplayers')
            if min_players is not None and min_players.get('value'):
                try:
                    game_data['min_players'] = int(min_players.get('value'))
                except (ValueError, TypeError):
                    pass
            if max_players is not None and max_players.get('value'):
                try:
                    game_data['max_players'] = int(max_players.get('value'))
                except (ValueError, TypeError):
                    pass
            
            # Playtime
            min_playtime = item.find('minplaytime')
            max_playtime = item.find('maxplaytime')
            if min_playtime is not None and min_playtime.get('value'):
                try:
                    game_data['min_playtime'] = int(min_playtime.get('value'))
                except (ValueError, TypeError):
                    pass
            if max_playtime is not None and max_playtime.get('value'):
                try:
                    game_data['max_playtime'] = int(max_playtime.get('value'))
                except (ValueError, TypeError):
                    pass
            
            # Min age
            min_age = item.find('minage')
            if min_age is not None and min_age.get('value'):
                try:
                    game_data['min_age'] = int(min_age.get('value'))
                except (ValueError, TypeError):
                    pass
            
            # Designers
            for link in item.findall("link[@type='boardgamedesigner']"):
                designer_name = link.get('value')
                if designer_name:
                    game_data['designer'].append(designer_name)
            
            # Artists
            for link in item.findall("link[@type='boardgameartist']"):
                artist_name = link.get('value')
                if artist_name:
                    game_data['artist'].append(artist_name)
            
            # Publishers
            for link in item.findall("link[@type='boardgamepublisher']"):
                publisher_name = link.get('value')
                if publisher_name:
                    game_data['publisher'].append(publisher_name)
            
            # Categories
            for link in item.findall("link[@type='boardgamecategory']"):
                category_name = link.get('value')
                if category_name:
                    game_data['categories'].append(category_name)
            
            # Mechanics
            for link in item.findall("link[@type='boardgamemechanic']"):
                mechanic_name = link.get('value')
                if mechanic_name:
                    game_data['mechanics'].append(mechanic_name)
            
            # Images
            image = item.find('image')
            thumbnail = item.find('thumbnail')
            
            if image is not None and image.text:
                game_data['images'].append(image.text.strip())
            if thumbnail is not None and thumbnail.text:
                game_data['thumbnail_url'] = thumbnail.text.strip()
                if thumbnail.text.strip() not in game_data['images']:
                    game_data['images'].append(thumbnail.text.strip())
            
            # Statistics (rating, weight, etc.)
            statistics = item.find('statistics')
            if statistics is not None:
                ratings = statistics.find('ratings')
                if ratings is not None:
                    # Average rating
                    average = ratings.find('average')
                    if average is not None and average.get('value'):
                        try:
                            game_data['rating'] = float(average.get('value'))
                        except (ValueError, TypeError):
                            pass
                    
                    # Weight (complexity)
                    averageweight = ratings.find('averageweight')
                    if averageweight is not None and averageweight.get('value'):
                        try:
                            game_data['weight'] = float(averageweight.get('value'))
                        except (ValueError, TypeError):
                            pass
            
            # Format designers as comma-separated string
            if game_data['designer']:
                game_data['designer'] = ', '.join(game_data['designer'])
            else:
                game_data['designer'] = ''
            
            # Note: BGG API doesn't provide MSRP prices directly
            # You may need to estimate or set manually
            game_data['msrp_price'] = None  # Will need to be set manually
            
            return game_data
        
        except requests.exceptions.SSLError as e:
            print(f"SSL Error fetching game details from BGG: {e}")
            print("Retrying without SSL verification (development only)...")
            try:
                # Retry without SSL verification (DEVELOPMENT ONLY)
                response = requests.get(
                    f"{BGGService.BASE_URL}/thing", 
                    params=params, 
                    headers=BGGService.HEADERS,
                    timeout=10,
                    verify=False
                )
                response.raise_for_status()
                root = ET.fromstring(response.content)
                item = root.find('item')
                if item is None:
                    return None
                # Continue with normal parsing...
                # (This would need the full parsing code duplicated, or refactored into a separate method)
                print("Retry succeeded, but full parsing not implemented in retry. Please check your SSL certificates.")
                return None
            except Exception as retry_error:
                print(f"Retry also failed: {retry_error}")
                return None
        except requests.RequestException as e:
            print(f"Error fetching game details from BGG: {e}")
            return None
        except ET.ParseError as e:
            print(f"Error parsing BGG game details: {e}")
            return None
    
    @staticmethod
    def search_and_get_details(query, limit=10):
        """
        Search for games and return detailed information for each result
        
        Args:
            query (str): Game name to search for
            limit (int): Maximum number of results to return
            
        Returns:
            list: List of dictionaries with detailed game information
        """
        search_results = BGGService.search_games(query)
        detailed_results = []
        
        for i, result in enumerate(search_results[:limit]):
            if result['id']:
                details = BGGService.get_game_details(result['id'])
                if details:
                    # Try to fetch price from BoardGamePrices
                    price_data = BGGService.fetch_boardgameprices(result['id'])
                    if price_data and price_data.get('base_price_eur'):
                        details['msrp_price'] = price_data['base_price_eur']
                        details['price_info'] = price_data
                    detailed_results.append(details)
                # Be nice to BGG API - add small delay between requests
                if i < len(search_results[:limit]) - 1:
                    time.sleep(0.5)
        
        return detailed_results
    
    @staticmethod
    def fetch_boardgameprices(bgg_id, region="IE", currency="EUR", gbp_to_eur_rate=1.17):
        """
        Fetch price data from BoardGamePrices for a specific game
        
        Args:
            bgg_id (int): BGG game ID
            region (str): Destination region (default: IE for Ireland)
            currency (str): Preferred currency (default: EUR)
            gbp_to_eur_rate (float): Conversion rate from GBP to EUR
            
        Returns:
            dict: Price information including base price, store details, etc.
        """
        try:
            # Try multiple BoardGamePrices endpoints
            endpoints = [
                f"https://www.boardgameprices.co.uk/api/item/{bgg_id}",
                f"https://boardgameprices.co.uk/item/{bgg_id}/prices.json",
                f"https://www.boardgameprices.com/api/item/{bgg_id}",
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/html',
            }
            
            data = None
            for url in endpoints:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            break
                        except:
                            continue
                except:
                    continue
            
            if not data:
                # Fallback: try scraping the page
                try:
                    url = f"https://www.boardgameprices.co.uk/item/{bgg_id}"
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        # Basic price extraction from HTML (simplified)
                        import re
                        prices = re.findall(r'€(\d+\.?\d*)', response.text)
                        if prices:
                            base_price_eur = float(prices[0])
                            return {
                                "base_price_eur": base_price_eur,
                                "store_name": "BoardGamePrices.co.uk",
                                "store_url": url,
                                "stock_status": "unknown",
                                "price_status": "ok",
                                "price_currency_source": "scraped",
                                "region": region,
                                "currency": currency,
                                "capture_time_utc": datetime.now(timezone.utc).isoformat(),
                            }
                except:
                    pass
                
                print(f"No prices found for BGG ID {bgg_id}")
                return None
            
            # Extract prices from JSON response
            prices = data.get('prices', [])
            if not prices:
                print(f"No prices found for BGG ID {bgg_id}")
                return None
            
            # Filter for target region and currency
            eu_prices = []
            gbp_prices = []
            
            for price_item in prices:
                item_currency = price_item.get('currency', '').upper()
                item_country = price_item.get('country', '').upper()
                price_value = price_item.get('price')
                
                if price_value is None:
                    continue
                
                # Check if delivers to Ireland/EU
                if item_currency == 'EUR':
                    eu_prices.append(price_item)
                elif item_currency == 'GBP' and item_country in ['UK', 'GB']:
                    gbp_prices.append(price_item)
            
            # Find lowest EUR price
            base_price_eur = None
            store_name = None
            store_url = None
            stock_status = "unknown"
            price_currency_source = "native"
            
            if eu_prices:
                lowest_eu = min(eu_prices, key=lambda x: x.get('price', float('inf')))
                base_price_eur = lowest_eu.get('price')
                store_name = lowest_eu.get('shop_name')
                store_url = lowest_eu.get('url')
                stock_status = "in_stock" if lowest_eu.get('in_stock') else "out_of_stock"
            
            # Fallback to GBP with conversion
            elif gbp_prices:
                lowest_gbp = min(gbp_prices, key=lambda x: x.get('price', float('inf')))
                gbp_price = lowest_gbp.get('price')
                if gbp_price:
                    base_price_eur = round(gbp_price * gbp_to_eur_rate, 2)
                    store_name = lowest_gbp.get('shop_name')
                    store_url = lowest_gbp.get('url')
                    stock_status = "in_stock" if lowest_gbp.get('in_stock') else "out_of_stock"
                    price_currency_source = "conversion"
            
            if base_price_eur:
                return {
                    "base_price_eur": base_price_eur,
                    "store_name": store_name,
                    "store_url": store_url,
                    "stock_status": stock_status,
                    "price_status": "ok",
                    "price_currency_source": price_currency_source,
                    "region": region,
                    "currency": currency,
                    "capture_time_utc": datetime.now(timezone.utc).isoformat(),
                }
            
            return None
            
        except requests.RequestException as e:
            print(f"Error fetching prices from BoardGamePrices: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in fetch_boardgameprices: {e}")
            return None
