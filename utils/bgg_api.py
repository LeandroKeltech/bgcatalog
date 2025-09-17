import requests
import xml.etree.ElementTree as ET
from kivymd.toast import toast

BGG_API_BASE = "https://api.geekdo.com/xmlapi2"

def search_by_barcode(barcode):
    """
    Search BGG by barcode (EAN).
    Returns list of game suggestions or empty list.
    """
    try:
        # BGG doesn't directly support barcode search
        # This is a placeholder - in reality we'd need a barcode-to-game database
        return []
    except Exception as e:
        toast(f"BGG search failed: {e}")
        return []

def search_by_name(name):
    """
    Search BGG by game name.
    Returns list of game suggestions with id, name, year.
    """
    try:
        url = f"{BGG_API_BASE}/search"
        params = {"query": name, "type": "boardgame"}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        root = ET.fromstring(response.content)
        games = []
        
        for item in root.findall("item")[:5]:  # Limit to 5 results
            game = {
                "id": item.get("id"),
                "name": item.find("name").get("value"),
                "year": item.find("yearpublished").get("value") if item.find("yearpublished") is not None else "Unknown"
            }
            games.append(game)
        
        return games
    except Exception as e:
        toast(f"BGG search failed: {e}")
        return []

def get_game_details(bgg_id):
    """
    Get detailed game info by BGG ID.
    Returns dict with name, year, description, etc.
    """
    try:
        url = f"{BGG_API_BASE}/thing"
        params = {"id": bgg_id}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        root = ET.fromstring(response.content)
        item = root.find("item")
        
        if item is None:
            return None
        
        name_elem = item.find("name[@type='primary']")
        if name_elem is None:
            name_elem = item.find("name")
        
        return {
            "id": item.get("id"),
            "name": name_elem.get("value") if name_elem is not None else "Unknown",
            "year": item.find("yearpublished").get("value") if item.find("yearpublished") is not None else "Unknown",
            "description": item.find("description").text if item.find("description") is not None else ""
        }
    except Exception as e:
        toast(f"BGG details failed: {e}")
        return None
