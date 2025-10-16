import requests
import csv
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

GBP_TO_EUR_RATE = 1.17  # Set externally if needed
REGION = "IE"
CURRENCY = "EUR"

BGG_SEARCH_URL = "https://boardgamegeek.com/xmlapi2/search"
BGG_THING_URL = "https://boardgamegeek.com/xmlapi2/thing"
BOARDGAMEPRICES_URL = "https://www.boardgameprices.co.uk/plugin/info"

HEADERS = {
    "User-Agent": "bgcatalog/1.0 (contact: popperl@gmail.com)"
}


def get_now_utc():
    return datetime.now(timezone.utc).isoformat()


def resolve_bgg_id(game_input: str) -> Dict[str, Any]:
    """
    If input is numeric, treat as BGG ID. Else, search by name.
    Returns: {bgg_id, resolution_method, bgg_thing_url}
    """
    if game_input.isdigit():
        return {
            "bgg_id": game_input,
            "resolution_method": "id",
            "bgg_thing_url": f"{BGG_THING_URL}?id={game_input}&stats=1"
        }
    # Name search
    params = {"query": game_input, "type": "boardgame"}
    r = requests.get(BGG_SEARCH_URL, params=params, headers=HEADERS)
    if r.status_code != 200:
        return {"error": "BGG search failed", "resolution_method": "name_search"}
    import xml.etree.ElementTree as ET
    root = ET.fromstring(r.text)
    items = root.findall("item")
    if not items:
        return {"error": "No BGG match", "resolution_method": "name_search"}
    bgg_id = items[0].attrib["id"]
    return {
        "bgg_id": bgg_id,
        "resolution_method": "name_search",
        "bgg_thing_url": f"{BGG_THING_URL}?id={bgg_id}&stats=1"
    }


def fetch_bgg_metadata(bgg_id: str) -> Dict[str, Any]:
    """Fetch BGG metadata for a game."""
    params = {"id": bgg_id, "stats": 1}
    r = requests.get(BGG_THING_URL, params=params, headers=HEADERS)
    if r.status_code != 200:
        return {"error": "BGG thing fetch failed"}
    import xml.etree.ElementTree as ET
    root = ET.fromstring(r.text)
    item = root.find("item")
    if item is None:
        return {"error": "No BGG item found"}
    # Extract fields
    def get_text(tag):
        el = item.find(tag)
        return el.text if el is not None else None
    primary_name = None
    for name in item.findall("name"):
        if name.attrib.get("type") == "primary":
            primary_name = name.attrib["value"]
            break
    yearpublished = get_text("yearpublished")
    image = get_text("image")
    thumbnail = get_text("thumbnail")
    stats = item.find("statistics")
    rating_average = None
    rating_bayes = None
    rank_overall = None
    if stats is not None:
        ratings = stats.find("ratings")
        if ratings is not None:
            rating_average = float(ratings.findtext("average", default="0"))
            rating_bayes = float(ratings.findtext("bayesaverage", default="0"))
        ranks = stats.find("ranks")
        if ranks is not None:
            for rank in ranks.findall("rank"):
                if rank.attrib.get("name") == "boardgame":
                    rank_overall = int(rank.attrib.get("value", "0"))
    minplayers = get_text("minplayers")
    maxplayers = get_text("maxplayers")
    playingtime = get_text("playingtime")
    return {
        "title": primary_name,
        "year": int(yearpublished) if yearpublished else None,
        "image": image,
        "thumbnail": thumbnail,
        "rating_average": rating_average,
        "rating_bayes": rating_bayes,
        "rank_overall": rank_overall,
        "players_min": int(minplayers) if minplayers else None,
        "players_max": int(maxplayers) if maxplayers else None,
        "playing_time_min": int(playingtime) if playingtime else None
    }


