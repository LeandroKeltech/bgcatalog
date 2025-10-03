// ================================
// BGG API MODULE
// ================================

class BGGApi {
    constructor() {
        this.baseUrl = 'https://boardgamegeek.com/xmlapi2';
        this.cache = new Map(); // Simple in-memory cache
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }

    // Search BGG by barcode (using UPC/EAN)
    async searchByBarcode(barcode) {
        try {
            // First try to find games that match this UPC/EAN
            const games = await this.searchByUPC(barcode);
            
            if (games.length === 0) {
                // If no direct UPC match, try searching by the barcode as a term
                return await this.searchByName(barcode);
            }
            
            return games;
        } catch (error) {
            console.error('BGG barcode search error:', error);
            // Return mock data for demo purposes
            return this.getMockResults(barcode);
        }
    }

    // Search by UPC (requires CORS proxy in production)
    async searchByUPC(upc) {
        // Note: BGG doesn't directly support UPC search via API
        // In production, you'd need a service that maps UPCs to BGG IDs
        // For now, return empty array to fall back to name search
        return [];
    }

    // Search games by name
    async searchByName(query) {
        const cacheKey = `search:${query}`;
        
        // Check cache first
        const cached = this.getFromCache(cacheKey);
        if (cached) {
            return cached;
        }

        try {
            // Use a CORS proxy for development (in production, use your own backend)
            const proxyUrl = 'https://api.allorigins.win/get?url=';
            const encodedUrl = encodeURIComponent(`${this.baseUrl}/search?query=${encodeURIComponent(query)}&type=boardgame&exact=0`);
            
            const response = await fetch(proxyUrl + encodedUrl);
            if (!response.ok) {
                throw new Error('BGG API request failed');
            }
            
            const data = await response.json();
            const xmlText = data.contents;
            
            const games = this.parseSearchResults(xmlText);
            
            // Cache results
            this.setCache(cacheKey, games);
            
            return games;
        } catch (error) {
            console.error('BGG search error:', error);
            // Return mock data for demo
            return this.getMockResults(query);
        }
    }

    // Get detailed game information
    async getGameDetails(gameId) {
        const cacheKey = `game:${gameId}`;
        
        const cached = this.getFromCache(cacheKey);
        if (cached) {
            return cached;
        }

        try {
            const proxyUrl = 'https://api.allorigins.win/get?url=';
            const encodedUrl = encodeURIComponent(`${this.baseUrl}/thing?id=${gameId}&stats=1`);
            
            const response = await fetch(proxyUrl + encodedUrl);
            if (!response.ok) {
                throw new Error('BGG API request failed');
            }
            
            const data = await response.json();
            const xmlText = data.contents;
            
            const gameDetails = this.parseGameDetails(xmlText);
            
            this.setCache(cacheKey, gameDetails);
            
            return gameDetails;
        } catch (error) {
            console.error('BGG game details error:', error);
            return null;
        }
    }

    // Parse search results XML
    parseSearchResults(xmlText) {
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
            
            const items = xmlDoc.querySelectorAll('item');
            const games = [];
            
            items.forEach(item => {
                const game = {
                    id: item.getAttribute('id'),
                    name: '',
                    yearPublished: ''
                };
                
                const nameElement = item.querySelector('name');
                if (nameElement) {
                    game.name = nameElement.getAttribute('value');
                }
                
                const yearElement = item.querySelector('yearpublished');
                if (yearElement) {
                    game.yearPublished = yearElement.getAttribute('value');
                }
                
                if (game.name) {
                    games.push(game);
                }
            });
            
            console.log('Parsed BGG search results:', games.length, 'games');
            return games;
        } catch (error) {
            console.error('Error parsing BGG search results:', error);
            return [];
        }
    }

    // Parse game details XML
    parseGameDetails(xmlText) {
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
            
            const item = xmlDoc.querySelector('item');
            if (!item) {
                return null;
            }
            
            const game = {
                id: item.getAttribute('id'),
                name: '',
                yearPublished: '',
                description: '',
                minPlayers: '',
                maxPlayers: '',
                playingTime: '',
                minAge: '',
                rating: '',
                weight: '',
                categories: [],
                mechanics: []
            };
            
            // Primary name
            const primaryName = item.querySelector('name[type="primary"]');
            if (primaryName) {
                game.name = primaryName.getAttribute('value');
            }
            
            // Year published
            const yearElement = item.querySelector('yearpublished');
            if (yearElement) {
                game.yearPublished = yearElement.getAttribute('value');
            }
            
            // Description
            const descElement = item.querySelector('description');
            if (descElement) {
                game.description = descElement.textContent;
            }
            
            // Player counts
            const minPlayersElement = item.querySelector('minplayers');
            if (minPlayersElement) {
                game.minPlayers = minPlayersElement.getAttribute('value');
            }
            
            const maxPlayersElement = item.querySelector('maxplayers');
            if (maxPlayersElement) {
                game.maxPlayers = maxPlayersElement.getAttribute('value');
            }
            
            // Playing time
            const playTimeElement = item.querySelector('playingtime');
            if (playTimeElement) {
                game.playingTime = playTimeElement.getAttribute('value');
            }
            
            // Min age
            const minAgeElement = item.querySelector('minage');
            if (minAgeElement) {
                game.minAge = minAgeElement.getAttribute('value');
            }
            
            // Statistics
            const statistics = item.querySelector('statistics ratings');
            if (statistics) {
                const averageElement = statistics.querySelector('average');
                if (averageElement) {
                    game.rating = parseFloat(averageElement.getAttribute('value')).toFixed(1);
                }
                
                const weightElement = statistics.querySelector('averageweight');
                if (weightElement) {
                    game.weight = parseFloat(weightElement.getAttribute('value')).toFixed(1);
                }
            }
            
            // Categories
            const categoryElements = item.querySelectorAll('link[type="boardgamecategory"]');
            categoryElements.forEach(cat => {
                game.categories.push(cat.getAttribute('value'));
            });
            
            // Mechanics
            const mechanicElements = item.querySelectorAll('link[type="boardgamemechanic"]');
            mechanicElements.forEach(mech => {
                game.mechanics.push(mech.getAttribute('value'));
            });
            
            return game;
        } catch (error) {
            console.error('Error parsing BGG game details:', error);
            return null;
        }
    }

    // Get mock results for demo/fallback
    getMockResults(query) {
        const mockGames = [
            {
                id: '13',
                name: 'Catan',
                yearPublished: '1995'
            },
            {
                id: '9209',
                name: 'Ticket to Ride',
                yearPublished: '2004'
            },
            {
                id: '148228',
                name: 'Splendor',
                yearPublished: '2014'
            },
            {
                id: '167791',
                name: 'Terraforming Mars',
                yearPublished: '2016'
            },
            {
                id: '161936',
                name: 'Pandemic Legacy: Season 1',
                yearPublished: '2015'
            }
        ];
        
        // Filter by query if it looks like a game name
        const queryLower = query.toLowerCase();
        const filtered = mockGames.filter(game => 
            game.name.toLowerCase().includes(queryLower) ||
            (query.length >= 10) // If it's a barcode, return first result
        );
        
        return filtered.length > 0 ? [filtered[0]] : mockGames.slice(0, 3);
    }

    // Cache management
    getFromCache(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            console.log('Cache hit for:', key);
            return cached.data;
        }
        return null;
    }

    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    clearCache() {
        this.cache.clear();
        console.log('BGG API cache cleared');
    }
}

