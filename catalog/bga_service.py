"""
Board Game Atlas API Service
API Documentation: https://www.boardgameatlas.com/api/docs
"""
import requests
import logging

logger = logging.getLogger(__name__)

# Client ID público de teste - você pode criar sua própria conta grátis em:
# https://www.boardgameatlas.com/api/docs/apps
CLIENT_ID = "JM0HZBu3g2"

BASE_URL = "https://api.boardgameatlas.com/api"

def search_games(query, limit=10):
    """
    Search for board games by name
    
    Returns list of games with:
    - id, name, year_published, price, msrp, image_url, description_preview
    """
    url = f"{BASE_URL}/search"
    
    params = {
        'name': query,
        'client_id': CLIENT_ID,
        'limit': limit,
        'fuzzy_match': 'true'
    }
    
    try:
        logger.info(f"Searching Board Game Atlas for: {query}")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        games = data.get('games', [])
        
        logger.info(f"Found {len(games)} games for query: {query}")
        
        # Format results
        results = []
        for game in games:
            results.append({
                'bga_id': game.get('id'),
                'name': game.get('name'),
                'year': game.get('year_published'),
                'price': game.get('price', '0'),
                'msrp': game.get('msrp', 0),
                'image_url': game.get('image_url'),
                'thumbnail': game.get('thumb_url'),
                'description': game.get('description_preview', ''),
                'min_players': game.get('min_players'),
                'max_players': game.get('max_players'),
                'min_playtime': game.get('min_playtime'),
                'max_playtime': game.get('max_playtime'),
                'min_age': game.get('min_age'),
            })
        
        return results
        
    except (requests.exceptions.RequestException, requests.exceptions.ConnectionError, 
            requests.exceptions.Timeout, OSError) as e:
        logger.warning(f"Board Game Atlas API error: {e}")
        logger.info("Returning mock data as fallback")
        # Return mock data as fallback
        return get_mock_data(query)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return get_mock_data(query)


def get_game_details(bga_id):
    """
    Get detailed information about a specific game by its Board Game Atlas ID
    """
    url = f"{BASE_URL}/search"
    
    params = {
        'ids': bga_id,
        'client_id': CLIENT_ID
    }
    
    try:
        logger.info(f"Getting details for BGA ID: {bga_id}")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        games = data.get('games', [])
        
        if games:
            game = games[0]
            return {
                'bga_id': game.get('id'),
                'name': game.get('name'),
                'year': game.get('year_published'),
                'price': game.get('price', '0'),
                'msrp': game.get('msrp', 0),
                'image_url': game.get('image_url'),
                'thumbnail': game.get('thumb_url'),
                'description': game.get('description', ''),
                'description_preview': game.get('description_preview', ''),
                'min_players': game.get('min_players'),
                'max_players': game.get('max_players'),
                'min_playtime': game.get('min_playtime'),
                'max_playtime': game.get('max_playtime'),
                'min_age': game.get('min_age'),
                'official_url': game.get('official_url'),
                'rules_url': game.get('rules_url'),
            }
        
        # If not found in API, check if it's a mock ID
        if str(bga_id).startswith('mock_'):
            logger.info(f"Mock ID detected: {bga_id}, returning mock data")
            mock_games = get_mock_data('')
            for game in mock_games:
                if game['bga_id'] == bga_id:
                    return game
        
        return None
        
    except (requests.exceptions.RequestException, requests.exceptions.ConnectionError,
            requests.exceptions.Timeout, OSError) as e:
        logger.warning(f"Error getting game details: {e}")
        logger.info("Checking if it's a mock ID")
        # Check if it's a mock ID
        if str(bga_id).startswith('mock_'):
            mock_games = get_mock_data('')
            for game in mock_games:
                if game['bga_id'] == bga_id:
                    return game
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting game details: {e}")
        return None


def get_mock_data(query):
    """
    Return mock data when API is unavailable
    """
    mock_games = [
        {
            'bga_id': 'mock_catan',
            'name': 'Catan',
            'year': 1995,
            'price': '44.99',
            'msrp': 49.99,
            'image_url': 'https://s3-us-west-1.amazonaws.com/5cc.images/games/uploaded/1629324722072.jpg',
            'thumbnail': 'https://s3-us-west-1.amazonaws.com/5cc.images/games/uploaded/1629324722072-thumb.jpg',
            'description': 'In CATAN, players try to be the dominant force on the island of Catan by building settlements, cities, and roads.',
            'min_players': 3,
            'max_players': 4,
            'min_playtime': 60,
            'max_playtime': 120,
            'min_age': 10,
        },
        {
            'bga_id': 'mock_ticket',
            'name': 'Ticket to Ride',
            'year': 2004,
            'price': '54.99',
            'msrp': 59.99,
            'image_url': 'https://s3-us-west-1.amazonaws.com/5cc.images/games/uploaded/1629324738308.jpg',
            'thumbnail': 'https://s3-us-west-1.amazonaws.com/5cc.images/games/uploaded/1629324738308-thumb.jpg',
            'description': 'Ticket to Ride is a cross-country train adventure game where players collect cards to claim railway routes.',
            'min_players': 2,
            'max_players': 5,
            'min_playtime': 30,
            'max_playtime': 60,
            'min_age': 8,
        },
        {
            'bga_id': 'mock_pandemic',
            'name': 'Pandemic',
            'year': 2008,
            'price': '39.99',
            'msrp': 44.99,
            'image_url': 'https://s3-us-west-1.amazonaws.com/5cc.images/games/uploaded/1629324760985.jpg',
            'thumbnail': 'https://s3-us-west-1.amazonaws.com/5cc.images/games/uploaded/1629324760985-thumb.jpg',
            'description': 'In Pandemic, several virulent diseases have broken out simultaneously all over the world! Players must work together.',
            'min_players': 2,
            'max_players': 4,
            'min_playtime': 45,
            'max_playtime': 45,
            'min_age': 8,
        }
    ]
    
    # Filter by query
    query_lower = query.lower()
    filtered = [g for g in mock_games if query_lower in g['name'].lower()]
    
    return filtered if filtered else mock_games
