"""
BGG Price Service - Integration with BoardGameGeek, Board Game Atlas, and BoardGamePrices.

This module provides functions to search for board games and fetch detailed information
using multiple data sources with a fallback strategy:
1. BGG XML API2 (primary)
2. Board Game Atlas API (fallback #1)
3. BGG Web Scraping (fallback #2)
4. BoardGamePrices API (pricing data)
"""

import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# API Constants
BGG_API_BASE = "https://boardgamegeek.com/xmlapi2"
BGG_SEARCH_URL = f"{BGG_API_BASE}/search"
BGG_THING_URL = f"{BGG_API_BASE}/thing"
BGG_WEB_BASE = "https://boardgamegeek.com"
BGA_API_BASE = "https://api.boardgameatlas.com/api"
BGA_CLIENT_ID = "JMc8dOwiQE"  # Public test key
BOARDGAMEPRICES_API = "https://www.boardgameprices.co.uk/plugin/info"

# Exchange rate GBP to EUR
GBP_TO_EUR = 1.17

# HTTP headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def search_bgg_games(query: str, exact: bool = False) -> List[Dict]:
    """
    Search for board games using multi-tier fallback strategy.
    
    Args:
        query: Search query (game name or barcode)
        exact: If True, search for exact match
        
    Returns:
        List of games with bgg_id, name, year, thumbnail
    """
    logger.info(f"Searching for games: '{query}' (exact={exact})")
    
    # Try BGG XML API first
    games = _search_bgg_xml_api(query, exact)
    if games:
        logger.info(f"BGG XML API returned {len(games)} results")
        return games
    
    # Fallback to Board Game Atlas
    logger.warning("BGG XML API failed, trying Board Game Atlas")
    games = _search_bga_api(query)
    if games:
        logger.info(f"Board Game Atlas returned {len(games)} results")
        return games
    
    # Fallback to web scraping
    logger.warning("Board Game Atlas failed, trying web scraping")
    games = _search_bgg_web_scraping(query)
    if games:
        logger.info(f"Web scraping returned {len(games)} results")
        return games
    
    logger.error(f"All search methods failed for query: {query}")
    return []


