# BGG API Examples & Testing 🎲

Quick reference for testing BoardGameGeek API integration.

## Testing BGG Search in Python Shell

```bash
python manage.py shell
```

Then run:

```python
from catalog.bgg_service import BGGService

# Search for games
results = BGGService.search_games("Catan")
for game in results:
    print(f"{game['id']}: {game['name']} ({game['year']})")

# Get game details
details = BGGService.get_game_details(13)  # Catan BGG ID
print(details['name'])
print(details['designer'])
print(details['year_published'])
print(details['images'])

# Search and get details in one call
games = BGGService.search_and_get_details("Ticket to Ride", limit=3)
for game in games:
    print(f"{game['name']} - {game['year_published']}")
```

## Popular Games to Test

| Game Name | BGG ID | Use Case |
|-----------|--------|----------|
| Catan | 13 | Simple game with good data |
| Ticket to Ride | 9209 | Multiple versions |
| Pandemic | 30549 | Popular modern game |
| Azul | 230802 | Recent game (2017) |
| Wingspan | 266192 | Complex data |
| Gloomhaven | 174430 | Heavy game |
| Codenames | 178900 | Party game |

## Test Searches

```python
# Good searches that should work:
BGGService.search_games("Catan")
BGGService.search_games("Pandemic")
BGGService.search_games("Ticket")  # Partial name
BGGService.search_games("Azul")

# Searches with multiple results:
BGGService.search_games("Pandemic")  # Returns multiple versions
BGGService.search_games("Carcassonne")  # Many expansions
```

## Example: Add Game Programmatically

```python
from catalog.models import BoardGame
from catalog.bgg_service import BGGService

# Fetch from BGG
game_data = BGGService.get_game_details(13)  # Catan

# Create game
game = BoardGame(
    bgg_id=game_data['bgg_id'],
    name=game_data['name'],
    description=game_data['description'],
    year_published=game_data['year_published'],
    designer=game_data['designer'],
    min_players=game_data['min_players'],
    max_players=game_data['max_players'],
    min_playtime=game_data['min_playtime'],
    max_playtime=game_data['max_playtime'],
    min_age=game_data['min_age'],
    thumbnail_url=game_data['thumbnail_url'],
    condition='used',
    msrp_price=50.00,
    stock_quantity=1
)
game.set_images_list(game_data['images'])
game.save()

print(f"Added: {game.name}")
print(f"Final Price: ${game.final_price}")
```

## BGG API Response Structure

### Search Response
```xml
<items total="1">
    <item type="boardgame" id="13">
        <name type="primary" value="Catan"/>
        <yearpublished value="1995"/>
    </item>
</items>
```

### Game Details Response
```xml
<items>
    <item type="boardgame" id="13">
        <thumbnail>https://...</thumbnail>
        <image>https://...</image>
        <name type="primary" value="Catan"/>
        <description>Players try to be...</description>
        <yearpublished value="1995"/>
        <minplayers value="3"/>
        <maxplayers value="4"/>
        <minplaytime value="60"/>
        <maxplaytime value="120"/>
        <minage value="10"/>
        <link type="boardgamedesigner" id="11" value="Klaus Teuber"/>
        <link type="boardgamecategory" id="1021" value="Economic"/>
        <statistics>
            <ratings>
                <average value="7.1"/>
                <averageweight value="2.3"/>
            </ratings>
        </statistics>
    </item>
</items>
```

## Error Handling

```python
try:
    results = BGGService.search_games("NonexistentGame123")
    if not results:
        print("No games found")
except Exception as e:
    print(f"Error: {e}")

try:
    details = BGGService.get_game_details(999999999)
    if not details:
        print("Game not found")
except Exception as e:
    print(f"Error: {e}")
```

## Performance Notes

- BGG API can be slow (5-30 seconds)
- Rate limiting: Wait 1 second between requests
- Search returns max 10-20 results
- Some games may not have all data
- Images are hotlinked from BGG
- MSRP prices not available from BGG (must be set manually)

## Useful BGG Links

- API Documentation: https://boardgamegeek.com/wiki/page/BGG_XML_API2
- Game Page Format: https://boardgamegeek.com/boardgame/{ID}
- Search on BGG: https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q={query}

## Testing Checklist

- [ ] Search returns results for popular games
- [ ] Game details load correctly
- [ ] Images display properly
- [ ] All game data fields populate
- [ ] Partial name search works
- [ ] Error handling works for invalid games
- [ ] Multiple results display correctly
- [ ] Game can be added to database
- [ ] Discount calculates correctly
- [ ] Final price shows properly

---

Happy Testing! 🧪
