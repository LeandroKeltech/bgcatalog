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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


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
    
    # Try multiple strategies to avoid 401 errors
    strategies = [
        # Strategy 1: Standard headers with SSL
        {
            "headers": HEADERS,
            "verify": True,
            "delay": 0
        },
        # Strategy 2: Minimal headers with SSL
        {
            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            "verify": True,
            "delay": 1
        },
        # Strategy 3: Minimal headers without SSL
        {
            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            "verify": False,
            "delay": 2
        },
        # Strategy 4: Different User-Agent
        {
            "headers": {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            "verify": False,
            "delay": 1
        },
    ]
    
    for i, strategy in enumerate(strategies):
        try:
            if strategy["delay"] > 0:
                time.sleep(strategy["delay"])
            
            print(f"Trying BGG search strategy {i+1}/{len(strategies)}")
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
    
    # All strategies failed
    print(f"All {len(strategies)} strategies failed for BGG search")
    return []


def get_bgg_game_details(bgg_id: str) -> Dict[str, Any]:
    """
    Fetch complete game details from BGG including metadata and price from BoardGamePrices.
    """
    params = {"id": bgg_id, "stats": 1}
    
    try:
        response = requests.get(BGG_THING_URL, params=params, headers=HEADERS, timeout=10)
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
            print(f"BGG API returned 401 for game details. Trying with simpler headers...")
            try:
                simple_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                response = requests.get(BGG_THING_URL, params=params, headers=simple_headers, timeout=10, verify=False)
                response.raise_for_status()
                # Process response (simplified - just return basic data)
                root = ET.fromstring(response.text)
                item = root.find("item")
                if item:
                    primary_name = None
                    for name in item.findall("name"):
                        if name.attrib.get("type") == "primary":
                            primary_name = name.attrib["value"]
                            break
                    return {
                        "bgg_id": bgg_id,
                        "name": primary_name,
                        "error": None
                    }
            except Exception as retry_error:
                print(f"Retry failed for game details: {retry_error}")
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