def _search_bgg_xml_api(query: str, exact: bool = False) -> List[Dict]:
    """Search BGG XML API2 with retry strategies."""
    headers_variants = [
        {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
        {'User-Agent': 'BGCatalog/1.0'},
        {},
    ]
    
    for attempt, headers in enumerate(headers_variants, 1):
        try:
            params = {'query': query, 'type': 'boardgame'}
            if exact:
                params['exact'] = '1'
            
            logger.debug(f"BGG XML API attempt {attempt} with headers: {headers}")
            response = requests.get(BGG_SEARCH_URL, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return _parse_bgg_search_results(response.text)
            else:
                logger.warning(f"BGG XML API attempt {attempt} failed: {response.status_code}")
        except Exception as e:
            logger.error(f"BGG XML API attempt {attempt} error: {str(e)}")
    
    return []


def _parse_bgg_search_results(xml_text: str) -> List[Dict]:
    """Parse BGG XML search results."""
    try:
        root = ET.fromstring(xml_text)
        games = []
        
        for item in root.findall('.//item'):
            game_id = item.get('id')
            name_elem = item.find('.//name[@type="primary"]')
            year_elem = item.find('yearpublished')
            
            if name_elem is not None and game_id:
                game = {
                    'bgg_id': game_id,
                    'name': name_elem.get('value', ''),
                    'year': int(year_elem.get('value', 0)) if year_elem is not None else None,
                    'thumbnail': '',  # Will be fetched in detail view
                }
                games.append(game)
        
        return games
    except Exception as e:
        logger.error(f"Error parsing BGG XML: {str(e)}")
        return []


def _search_bga_api(query: str) -> List[Dict]:
    """Search Board Game Atlas API."""
    try:
        params = {
            'name': query,
            'fuzzy_match': 'true',
            'client_id': BGA_CLIENT_ID,
            'limit': 10,
        }
        
        response = requests.get(f"{BGA_API_BASE}/search", params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            games = []
            
            for game in data.get('games', []):
                games.append({
                    'bgg_id': f"bga_{game['id']}",  # Prefix to indicate BGA source
                    'name': game.get('name', ''),
                    'year': game.get('year_published'),
                    'thumbnail': game.get('thumb_url', ''),
                })
            
            return games
        else:
            logger.error(f"BGA API error: {response.status_code}")
    except Exception as e:
        logger.error(f"BGA API exception: {str(e)}")
    
    return []


def _search_bgg_web_scraping(query: str) -> List[Dict]:
    """Scrape BGG website for search results."""
    import warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    
    try:
        search_url = f"{BGG_WEB_BASE}/geeksearch.php"
        params = {'action': 'search', 'objecttype': 'boardgame', 'q': query}
        
        response = requests.get(search_url, params=params, headers=HEADERS, timeout=15, verify=False)
        
        if response.status_code != 200:
            logger.error(f"BGG web scraping failed: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        games = []
        
        # Find game links in search results
        for row in soup.select('tr[id^="row_"]'):
            try:
                link = row.select_one('a.primary')
                if not link:
                    continue
                
                href = link.get('href', '')
                match = re.search(r'/boardgame/(\d+)/', href)
                if not match:
                    continue
                
                game_id = match.group(1)
                name = link.get_text(strip=True)
                
                # Try to extract year
                year_elem = row.select_one('.collection_year')
                year = None
                if year_elem:
                    year_text = year_elem.get_text(strip=True)
                    year_match = re.search(r'\d{4}', year_text)
                    if year_match:
                        year = int(year_match.group())
                
                if name:
                    games.append({
                        'bgg_id': game_id,
                        'name': name,
                        'year': year,
                        'thumbnail': '',
                    })
            except Exception as e:
                logger.warning(f"Error parsing search result row: {str(e)}")
                continue
        
        return games
    except Exception as e:
        logger.error(f"BGG web scraping exception: {str(e)}")
        return []


def get_bgg_game_details(bgg_id: str) -> Dict:
    """
    Get detailed game information.
    
    Args:
        bgg_id: BGG ID or BGA ID (prefixed with 'bga_')
        
    Returns:
        Dictionary with complete game data
    """
    logger.info(f"Fetching game details for: {bgg_id}")
    
    # Check if this is a BGA ID
    if bgg_id.startswith('bga_'):
        bga_id = bgg_id[4:]  # Remove 'bga_' prefix
        return get_bga_game_details(bga_id)
    
    # Try BGG XML API first
    try:
        logger.info(f"Trying BGG XML API for {bgg_id}")
        game_data = _get_bgg_xml_details(bgg_id)
        if game_data and game_data.get('name'):
            logger.info(f"BGG XML API SUCCESS: {game_data.get('name')}")
            return game_data
        logger.warning(f"BGG XML API returned empty or no name for {bgg_id}")
    except Exception as e:
        logger.error(f"BGG XML API exception: {e}")
    
    # Fallback to web scraping
    try:
        logger.warning(f"BGG XML API failed, trying web scraping for {bgg_id}")
        game_data = scrape_bgg_game_page(bgg_id)
        if game_data and game_data.get('name'):
            logger.info(f"Web scraping SUCCESS: {game_data.get('name')}")
            return game_data
        logger.error(f"Web scraping returned empty or no name for {bgg_id}")
    except Exception as e:
        logger.error(f"Web scraping exception: {e}")
    
    logger.error(f"All methods failed to fetch details for BGG ID: {bgg_id}")
    return {}


def fetch_bgg_thumbnail(bgg_id: str) -> str:
    """Fetch thumbnail by scraping BGG game page since Thing API returns 401.

    Returns an empty string if not available or on error. Forces HTTPS for security.
    """
    import warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    
    try:
        url = f"https://boardgamegeek.com/boardgame/{bgg_id}"
        logger.info(f"Fetching thumbnail for BGG {bgg_id} from {url}")
        response = requests.get(url, headers=HEADERS, timeout=8, verify=False)
        logger.info(f"BGG page response: {response.status_code}")
        if response.status_code != 200:
            return ''
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try meta og:image first (most reliable)
        meta_img = soup.select_one('meta[property="og:image"]')
        if meta_img and meta_img.get('content'):
            img_url = meta_img.get('content').strip()
            if img_url.startswith('http://'):
                img_url = 'https://' + img_url[7:]
            logger.info(f"Found thumbnail via og:image: {img_url}")
            return img_url
        
        # Fallback to game header image
        header_img = soup.select_one('img.game-header-image, img[alt*="game"]')
        if header_img and header_img.get('src'):
            img_url = header_img.get('src').strip()
            if img_url.startswith('http://'):
                img_url = 'https://' + img_url[7:]
            logger.info(f"Found thumbnail via header img: {img_url}")
            return img_url
        
        logger.warning(f"No thumbnail found for BGG {bgg_id}")
        return ''
    except Exception as e:
        try:
            logger.error(f"Scraping thumbnail failed for {bgg_id}: {e}")
        except:
            pass
        return ''


def _get_bgg_xml_details(bgg_id: str) -> Dict:
    """Fetch game details from BGG XML API."""
    try:
        params = {'id': bgg_id, 'stats': '1'}
        response = requests.get(BGG_THING_URL, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"BGG XML details failed: {response.status_code}")
            return {}
        
        return _parse_bgg_thing_xml(response.text)
    except Exception as e:
        logger.error(f"BGG XML details exception: {str(e)}")
        return {}


def _parse_bgg_thing_xml(xml_text: str) -> Dict:
    """Parse BGG thing API XML response."""
    try:
        root = ET.fromstring(xml_text)
        item = root.find('.//item[@type="boardgame"]')
        
        if item is None:
            return {}
        
        # Extract basic info
        name_elem = item.find('.//name[@type="primary"]')
        year_elem = item.find('yearpublished')
        image_elem = item.find('image')
        thumbnail_elem = item.find('thumbnail')
        description_elem = item.find('description')
        
        # Extract gameplay info
        minplayers_elem = item.find('minplayers')
        maxplayers_elem = item.find('maxplayers')
        playingtime_elem = item.find('playingtime')
        minplaytime_elem = item.find('minplaytime')
        maxplaytime_elem = item.find('maxplaytime')
        minage_elem = item.find('minage')
        
        # Extract designer
        designers = []
        for link in item.findall('.//link[@type="boardgamedesigner"]'):
            designers.append(link.get('value', ''))
        
        # Extract categories
        categories = []
        for link in item.findall('.//link[@type="boardgamecategory"]'):
            categories.append(link.get('value', ''))
        
        # Extract mechanics
        mechanics = []
        for link in item.findall('.//link[@type="boardgamemechanic"]'):
            mechanics.append(link.get('value', ''))
        
        # Extract ratings
        ratings = item.find('.//statistics/ratings')
        rating_avg = None
        rating_bayes = None
        rank = None
        num_ratings = None
        
        if ratings is not None:
            avg_elem = ratings.find('average')
            bayes_elem = ratings.find('bayesaverage')
            num_elem = ratings.find('usersrated')
            rank_elem = ratings.find('.//rank[@type="subtype"]')
            
            if avg_elem is not None:
                rating_avg = float(avg_elem.get('value', 0))
            if bayes_elem is not None:
                rating_bayes = float(bayes_elem.get('value', 0))
            if num_elem is not None:
                num_ratings = int(num_elem.get('value', 0))
            if rank_elem is not None:
                rank_value = rank_elem.get('value', 'Not Ranked')
                if rank_value.isdigit():
                    rank = int(rank_value)
        
        game_data = {
            'name': name_elem.get('value', '') if name_elem is not None else '',
            'year_published': int(year_elem.get('value', 0)) if year_elem is not None else None,
            'image_url': image_elem.text if image_elem is not None else '',
            'thumbnail_url': thumbnail_elem.text if thumbnail_elem is not None else '',
            'description': description_elem.text if description_elem is not None else '',
            'designer': ', '.join(designers[:3]),  # Limit to first 3
            'min_players': int(minplayers_elem.get('value', 0)) if minplayers_elem is not None else None,
            'max_players': int(maxplayers_elem.get('value', 0)) if maxplayers_elem is not None else None,
            'min_playtime': int(minplaytime_elem.get('value', 0)) if minplaytime_elem is not None else None,
            'max_playtime': int(maxplaytime_elem.get('value', 0)) if maxplaytime_elem is not None else None,
            'min_age': int(minage_elem.get('value', 0)) if minage_elem is not None else None,
            'categories': ', '.join(categories[:5]),  # Limit to first 5
            'mechanics': ', '.join(mechanics[:5]),
            'rating_average': rating_avg,
            'rating_bayes': rating_bayes,
            'rank_overall': rank,
            'num_ratings': num_ratings,
        }
        
        return game_data
    except Exception as e:
        logger.error(f"Error parsing BGG thing XML: {str(e)}")
        return {}


def get_bga_game_details(bga_id: str) -> Dict:
    """Fetch game details from Board Game Atlas API and enrich with BGG scraping."""
    try:
        params = {
            'ids': bga_id,
            'client_id': BGA_CLIENT_ID,
        }
        
        response = requests.get(f"{BGA_API_BASE}/search", params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"BGA details API error: {response.status_code}")
            return {}
        
        data = response.json()
        games = data.get('games', [])
        
        if not games:
            logger.error(f"No game found for BGA ID: {bga_id}")
            return {}
        
        game = games[0]
        
        # Map BGA data to our format
        game_data = {
            'name': game.get('name', ''),
            'year_published': game.get('year_published'),
            'image_url': game.get('image_url', ''),
            'thumbnail_url': game.get('thumb_url', ''),
            'description': game.get('description_preview', ''),
            'min_players': game.get('min_players'),
            'max_players': game.get('max_players'),
            'min_playtime': game.get('min_playtime'),
            'max_playtime': game.get('max_playtime'),
            'min_age': game.get('min_age'),
            'rating_average': game.get('average_user_rating'),
            'num_ratings': game.get('num_user_ratings'),
        }
        
        # Extract categories and mechanics
        categories = [cat['id'] for cat in game.get('categories', [])]
        mechanics = [mech['id'] for mech in game.get('mechanics', [])]
        game_data['categories'] = ', '.join(categories[:5])
        game_data['mechanics'] = ', '.join(mechanics[:5])
        
        # Try to get designer from BGA
        designers = game.get('designers', [])
        if designers:
            game_data['designer'] = ', '.join(designers[:3])
        
        # Enrich with BGG data if available
        # BGA sometimes includes BGG ID in external_links
        logger.info("Attempting to enrich BGA data with BGG scraping")
        bgg_id = None
        for link in game.get('official_url', '').split():
            if 'boardgamegeek.com/boardgame/' in link:
                match = re.search(r'/boardgame/(\d+)/', link)
                if match:
                    bgg_id = match.group(1)
                    break
        
        # If we found a BGG ID, enrich the data
        if bgg_id:
            logger.info(f"Found BGG ID {bgg_id} from BGA data, enriching...")
            bgg_data = scrape_bgg_game_page(bgg_id)
            if bgg_data:
                # Merge BGG data (BGG takes priority for missing fields)
                for key, value in bgg_data.items():
                    if not game_data.get(key) and value:
                        game_data[key] = value
        
        return game_data
    except Exception as e:
        logger.error(f"BGA details exception: {str(e)}")
        return {}


def scrape_bgg_game_page(bgg_id: str) -> Dict:
    """
    Comprehensive web scraping of BGG game page.
    
    Args:
        bgg_id: BoardGameGeek game ID
        
    Returns:
        Dictionary with extracted game data
    """
    import warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    
    try:
        url = f"{BGG_WEB_BASE}/boardgame/{bgg_id}"
        logger.info(f"Scraping BGG page: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        
        if response.status_code != 200:
            logger.error(f"BGG page scraping failed: {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        game_data = {}
        
        # Extract game name - try multiple selectors
        name_elem = soup.select_one('h1.game-header-title-info a, h1 a[href*="/boardgame/"], meta[property="og:title"]')
        if name_elem:
            if name_elem.name == 'meta':
                game_data['name'] = name_elem.get('content', '').strip()
            else:
                game_data['name'] = name_elem.get_text(strip=True)
        
        # If still no name, try from page title
        if not game_data.get('name'):
            title_elem = soup.find('title')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                # Extract game name from title like "CATAN | Board Game | BoardGameGeek"
                if '|' in title_text:
                    game_data['name'] = title_text.split('|')[0].strip()
                else:
                    game_data['name'] = title_text.strip()
        
        logger.info(f"Extracted name: {game_data.get('name', 'NO NAME FOUND')}")
        
        # Extract year from meta or text
        year_elem = soup.select_one('meta[property="og:description"]')
        if year_elem:
            desc = year_elem.get('content', '')
            year_match = re.search(r'\((\d{4})\)', desc)
            if year_match:
                game_data['year_published'] = int(year_match.group(1))
                logger.info(f"Extracted year from meta: {game_data['year_published']}")
        
        if not game_data.get('year_published'):
            year_match = re.search(r'\((\d{4})\)', soup.get_text())
            if year_match:
                game_data['year_published'] = int(year_match.group(1))
                logger.info(f"Extracted year from text: {game_data['year_published']}")
        
        # Extract image from meta tags (most reliable)
        image_elem = soup.select_one('meta[property="og:image"]')
        if image_elem:
            game_data['image_url'] = image_elem.get('content', '')
            game_data['thumbnail_url'] = game_data['image_url']
            logger.info(f"Extracted image from og:image")
        else:
            # Fallback to img tag
            image_elem = soup.select_one('img.game-header-image, img[alt*="game"]')
            if image_elem:
                game_data['image_url'] = image_elem.get('src', '')
                game_data['thumbnail_url'] = game_data['image_url']
                logger.info(f"Extracted image from img tag")
        
        # Extract description from meta or div
        desc_elem = soup.select_one('meta[property="og:description"]')
        if desc_elem:
            game_data['description'] = desc_elem.get('content', '')[:1000]
            logger.info(f"Extracted description from meta ({len(game_data['description'])} chars)")
        else:
            desc_elem = soup.select_one('div.game-description-body, div[class*="description"], p[class*="description"]')
            if desc_elem:
                game_data['description'] = desc_elem.get_text(strip=True)[:1000]
                logger.info(f"Extracted description from div ({len(game_data['description'])} chars)")
        
        # Extract gameplay info using regex from page text
        text = soup.get_text()
        
        # Players - try multiple patterns
        players_match = re.search(r'(\d+)[-–—](\d+)\s+(?:Players?|player)', text, re.IGNORECASE)
        if players_match:
            game_data['min_players'] = int(players_match.group(1))
            game_data['max_players'] = int(players_match.group(2))
            logger.info(f"Extracted players: {game_data['min_players']}-{game_data['max_players']}")
        else:
            single_player_match = re.search(r'(\d+)\s+(?:Players?|player)', text, re.IGNORECASE)
            if single_player_match:
                game_data['min_players'] = int(single_player_match.group(1))
                game_data['max_players'] = int(single_player_match.group(1))
                logger.info(f"Extracted single player count: {game_data['min_players']}")
        
        # Playtime - try multiple patterns
        time_match = re.search(r'(\d+)[-–—](\d+)\s+(?:Min|Minutes?)', text, re.IGNORECASE)
        if time_match:
            game_data['min_playtime'] = int(time_match.group(1))
            game_data['max_playtime'] = int(time_match.group(2))
            logger.info(f"Extracted playtime: {game_data['min_playtime']}-{game_data['max_playtime']}")
        else:
            single_time_match = re.search(r'(\d+)\s+(?:Min|Minutes?)', text, re.IGNORECASE)
            if single_time_match:
                game_data['min_playtime'] = int(single_time_match.group(1))
                game_data['max_playtime'] = int(single_time_match.group(1))
                logger.info(f"Extracted single playtime: {game_data['min_playtime']}")
        
        # Age - try multiple patterns
        age_match = re.search(r'(?:Age|Ages?):\s*(\d+)\+', text, re.IGNORECASE)
        if not age_match:
            age_match = re.search(r'(\d+)\+\s+(?:yrs|years?)', text, re.IGNORECASE)
        if age_match:
            game_data['min_age'] = int(age_match.group(1))
            logger.info(f"Extracted min age: {game_data['min_age']}")
        
        # Extract designer
        designer_elem = soup.select_one('a[href*="/boardgamedesigner/"]')
        if designer_elem:
            game_data['designer'] = designer_elem.get_text(strip=True)
            logger.info(f"Extracted designer: {game_data['designer']}")
        
        # Extract rating
        rating_elem = soup.select_one('span.rating-value, div[class*="rating"]')
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            rating_match = re.search(r'(\d+\.\d+)', rating_text)
            if rating_match:
                game_data['rating_average'] = float(rating_match.group(1))
                logger.info(f"Extracted rating: {game_data['rating_average']}")
        
        # Extract rank
        rank_elem = soup.select_one('span[class*="rank"], div[class*="rank"]')
        if rank_elem:
            rank_text = rank_elem.get_text(strip=True)
            rank_match = re.search(r'#(\d+)', rank_text)
            if rank_match:
                game_data['rank_overall'] = int(rank_match.group(1))
                logger.info(f"Extracted rank: {game_data['rank_overall']}")
        
        logger.info(f"Scraped game data complete. Fields found: {list(game_data.keys())}")
        logger.info(f"Full data: {game_data}")
        return game_data
    except Exception as e:
        logger.error(f"BGG page scraping exception: {str(e)}")
        return {}


def fetch_boardgameprices(bgg_id: str) -> Dict:
    """
    Fetch pricing information from BoardGamePrices.co.uk.
    
    Args:
        bgg_id: BoardGameGeek game ID
        
    Returns:
        Dictionary with price, store, url, availability
    """
    try:
        # Skip if this is a BGA ID
        if bgg_id.startswith('bga_'):
            logger.info("Skipping BoardGamePrices for BGA ID")
            return {}
        
        params = {'bggid': bgg_id}
        response = requests.get(BOARDGAMEPRICES_API, params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"BoardGamePrices API error: {response.status_code}")
            return {}
        
        data = response.json()
        
        if not data or 'prices' not in data:
            logger.warning(f"No pricing data for BGG ID: {bgg_id}")
            return {}
        
        prices = data['prices']
        if not prices:
            return {}
        
        # Get lowest price (prices are already sorted)
        lowest = prices[0]
        
        # Extract price and currency
        price_str = lowest.get('price', '0')
        currency = lowest.get('currency', 'GBP')
        
        # Parse price
        price_match = re.search(r'[\d.]+', price_str)
        if not price_match:
            return {}
        
        price = float(price_match.group())
        
        # Convert GBP to EUR if needed
        if currency == 'GBP':
            price = round(price * GBP_TO_EUR, 2)
        
        return {
            'price': price,
            'store': lowest.get('shop', ''),
            'url': lowest.get('url', ''),
            'availability': lowest.get('availability', ''),
        }
    except Exception as e:
        logger.error(f"BoardGamePrices exception: {str(e)}")
        return {}