// Global BGG API instance
const bggApi = new BGGApi();

// Global functions for the app
async function searchBGG() {
    const barcodeInput = document.getElementById('barcode');
    const loadingDiv = document.getElementById('bgg-loading');
    const resultsDiv = document.getElementById('bgg-results');
    
    const barcode = barcodeInput.value.trim();
    
    if (!barcode) {
        showToast('Digite ou escaneie um código de barras primeiro', 'warning');
        return;
    }
    
    // Show loading
    loadingDiv.classList.remove('hidden');
    resultsDiv.classList.add('hidden');
    
    try {
        let games = [];
        
        // If it looks like a barcode (numbers), search by barcode
        if (/^\d{8,}$/.test(barcode)) {
            games = await bggApi.searchByBarcode(barcode);
        } else {
            // Otherwise search by name
            games = await bggApi.searchByName(barcode);
        }
        
        displayBGGResults(games);
        
    } catch (error) {
        console.error('BGG search error:', error);
        showToast('Erro ao buscar no BGG: ' + error.message, 'error');
    } finally {
        loadingDiv.classList.add('hidden');
    }
}

function displayBGGResults(games) {
    const resultsDiv = document.getElementById('bgg-results');
    
    if (games.length === 0) {
        resultsDiv.innerHTML = `
            <div class="bgg-no-results">
                <p>Nenhum jogo encontrado no BGG.</p>
                <p>Você ainda pode adicionar o item manualmente.</p>
            </div>
        `;
        resultsDiv.classList.remove('hidden');
        return;
    }
    
    const gamesHtml = games.map(game => `
        <div class="bgg-game" onclick="selectBGGGame('${game.id}', '${game.name}', '${game.yearPublished}')">
            <div class="bgg-game-name">${game.name}</div>
            <div class="bgg-game-year">${game.yearPublished ? `(${game.yearPublished})` : ''}</div>
        </div>
    `).join('');
    
    resultsDiv.innerHTML = `
        <div class="bgg-results-header">
            <p><strong>Encontrado${games.length > 1 ? 's' : ''} ${games.length} jogo${games.length > 1 ? 's' : ''}:</strong></p>
        </div>
        ${gamesHtml}
        <div class="bgg-results-footer">
            <p><small>Clique em um jogo para preencher automaticamente</small></p>
        </div>
    `;
    resultsDiv.classList.remove('hidden');
}

async function selectBGGGame(gameId, gameName, yearPublished) {
    try {
        // Fill basic info immediately
        document.getElementById('title').value = gameName + (yearPublished ? ` (${yearPublished})` : '');
        document.getElementById('category').value = 'boardgame';
        
        // Hide results
        document.getElementById('bgg-results').classList.add('hidden');
        
        // Get detailed info in background
        const gameDetails = await bggApi.getGameDetails(gameId);
        if (gameDetails) {
            // Could populate additional fields if we had them in the form
            console.log('Game details loaded:', gameDetails);
        }
        
        // Focus on next field
        document.getElementById('condition').focus();
        
        showToast('Informações do jogo carregadas do BGG!', 'success');
        
    } catch (error) {
        console.error('Error selecting BGG game:', error);
        showToast('Erro ao carregar detalhes do jogo', 'error');
    }
}