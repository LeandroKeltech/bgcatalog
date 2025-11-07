"""
BoardGameGeek and BoardGamePrices integration service
"""
import requests
import urllib3
import xml.etree.ElementTree as ET
import time
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Suppress SSL warnings when using verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GBP_TO_EUR_RATE = 1.17
REGION = "IE"
CURRENCY = "EUR"

BGG_SEARCH_URL = "https://boardgamegeek.com/xmlapi2/search"
BGG_THING_URL = "https://boardgamegeek.com/xmlapi2/thing"
BOARDGAMEPRICES_URL = "https://www.boardgameprices.co.uk/plugin/info"

# Board Game Atlas API (alternative to BGG when it's blocked)
# Free tier: 100 requests/month - Get your key at https://www.boardgameatlas.com/api/docs
BGA_SEARCH_URL = "https://api.boardgameatlas.com/api/search"
BGA_CLIENT_ID = "JMc8dOwiQE"  # Public client ID for testing

# More complete browser-like headers to avoid 401
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1"
}

# Create a session to maintain cookies
_bgg_session = None

def get_bgg_session():
    """Get or create a requests session with BGG cookies"""
    global _bgg_session
    if _bgg_session is None:
        _bgg_session = requests.Session()
        # Visit main page to get cookies
        try:
            _bgg_session.get("https://boardgamegeek.com/", headers=HEADERS, timeout=10, verify=False)
        except:
            pass
    return _bgg_session


