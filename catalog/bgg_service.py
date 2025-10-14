"""
BoardGameGeek (BGG) XML API Integration Service
Documentation: https://boardgamegeek.com/wiki/page/BGG_XML_API2
"""

import requests
import xml.etree.ElementTree as ET
from decimal import Decimal
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
                    detailed_results.append(details)
                # Be nice to BGG API - add small delay between requests
                if i < len(search_results[:limit]) - 1:
                    time.sleep(0.5)
        
        return detailed_results