def fetch_boardgameprices(bgg_id: str) -> Dict[str, Any]:
    """Fetch price data from BoardGamePrices for Ireland."""
    params = {
        "eid": bgg_id,
        "currency": CURRENCY,
        "destination": REGION
    }
    r = requests.get(BOARDGAMEPRICES_URL, params=params, headers=HEADERS)
    if r.status_code != 200:
        return {"error": "BoardGamePrices fetch failed", "price_status": "error"}
    data = r.json()
    offers = data.get("offers", [])
    # Filter for EU/UK stores only
    eu_offers = [o for o in offers if o.get("currency") == "EUR" and o.get("destination") == REGION]
    gbp_offers = [o for o in offers if o.get("currency") == "GBP" and o.get("destination") == REGION]
    # Find lowest price
    def get_lowest(offers, key):
        valid = [o for o in offers if o.get(key) is not None]
        if not valid:
            return None, None, None, None, None, None
        lowest = min(valid, key=lambda o: o[key])
        return (
            lowest[key],
            lowest.get("price_incl_shipping"),
            lowest.get("store"),
            lowest.get("url"),
            lowest.get("stock"),
            lowest.get("last_seen")
        )
    # EUR offers
    base_price_eur, base_price_eur_incl_shipping, store_name, store_url, stock_status, last_seen = get_lowest(eu_offers, "price")
    price_currency_source = "native"
    price_status = "ok" if base_price_eur else "not_found_eu"
    # GBP fallback
    if not base_price_eur and gbp_offers:
        base_price_gbp, base_price_gbp_incl_shipping, store_name, store_url, stock_status, last_seen = get_lowest(gbp_offers, "price")
        base_price_eur = round(base_price_gbp * GBP_TO_EUR_RATE, 2) if base_price_gbp else None
        base_price_eur_incl_shipping = round(base_price_gbp_incl_shipping * GBP_TO_EUR_RATE, 2) if base_price_gbp_incl_shipping else None
        price_currency_source = "conversion"
        price_status = "ok" if base_price_eur else "not_found_eu"
    return {
        "base_price_eur": base_price_eur,
        "base_price_eur_incl_shipping": base_price_eur_incl_shipping,
        "store_name": store_name,
        "store_url": store_url,
        "stock_status": stock_status or "unknown",
        "price_status": price_status,
        "price_currency_source": price_currency_source,
        "last_seen": last_seen
    }


def process_games(game_inputs: List[str], gbp_to_eur_rate: float = 1.17):
    results = []
    for game_input in game_inputs:
        resolved = resolve_bgg_id(game_input)
        bgg_id = resolved.get("bgg_id")
        if not bgg_id:
            result = {"input": game_input, "error": resolved.get("error", "Could not resolve BGG ID")}
            results.append(result)
            continue
        meta = fetch_bgg_metadata(bgg_id)
        price = fetch_boardgameprices(bgg_id)
        now_utc = get_now_utc()
        result = {
            "input": game_input,
            "bgg_id": bgg_id,
            "region": REGION,
            "currency": CURRENCY,
            "capture_time_utc": now_utc,
            "resolution_method": resolved.get("resolution_method"),
            "sources": {
                "bgg_thing_url": resolved.get("bgg_thing_url"),
                "boardgameprices_hint": f"currency=EUR&destination=IE&eid={bgg_id}"
            },
            "notes": ""
        }
        result.update(meta)
        result.update(price)
        results.append(result)
    return results


def save_jsonl(results, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")


def save_csv(results, filename):
    if not results:
        return
    keys = list(results[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

if __name__ == "__main__":
    # Example usage
    game_inputs = ["174430", "Cascadia", "234277", "Brass: Birmingham"]
    results = process_games(game_inputs, gbp_to_eur_rate=GBP_TO_EUR_RATE)
    save_jsonl(results, "prices_ie.jsonl")
    save_csv(results, "prices_ie.csv")
    print("Done! Saved prices_ie.jsonl and prices_ie.csv.")
