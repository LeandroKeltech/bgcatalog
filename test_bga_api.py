"""
Test Board Game Atlas API
"""
import requests

# Board Game Atlas API
# Você precisa criar uma conta grátis em: https://www.boardgameatlas.com/api/docs
# E pegar sua Client ID
CLIENT_ID = "JM0HZBu3g2"  # Client ID público de teste

def test_board_game_atlas():
    print("Testing Board Game Atlas API...")
    url = "https://api.boardgameatlas.com/api/search"
    
    params = {
        'name': 'Catan',
        'client_id': CLIENT_ID,
        'limit': 3
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nFound {len(data.get('games', []))} games")
            
            for game in data.get('games', [])[:1]:
                print(f"\nGame: {game.get('name')}")
                print(f"Year: {game.get('year_published')}")
                print(f"Price: ${game.get('price', 'N/A')}")
                print(f"MSRP: ${game.get('msrp', 'N/A')}")
                print(f"Image: {game.get('image_url', 'N/A')[:50]}...")
                print(f"Description: {game.get('description_preview', 'N/A')[:100]}...")
                
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_board_game_atlas()
