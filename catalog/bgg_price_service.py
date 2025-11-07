"""
BoardGameGeek and BoardGamePrices integration service
"""
import requests
import urllib3
import xml.etree.ElementTree as ET
import time
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
    
    # All API strategies failed, try web scraping as fallback
    print(f"All {len(strategies)} API strategies failed, trying web scraping fallback...")
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
            
            results = []
            # Look for game links in search results
            # BGG search results typically have links like /boardgame/XXXXX/game-name
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/boardgame/' in href and href.count('/') >= 3:
                    try:
                        # Extract BGG ID from URL like /boardgame/13/catan
                        parts = href.split('/')
                        if len(parts) >= 3 and parts[1] == 'boardgame':
                            bgg_id = parts[2]
                            if bgg_id.isdigit():
                                game_name = link.get_text().strip()
                                if game_name and len(game_name) > 1:
                                    # Avoid duplicates
                                    if not any(r['bgg_id'] == bgg_id for r in results):
                                        results.append({
                                            "bgg_id": bgg_id,
                                            "name": game_name,
                                            "year": None,
                                            "type": "boardgame"
                                        })
                                        if len(results) >= 20:
                                            break
                    except Exception as parse_error:
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


def get_bgg_game_details(bgg_id: str) -> Dict[str, Any]:
    """
    Fetch complete game details from BGG including metadata and price from BoardGamePrices.
    """
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
                    
                    # Try to find year
                    year_published = None
                    year_span = soup.find('span', class_='yearpublished')
                    if year_span:
                        year_text = year_span.get_text().strip('()')
                        if year_text.isdigit():
                            year_published = int(year_text)
                    
                    # Try to find thumbnail
                    thumbnail_url = None
                    img_tag = soup.find('img', class_='game-image')
                    if not img_tag:
                        img_tag = soup.find('meta', property='og:image')
                        if img_tag:
                            thumbnail_url = img_tag.get('content')
                    else:
                        thumbnail_url = img_tag.get('src')
                    
                    # Basic scraped data
                    scraped_data = {
                        "bgg_id": bgg_id,
                        "name": primary_name or f"Game {bgg_id}",
                        "year_published": year_published,
                        "thumbnail_url": thumbnail_url,
                        "description": "Details available on BoardGameGeek",
                        "image_url": thumbnail_url,
                        "designer": None,
                        "min_players": None,
                        "max_players": None,
                        "min_playtime": None,
                        "max_playtime": None,
                        "playing_time": None,
                        "min_age": None,
                        "categories": None,
                        "mechanics": None,
                        "rating_average": None,
                        "rating_bayes": None,
                        "rank_overall": None,
                        "num_ratings": None,
                        "msrp_price": None,
                        "price_incl_shipping": None,
                        "store_name": None,
                        "store_url": None,
                        "price_status": "scraped",
                        "price_currency_source": "unknown",
                        "price_last_seen": None,
                    }
                    
                    print(f"Web scraping succeeded for game {bgg_id}: {primary_name}")
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