def search_bgg_games(query: str, exact: bool = False) -> List[Dict[str, Any]]:
    """
    Search for board games on BGG by name.
    Returns a list of games with basic info for selection.
    """
    params = {
        "query": query,
        "type": "boardgame",
        "exact": 1 if exact else 0
    }
    
    # Get session with cookies
    session = get_bgg_session()
    
    # Try multiple strategies to avoid 401 errors
    strategies = [
        # Strategy 1: Use session with full headers
        {
            "use_session": True,
            "headers": HEADERS,
            "verify": False,
            "delay": 0
        },
        # Strategy 2: Session with minimal headers
        {
            "use_session": True,
            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            "verify": False,
            "delay": 1
        },
        # Strategy 3: Direct request without session
        {
            "use_session": False,
            "headers": HEADERS,
            "verify": False,
            "delay": 0.5
        },
    ]
    
    for i, strategy in enumerate(strategies):
        try:
            if strategy["delay"] > 0:
                time.sleep(strategy["delay"])
            
            print(f"Trying BGG search strategy {i+1}/{len(strategies)}")
            
            if strategy["use_session"]:
                response = session.get(
                    BGG_SEARCH_URL, 
                    params=params, 
                    headers=strategy["headers"],
                    timeout=15,
                    verify=strategy["verify"]
                )
            else:
                response = requests.get(
                    BGG_SEARCH_URL, 
                    params=params, 
                    headers=strategy["headers"],
                    timeout=15,
                    verify=strategy["verify"]
                )
            
            # If we get a response (even if it's an error), check it
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                items = root.findall("item")
                
                results = []
                for item in items[:20]:  # Limit to first 20 results
                    bgg_id = item.attrib.get("id")
                    game_type = item.attrib.get("type")
                    
                    # Get primary name
                    name_elem = item.find("name[@type='primary']")
                    if name_elem is None:
                        name_elem = item.find("name")
                    name = name_elem.attrib.get("value", "Unknown") if name_elem is not None else "Unknown"
                    
                    # Get year
                    year_elem = item.find("yearpublished")
                    year = year_elem.attrib.get("value") if year_elem is not None else None
                    
                    results.append({
                        "bgg_id": bgg_id,
                        "name": name,
                        "year": int(year) if year else None,
                        "type": game_type
                    })
                
                print(f"Strategy {i+1} succeeded! Found {len(results)} results")
                return results
            elif response.status_code == 401:
                print(f"Strategy {i+1} got 401, trying next strategy...")
                continue
            else:
                print(f"Strategy {i+1} got status {response.status_code}, trying next...")
                continue
                
        except requests.exceptions.HTTPError as e:
            print(f"Strategy {i+1} HTTP error: {e}")
            continue
        except requests.exceptions.RequestException as e:
            print(f"Strategy {i+1} network error: {e}")
            continue
        except ET.ParseError as e:
            print(f"Strategy {i+1} XML parse error: {e}")
            continue
        except Exception as e:
            print(f"Strategy {i+1} unexpected error: {e}")
            continue
    
    # Strategy 4: Try Board Game Atlas API (alternative database)
    print("All BGG API strategies failed, trying Board Game Atlas API...")
    try:
        bga_params = {
            "name": query,
            "fuzzy_match": "true",
            "limit": 20,
            "client_id": BGA_CLIENT_ID
        }
        
        response = requests.get(BGA_SEARCH_URL, params=bga_params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            games = data.get("games", [])
            
            if games:
                results = []
                for game in games:
                    # Board Game Atlas has its own IDs, but many games have BGG IDs in metadata
                    bgg_id = None
                    
                    # Try to get BGG ID from the game data
                    # BGA doesn't always have BGG IDs, so we'll use BGA ID prefixed with 'bga_'
                    if game.get("id"):
                        bgg_id = f"bga_{game['id']}"
                    
                    results.append({
                        "bgg_id": bgg_id or game.get("handle", "unknown"),
                        "name": game.get("name", "Unknown"),
                        "year": game.get("year_published"),
                        "type": "boardgame",
                        "thumbnail": game.get("thumb_url") or game.get("image_url"),
                        "_bga_id": game.get("id"),  # Store original BGA ID
                        "_source": "bga"  # Mark as coming from Board Game Atlas
                    })
                
                print(f"Board Game Atlas API succeeded! Found {len(results)} results")
                return results
            else:
                print("Board Game Atlas returned no results")
        else:
            print(f"Board Game Atlas API returned status {response.status_code}")
            
    except Exception as e:
        print(f"Board Game Atlas API error: {e}")
    
    # Fallback: Web scraping BGG
    print("Trying web scraping fallback...")
    try:
        from bs4 import BeautifulSoup
        
        # Try scraping BGG search page
        search_url = f"https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://boardgamegeek.com/",
        }
        
        print(f"Trying to scrape BGG search page: {search_url}")
        response = session.get(search_url, headers=headers, timeout=15, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Debug: print a sample of the HTML to understand structure
            print(f"Received HTML page with length: {len(response.text)} chars")
            
            results = []
            # Look for game links in search results with thumbnails
            # BGG search results typically have rows with game info
            
            # Try to find game rows/items
            game_rows = soup.find_all('tr', id=re.compile(r'row_'))
            print(f"Found {len(game_rows)} table rows with id pattern 'row_'")
            
            if not game_rows:
                game_rows = soup.find_all('div', class_=re.compile(r'game|item'))
                print(f"Found {len(game_rows)} divs with class pattern 'game' or 'item'")
            
            if not game_rows:
                # Fallback: look for ANY links with /boardgame/ pattern
                print("No structured rows found, searching for boardgame links...")
                all_links = soup.find_all('a', href=re.compile(r'/boardgame/\d+'))
                print(f"Found {len(all_links)} links matching /boardgame/XXXXX pattern")
                
                for link in all_links:
                    href = link.get('href', '')
                    if '/boardgame/' in href:
                        try:
                            # Extract BGG ID from URL like /boardgame/13/catan
                            parts = href.split('/')
                            # Find the boardgame part and get the next element (ID)
                            if 'boardgame' in parts:
                                idx = parts.index('boardgame')
                                if idx + 1 < len(parts):
                                    bgg_id = parts[idx + 1]
                                    if bgg_id.isdigit():
                                        game_name = link.get_text().strip()
                                        if game_name and len(game_name) > 1:
                                            # Avoid duplicates
                                            if not any(r['bgg_id'] == bgg_id for r in results):
                                                # Try to find nearby image
                                                thumbnail = None
                                                parent = link.parent
                                                if parent:
                                                    img = parent.find('img')
                                                    if img:
                                                        thumbnail = img.get('src') or img.get('data-src')
                                                
                                                print(f"Found game via link: {game_name} (ID: {bgg_id})")
                                                results.append({
                                                    "bgg_id": bgg_id,
                                                    "name": game_name,
                                                    "year": None,
                                                    "type": "boardgame",
                                                    "thumbnail": thumbnail
                                                })
                                                if len(results) >= 20:
                                                    break
                        except Exception as parse_error:
                            print(f"Error parsing link {href}: {parse_error}")
                            continue
            else:
                # Parse structured rows
                print(f"Processing {len(game_rows)} structured rows...")
                processed = 0
                for row in game_rows:
                    try:
                        processed += 1
                        # Find game link - try multiple patterns
                        link = row.find('a', href=re.compile(r'/boardgame/\d+'))
                        if not link:
                            if processed <= 3:  # Debug first 3 rows
                                print(f"Row {processed}: No link found with /boardgame/ pattern")
                            continue
                        
                        href = link.get('href', '')
                        
                        # Extract BGG ID from URL - handle different URL formats
                        # Could be: /boardgame/123/name or boardgame/123/name or https://...
                        parts = href.split('/')
                        bgg_id = None
                        
                        # Find 'boardgame' in parts and get the next element
                        for i, part in enumerate(parts):
                            if part == 'boardgame' and i + 1 < len(parts):
                                potential_id = parts[i + 1]
                                if potential_id.isdigit():
                                    bgg_id = potential_id
                                    break
                        
                        if not bgg_id:
                            if processed <= 3:  # Debug first 3 rows
                                print(f"Row {processed}: Found link {href} but couldn't extract ID")
                            continue
                        
                        # Try to get game name from the link text first
                        game_name = link.get_text().strip()
                        
                        # If link text is empty, try to find name in other elements within the row
                        if not game_name or len(game_name) <= 1:
                            # Try finding a primary name element
                            primary_name = row.find('a', class_='primary')
                            if primary_name:
                                game_name = primary_name.get_text().strip()
                            
                            # Try finding any link within the row that has substantial text
                            if not game_name:
                                for a_tag in row.find_all('a'):
                                    text = a_tag.get_text().strip()
                                    if text and len(text) > 2 and '/boardgame/' not in text:
                                        game_name = text
                                        break
                            
                            # Last resort: get all text from row and try to extract game name
                            if not game_name:
                                row_text = row.get_text().strip()
                                # Remove year if present
                                row_text = re.sub(r'\(\d{4}\)', '', row_text).strip()
                                # Take first substantial text
                                if row_text and len(row_text) > 2:
                                    game_name = row_text.split('\n')[0].strip()
                        
                        if processed <= 3:  # Debug first 3 rows
                            print(f"Row {processed}: Extracted name '{game_name}' for ID {bgg_id}")
                        
                        # Try to find thumbnail
                        thumbnail = None
                        img = row.find('img')
                        if img:
                            thumbnail = img.get('src') or img.get('data-src')
                        
                        # Try to find year
                        year = None
                        year_match = re.search(r'\((\d{4})\)', row.get_text())
                        if year_match:
                            year = int(year_match.group(1))
                        
                        if game_name and len(game_name) > 1:
                            if not any(r['bgg_id'] == bgg_id for r in results):
                                print(f"Found game from row: {game_name} (ID: {bgg_id}, Year: {year})")
                                results.append({
                                    "bgg_id": bgg_id,
                                    "name": game_name,
                                    "year": year,
                                    "type": "boardgame",
                                    "thumbnail": thumbnail
                                })
                                if len(results) >= 20:
                                    break
                        else:
                            if processed <= 3:  # Debug first 3 rows
                                print(f"Row {processed}: Game name too short or empty: '{game_name}'")
                    except Exception as parse_error:
                        if processed <= 3:  # Debug first 3 rows
                            print(f"Row {processed} error: {parse_error}")
                        continue
            
            if results:
                print(f"Web scraping succeeded! Found {len(results)} results")
                return results
            else:
                print("Web scraping found no results")
        else:
            print(f"Web scraping failed with status {response.status_code}")
            
    except ImportError:
        print("BeautifulSoup not available for web scraping fallback")
    except Exception as scrape_error:
        print(f"Web scraping error: {scrape_error}")
    
    # Ultimate fallback - return empty list
    print("All strategies including web scraping failed")
    return []


def get_bga_game_details(bga_id: str) -> Dict[str, Any]:
    """
    Fetch game details from Board Game Atlas API.
    Then try to enrich with BGG data.
    """
    print(f"Fetching Board Game Atlas details for ID: {bga_id}")
    try:
        params = {
            "ids": bga_id,
            "client_id": BGA_CLIENT_ID
        }
        
        print(f"BGA API request: {BGA_SEARCH_URL} with params {params}")
        response = requests.get(BGA_SEARCH_URL, params=params, timeout=10)
        
        print(f"BGA API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            games = data.get("games", [])
            
            print(f"BGA API returned {len(games)} games")
            
            if games:
                game = games[0]
                
                print(f"Processing BGA game: {game.get('name')}")
                print(f"BGA game data keys: {list(game.keys())}")
                print(f"BGA raw data - year: {game.get('year_published')}, designer: {game.get('primary_designer')}, designers: {game.get('designers')}")
                print(f"BGA raw data - url: {game.get('url')}, rules_url: {game.get('rules_url')}, official_url: {game.get('official_url')}")
                
                # Extract designers from primary_designer or designers array
                designers = []
                if game.get("primary_designer"):
                    designers.append(game.get("primary_designer"))
                elif game.get("designers"):
                    designers = game.get("designers", [])[:3]  # Limit to 3
                
                designer = ", ".join(designers) if designers else None
                
                # Try to get the actual BGG ID from the game's URL or rules_url
                actual_bgg_id = None
                
                # Check multiple fields for BGG ID
                for url_field in ['url', 'rules_url', 'official_url']:
                    url_value = game.get(url_field, '')
                    if url_value and "boardgamegeek.com" in url_value:
                        match = re.search(r'/boardgame/(\d+)', url_value)
                        if match:
                            actual_bgg_id = match.group(1)
                            print(f"Found BGG ID {actual_bgg_id} from {url_field}")
                            break
                
                # Get full description
                description = game.get("description") or game.get("description_preview") or "No description available"
                
                year_published = game.get("year_published")
                min_players = game.get("min_players")
                max_players = game.get("max_players")
                min_playtime = game.get("min_playtime")
                max_playtime = game.get("max_playtime")
                min_age = game.get("min_age")
                
                # If we have a real BGG ID, try to get complete details via web scraping
                if actual_bgg_id:
                    print(f"Found BGG ID {actual_bgg_id}, attempting comprehensive BGG web scraping...")
                    try:
                        bgg_data = scrape_bgg_game_page(actual_bgg_id)
                        
                        # Override with BGG data where available (it's usually more complete)
                        if bgg_data.get("designer"):
                            designer = bgg_data["designer"]
                            print(f"Using BGG designer: {designer}")
                        if bgg_data.get("year_published"):
                            year_published = bgg_data["year_published"]
                            print(f"Using BGG year: {year_published}")
                        if bgg_data.get("description") and len(bgg_data["description"]) > len(description):
                            description = bgg_data["description"]
                            print(f"Using BGG description (longer)")
                        if bgg_data.get("min_players"):
                            min_players = bgg_data["min_players"]
                            max_players = bgg_data["max_players"]
                        if bgg_data.get("min_playtime"):
                            min_playtime = bgg_data["min_playtime"]
                            max_playtime = bgg_data["max_playtime"]
                        if bgg_data.get("min_age"):
                            min_age = bgg_data["min_age"]
                            
                    except Exception as scrape_err:
                        print(f"BGG scraping failed but continuing with BGA data: {scrape_err}")
                
                # Extract categories
                categories = []
                if game.get("categories"):
                    cat_list = game.get("categories", [])
                    if isinstance(cat_list, list):
                        categories = [c.get("id") if isinstance(c, dict) else str(c) for c in cat_list[:5]]
                
                # Extract mechanics
                mechanics = []
                if game.get("mechanics"):
                    mech_list = game.get("mechanics", [])
                    if isinstance(mech_list, list):
                        mechanics = [m.get("id") if isinstance(m, dict) else str(m) for m in mech_list[:5]]
                
                # Map BGA data to our format
                result = {
                    "bgg_id": f"bga_{bga_id}",
                    "name": game.get("name"),
                    "year_published": year_published,
                    "description": description,
                    "image_url": game.get("image_url"),
                    "thumbnail_url": game.get("thumb_url") or game.get("image_url"),
                    "designer": designer,
                    "min_players": min_players,
                    "max_players": max_players,
                    "min_playtime": min_playtime,
                    "max_playtime": max_playtime,
                    "playing_time": max_playtime,
                    "min_age": min_age,
                    "categories": ", ".join(categories) if categories else None,
                    "mechanics": ", ".join(mechanics) if mechanics else None,
                    "rating_average": game.get("average_user_rating"),
                    "rating_bayes": None,
                    "rank_overall": game.get("rank"),
                    "num_ratings": game.get("num_user_ratings"),
                    # Price data
                    "msrp_price": game.get("msrp"),
                    "price_incl_shipping": None,
                    "store_name": None,
                    "store_url": game.get("official_url"),
                    "price_status": "bga_source",
                    "price_currency_source": "usd",
                    "last_seen": None,
                }
                
                print(f"Final result: designer={result['designer']}, year={result['year_published']}, players={result['min_players']}-{result['max_players']}")
                return result
            else:
                print("BGA API returned empty games array")
        
        print(f"Board Game Atlas details failed with status {response.status_code}")
        return {"error": "Board Game Atlas API failed"}
        
    except Exception as e:
        print(f"Error fetching BGA details: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def scrape_bgg_game_page(bgg_id: str) -> Dict[str, Any]:
    """
    Comprehensive web scraping of BGG game page to extract all details.
    """
    try:
        from bs4 import BeautifulSoup
        
        game_url = f"https://boardgamegeek.com/boardgame/{bgg_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://boardgamegeek.com/",
        }
        
        print(f"Scraping BGG game page: {game_url}")
        response = requests.get(game_url, headers=headers, timeout=15, verify=False)
        
        if response.status_code != 200:
            print(f"BGG scraping returned status {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        result = {}
        
        # Extract year
        year_match = re.search(r'\((\d{4})\)', soup.find('title').get_text() if soup.find('title') else '')
        if year_match:
            result["year_published"] = int(year_match.group(1))
        
        # Extract designer
        designer_link = soup.find('a', href=re.compile(r'/boardgamedesigner/'))
        if designer_link:
            result["designer"] = designer_link.get_text().strip()
        
        # Extract description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            result["description"] = meta_desc.get('content', '').strip()
        
        # Extract players (e.g., "2-4 Players")
        players_match = re.search(r'(\d+)[-–](\d+)\s+[Pp]layers?', page_text)
        if players_match:
            result["min_players"] = int(players_match.group(1))
            result["max_players"] = int(players_match.group(2))
        else:
            players_match = re.search(r'(\d+)\s+[Pp]layers?', page_text)
            if players_match:
                result["min_players"] = int(players_match.group(1))
                result["max_players"] = result["min_players"]
        
        # Extract playtime (e.g., "30-60 Min")
        playtime_match = re.search(r'(\d+)[-–](\d+)\s+[Mm]in', page_text)
        if playtime_match:
            result["min_playtime"] = int(playtime_match.group(1))
            result["max_playtime"] = int(playtime_match.group(2))
        else:
            playtime_match = re.search(r'(\d+)\s+[Mm]in', page_text)
            if playtime_match:
                result["min_playtime"] = int(playtime_match.group(1))
                result["max_playtime"] = result["min_playtime"]
        
        # Extract age (e.g., "10+")
        age_match = re.search(r'[Aa]ge[:\s]+(\d+)', page_text)
        if age_match:
            result["min_age"] = int(age_match.group(1))
        else:
            age_match = re.search(r'(\d+)\+', page_text)
            if age_match:
                result["min_age"] = int(age_match.group(1))
        
        print(f"BGG scraping extracted: {list(result.keys())}")
        return result
        
    except Exception as e:
        print(f"Error scraping BGG page: {e}")
        return {}


def get_bgg_game_details(bgg_id: str) -> Dict[str, Any]:
    """
    Fetch complete game details from BGG including metadata and price from BoardGamePrices.
    Falls back to Board Game Atlas if BGG fails.
    """
    # Check if this is a Board Game Atlas ID
    if bgg_id.startswith("bga_"):
        return get_bga_game_details(bgg_id.replace("bga_", ""))
    
    params = {"id": bgg_id, "stats": 1}
    
    # Get session with cookies
    session = get_bgg_session()
    
    try:
        # Try with session first
        response = session.get(BGG_THING_URL, params=params, headers=HEADERS, timeout=15, verify=False)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        item = root.find("item")
        
        if item is None:
            return {"error": "Game not found"}
        
        # Extract basic info
        primary_name = None
        for name in item.findall("name"):
            if name.attrib.get("type") == "primary":
                primary_name = name.attrib["value"]
                break
        
        # Helper function to safely get text
        def get_text(tag):
            el = item.find(tag)
            return el.attrib.get("value") if el is not None and "value" in el.attrib else None
        
        # Year
        yearpublished = get_text("yearpublished")
        
        # Images
        image_elem = item.find("image")
        image = image_elem.text if image_elem is not None else None
        
        thumbnail_elem = item.find("thumbnail")
        thumbnail = thumbnail_elem.text if thumbnail_elem is not None else None
        
        # Description
        description_elem = item.find("description")
        description = description_elem.text if description_elem is not None else None
        
        # Players
        minplayers = get_text("minplayers")
        maxplayers = get_text("maxplayers")
        
        # Playing time
        minplaytime = get_text("minplaytime")
        maxplaytime = get_text("maxplaytime")
        playingtime = get_text("playingtime")
        
        # Age
        minage = get_text("minage")
        
        # Designer
        designers = []
        for link in item.findall("link[@type='boardgamedesigner']"):
            designers.append(link.attrib.get("value"))
        designer = ", ".join(designers) if designers else None
        
        # Categories
        categories = []
        for link in item.findall("link[@type='boardgamecategory']"):
            categories.append(link.attrib.get("value"))
        
        # Mechanics
        mechanics = []
        for link in item.findall("link[@type='boardgamemechanic']"):
            mechanics.append(link.attrib.get("value"))
        
        # Statistics
        stats = item.find("statistics")
        rating_average = None
        rating_bayes = None
        rank_overall = None
        num_ratings = None
        
        if stats is not None:
            ratings = stats.find("ratings")
            if ratings is not None:
                avg_elem = ratings.find("average")
                rating_average = float(avg_elem.attrib.get("value", 0)) if avg_elem is not None else None
                
                bayes_elem = ratings.find("bayesaverage")
                rating_bayes = float(bayes_elem.attrib.get("value", 0)) if bayes_elem is not None else None
                
                num_elem = ratings.find("usersrated")
                num_ratings = int(num_elem.attrib.get("value", 0)) if num_elem is not None else None
                
                # Get overall rank
                ranks_elem = ratings.find("ranks")
                if ranks_elem is not None:
                    for rank in ranks_elem.findall("rank"):
                        if rank.attrib.get("name") == "boardgame":
                            rank_val = rank.attrib.get("value")
                            if rank_val and rank_val != "Not Ranked":
                                rank_overall = int(rank_val)
        
        # Get price from BoardGamePrices
        price_data = fetch_boardgameprices(bgg_id)
        
        return {
            "bgg_id": bgg_id,
            "name": primary_name,
            "year_published": int(yearpublished) if yearpublished else None,
            "description": description,
            "image_url": image,
            "thumbnail_url": thumbnail,
            "designer": designer,
            "min_players": int(minplayers) if minplayers else None,
            "max_players": int(maxplayers) if maxplayers else None,
            "min_playtime": int(minplaytime) if minplaytime else None,
            "max_playtime": int(maxplaytime) if maxplaytime else None,
            "playing_time": int(playingtime) if playingtime else None,
            "min_age": int(minage) if minage else None,
            "categories": ", ".join(categories[:5]) if categories else None,
            "mechanics": ", ".join(mechanics[:5]) if mechanics else None,
            "rating_average": rating_average,
            "rating_bayes": rating_bayes,
            "rank_overall": rank_overall,
            "num_ratings": num_ratings,
            # Price data from BoardGamePrices
            "msrp_price": price_data.get("base_price_eur"),
            "price_incl_shipping": price_data.get("base_price_eur_incl_shipping"),
            "store_name": price_data.get("store_name"),
            "store_url": price_data.get("store_url"),
            "price_status": price_data.get("price_status"),
            "price_currency_source": price_data.get("price_currency_source"),
            "price_last_seen": price_data.get("last_seen"),
        }
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"BGG API returned 401 for game details. Trying web scraping fallback...")
            try:
                from bs4 import BeautifulSoup
                
                # Try scraping BGG game page
                game_url = f"https://boardgamegeek.com/boardgame/{bgg_id}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Referer": "https://boardgamegeek.com/",
                }
                
                print(f"Scraping BGG game page: {game_url}")
                response = requests.get(game_url, headers=headers, timeout=15, verify=False)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract game name from title or h1
                    primary_name = None
                    title_tag = soup.find('title')
                    if title_tag:
                        # Title is usually like "Game Name | Board Game | BoardGameGeek"
                        title_text = title_tag.get_text()
                        if '|' in title_text:
                            primary_name = title_text.split('|')[0].strip()
                    
                    if not primary_name:
                        h1_tag = soup.find('h1')
                        if h1_tag:
                            primary_name = h1_tag.get_text().strip()
                    
                    # Try to find year - multiple approaches
                    year_published = None
                    # Try meta tags first
                    for meta in soup.find_all('meta'):
                        if meta.get('property') == 'og:title' or meta.get('name') == 'title':
                            content = meta.get('content', '')
                            # Look for (YYYY) pattern
                            import re
                            year_match = re.search(r'\((\d{4})\)', content)
                            if year_match:
                                year_published = int(year_match.group(1))
                                break
                    
                    # Fallback to searching in page text
                    if not year_published:
                        year_span = soup.find('span', class_='yearpublished')
                        if year_span:
                            year_text = year_span.get_text().strip('()')
                            if year_text.isdigit():
                                year_published = int(year_text)
                    
                    # Try to find designer
                    designer = None
                    # Look for designer link or text
                    designer_link = soup.find('a', href=re.compile(r'/boardgamedesigner/'))
                    if designer_link:
                        designer = designer_link.get_text().strip()
                    
                    # Try to find description
                    description = None
                    # Try meta description first
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    if meta_desc:
                        description = meta_desc.get('content', '').strip()
                    
                    # Fallback to og:description
                    if not description:
                        og_desc = soup.find('meta', property='og:description')
                        if og_desc:
                            description = og_desc.get('content', '').strip()
                    
                    # Fallback to article or main content
                    if not description:
                        article = soup.find('article') or soup.find('div', class_='game-description')
                        if article:
                            # Get first paragraph
                            first_p = article.find('p')
                            if first_p:
                                description = first_p.get_text().strip()
                    
                    # Try to find thumbnail/image
                    thumbnail_url = None
                    image_url = None
                    
                    # Try og:image first (usually the best quality)
                    og_image = soup.find('meta', property='og:image')
                    if og_image:
                        image_url = og_image.get('content')
                        thumbnail_url = image_url
                    
                    # Fallback to game-image class
                    if not thumbnail_url:
                        img_tag = soup.find('img', class_='game-image')
                        if img_tag:
                            thumbnail_url = img_tag.get('src')
                            image_url = thumbnail_url
                    
                    # Fallback to any img with boardgame in src
                    if not thumbnail_url:
                        for img in soup.find_all('img'):
                            src = img.get('src', '')
                            if 'boardgame' in src.lower() or 'geekdo' in src.lower():
                                thumbnail_url = src
                                image_url = src
                                break
                    
                    # Try to extract game stats (players, playtime, age)
                    min_players = None
                    max_players = None
                    min_playtime = None
                    max_playtime = None
                    playing_time = None
                    min_age = None
                    
                    # Look for gameplay info sections
                    # BGG often has divs/spans with specific classes or data attributes
                    page_text = soup.get_text()
                    
                    # Try to find number of players (e.g., "2-4 Players")
                    players_match = re.search(r'(\d+)[-–](\d+)\s+[Pp]layers?', page_text)
                    if players_match:
                        min_players = int(players_match.group(1))
                        max_players = int(players_match.group(2))
                    else:
                        # Single player count
                        players_match = re.search(r'(\d+)\s+[Pp]layers?', page_text)
                        if players_match:
                            min_players = int(players_match.group(1))
                            max_players = min_players
                    
                    # Try to find playtime (e.g., "30-60 Min", "45 Minutes")
                    playtime_match = re.search(r'(\d+)[-–](\d+)\s+[Mm]in', page_text)
                    if playtime_match:
                        min_playtime = int(playtime_match.group(1))
                        max_playtime = int(playtime_match.group(2))
                        playing_time = max_playtime
                    else:
                        # Single playtime
                        playtime_match = re.search(r'(\d+)\s+[Mm]in', page_text)
                        if playtime_match:
                            playing_time = int(playtime_match.group(1))
                            min_playtime = playing_time
                            max_playtime = playing_time
                    
                    # Try to find minimum age (e.g., "10+", "Age: 12+")
                    age_match = re.search(r'[Aa]ge[:\s]+(\d+)', page_text)
                    if age_match:
                        min_age = int(age_match.group(1))
                    else:
                        age_match = re.search(r'(\d+)\+', page_text)
                        if age_match:
                            min_age = int(age_match.group(1))
                    
                    # Try to extract rating and rank
                    rating_average = None
                    num_ratings = None
                    rank_overall = None
                    
                    # Look for rating pattern (e.g., "7.5" or "Rating: 8.2")
                    rating_match = re.search(r'[Rr]ating[:\s]+(\d+\.?\d*)', page_text)
                    if rating_match:
                        try:
                            rating_average = float(rating_match.group(1))
                        except:
                            pass
                    
                    # Look for number of ratings (e.g., "1234 ratings")
                    num_ratings_match = re.search(r'(\d+)\s+[Rr]atings?', page_text)
                    if num_ratings_match:
                        try:
                            num_ratings = int(num_ratings_match.group(1))
                        except:
                            pass
                    
                    # Look for rank (e.g., "Rank: #42" or "#42 Overall")
                    rank_match = re.search(r'#(\d+)', page_text)
                    if rank_match:
                        try:
                            rank_overall = int(rank_match.group(1))
                        except:
                            pass
                    
                    # Try to extract categories and mechanics
                    categories = []
                    mechanics = []
                    
                    # Look for category links (e.g., href="/boardgamecategory/...")
                    category_links = soup.find_all('a', href=re.compile(r'/boardgamecategory/'))
                    for link in category_links[:5]:  # Limit to 5
                        cat_text = link.get_text().strip()
                        if cat_text and len(cat_text) > 2:
                            categories.append(cat_text)
                    
                    # Look for mechanic links (e.g., href="/boardgamemechanic/...")
                    mechanic_links = soup.find_all('a', href=re.compile(r'/boardgamemechanic/'))
                    for link in mechanic_links[:5]:  # Limit to 5
                        mech_text = link.get_text().strip()
                        if mech_text and len(mech_text) > 2:
                            mechanics.append(mech_text)
                    
                    # Get price data
                    price_data = fetch_boardgameprices(bgg_id)
                    
                    # Basic scraped data
                    scraped_data = {
                        "bgg_id": bgg_id,
                        "name": primary_name or f"Game {bgg_id}",
                        "year_published": year_published,
                        "thumbnail_url": thumbnail_url,
                        "description": description or "Visit BoardGameGeek for full description",
                        "image_url": image_url,
                        "designer": designer,
                        "min_players": min_players,
                        "max_players": max_players,
                        "min_playtime": min_playtime,
                        "max_playtime": max_playtime,
                        "playing_time": playing_time,
                        "min_age": min_age,
                        "categories": ", ".join(categories) if categories else None,
                        "mechanics": ", ".join(mechanics) if mechanics else None,
                        "rating_average": rating_average,
                        "rating_bayes": None,
                        "rank_overall": rank_overall,
                        "num_ratings": num_ratings,
                        "msrp_price": price_data.get("base_price_eur"),
                        "price_incl_shipping": price_data.get("base_price_eur_incl_shipping"),
                        "store_name": price_data.get("store_name"),
                        "store_url": price_data.get("store_url"),
                        "price_status": price_data.get("price_status"),
                        "price_currency_source": price_data.get("price_currency_source"),
                        "price_last_seen": price_data.get("last_seen"),
                    }
                    
                    print(f"Web scraping succeeded for game {bgg_id}: {primary_name} ({year_published})")
                    return scraped_data
                else:
                    print(f"Web scraping failed with status {response.status_code}")
                    
            except ImportError:
                print("BeautifulSoup not available for web scraping fallback")
            except Exception as scrape_error:
                print(f"Web scraping error for game details: {scrape_error}")
        
        print(f"Error fetching BGG details: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Error fetching BGG details: {e}")
        return {"error": str(e)}


def fetch_boardgameprices(bgg_id: str) -> Dict[str, Any]:
    """
    Fetch price data from BoardGamePrices for Ireland (IE) in EUR.
    Falls back to GBP conversion if EUR not available.
    """
    params = {
        "eid": bgg_id,
        "currency": CURRENCY,
        "destination": REGION
    }
    
    try:
        response = requests.get(BOARDGAMEPRICES_URL, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return {
                "base_price_eur": None,
                "base_price_eur_incl_shipping": None,
                "store_name": None,
                "store_url": None,
                "stock_status": "unknown",
                "price_status": "error",
                "price_currency_source": "unknown",
                "last_seen": None
            }
        
        data = response.json()
        offers = data.get("offers", [])
        
        # Filter for EU/UK stores
        eur_offers = [o for o in offers if o.get("currency") == "EUR"]
        gbp_offers = [o for o in offers if o.get("currency") == "GBP"]
        
        # Helper to find lowest price
        def get_lowest(offers, price_key="price"):
            if not offers:
                return None
            valid = [o for o in offers if o.get(price_key) is not None]
            if not valid:
                return None
            return min(valid, key=lambda o: o[price_key])
        
        # Try EUR first
        lowest_offer = get_lowest(eur_offers)
        price_currency_source = "native"
        
        # Fallback to GBP with conversion
        if not lowest_offer:
            lowest_offer = get_lowest(gbp_offers)
            if lowest_offer:
                price_currency_source = "conversion"
                # Convert prices
                if lowest_offer.get("price"):
                    lowest_offer["price"] = round(lowest_offer["price"] * GBP_TO_EUR_RATE, 2)
                if lowest_offer.get("price_incl_shipping"):
                    lowest_offer["price_incl_shipping"] = round(lowest_offer["price_incl_shipping"] * GBP_TO_EUR_RATE, 2)
        
        if not lowest_offer:
            return {
                "base_price_eur": None,
                "base_price_eur_incl_shipping": None,
                "store_name": None,
                "store_url": None,
                "stock_status": "unknown",
                "price_status": "not_found_eu",
                "price_currency_source": "unknown",
                "last_seen": None
            }
        
        return {
            "base_price_eur": lowest_offer.get("price"),
            "base_price_eur_incl_shipping": lowest_offer.get("price_incl_shipping"),
            "store_name": lowest_offer.get("store"),
            "store_url": lowest_offer.get("url"),
            "stock_status": lowest_offer.get("stock", "unknown"),
            "price_status": "ok",
            "price_currency_source": price_currency_source,
            "last_seen": lowest_offer.get("last_seen")
        }
    
    except Exception as e:
        print(f"Error fetching BoardGamePrices: {e}")
        return {
            "base_price_eur": None,
            "base_price_eur_incl_shipping": None,
            "store_name": None,
            "store_url": None,
            "stock_status": "unknown",
            "price_status": "error",
            "price_currency_source": "unknown",
            "last_seen": None
        }
