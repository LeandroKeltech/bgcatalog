// Global variables
let items = [];
let settings = {
    scriptUrl: '',
    imageQuality: 80
};

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    showItems();
    console.log('App initialized');
});

// Camera Scanner Variables
let scannerActive = false;
let videoStream = null;

// Barcode Scanner Functions
async function startBarcodeScanner() {
    try {
        // Show scanner modal
        document.getElementById('scanner-modal').classList.remove('hidden');
        
        // Get camera access
        videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'environment', // Use back camera
                width: { ideal: 1280 },
                height: { ideal: 720 }
            } 
        });
        
        const video = document.getElementById('scanner-video');
        video.srcObject = videoStream;
        
        // Initialize Quagga scanner
        initQuaggaScanner();
        
    } catch (error) {
        console.error('Camera access error:', error);
        alert('Cannot access camera. Please check permissions or use manual input.');
        stopBarcodeScanner();
        openBarcodeInput();
    }
}

function initQuaggaScanner() {
    Quagga.init({
        inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector('#scanner-video'),
            constraints: {
                width: 640,
                height: 480,
                facingMode: "environment"
            }
        },
        decoder: {
            readers: [
                "code_128_reader",
                "ean_reader",
                "ean_8_reader",
                "code_39_reader",
                "code_39_vin_reader",
                "codabar_reader",
                "upc_reader",
                "upc_e_reader",
                "i2of5_reader"
            ]
        },
        locate: true,
        locator: {
            patchSize: "medium",
            halfSample: true
        }
    }, function(err) {
        if (err) {
            console.error('Quagga init error:', err);
            alert('Scanner initialization failed. Using manual input.');
            stopBarcodeScanner();
            openBarcodeInput();
            return;
        }
        
        console.log("Quagga initialization finished. Ready to start");
        Quagga.start();
        scannerActive = true;
        
        // Listen for barcode detection
        Quagga.onDetected(onBarcodeDetected);
    });
}

function onBarcodeDetected(result) {
    const code = result.codeResult.code;
    console.log('Barcode detected:', code);
    
    // Stop scanner and process result
    stopBarcodeScanner();
    handleBarcodeResult(code);
    
    // Show success feedback
    alert('Barcode scanned: ' + code);
}

function stopBarcodeScanner() {
    // Hide modal
    document.getElementById('scanner-modal').classList.add('hidden');
    
    // Stop Quagga
    if (scannerActive) {
        Quagga.stop();
        scannerActive = false;
    }
    
    // Stop video stream
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
}

function toggleFlash() {
    if (videoStream) {
        const track = videoStream.getVideoTracks()[0];
        const capabilities = track.getCapabilities();
        
        if (capabilities.torch) {
            const settings = track.getSettings();
            track.applyConstraints({
                advanced: [{ torch: !settings.torch }]
            });
        } else {
            alert('Flash not supported on this device');
        }
    }
}

function openBarcodeInput() {
    const barcode = prompt('Enter the barcode number manually:');
    if (barcode && barcode.trim()) {
        handleBarcodeResult(barcode.trim());
    }
}

function scanBarcode() {
    startBarcodeScanner();
}

function handleBarcodeResult(barcode) {
    document.getElementById('barcode').value = barcode;
    onBarcodeInput(barcode);
}

function onBarcodeInput(barcode) {
    const searchBtn = document.getElementById('bgg-search-btn');
    
    if (barcode && barcode.length >= 8) {
        searchBtn.disabled = false;
        // Auto-search BGG if it looks like a valid barcode
        if (barcode.length >= 12) {
            setTimeout(() => searchBGG(), 500); // Small delay for better UX
        }
    } else {
        searchBtn.disabled = true;
        document.getElementById('bgg-results').classList.add('hidden');
    }
}

// BGG API Functions
async function searchBGG() {
    const barcode = document.getElementById('barcode').value;
    
    if (!barcode) {
        alert('Please scan or enter a barcode first');
        return;
    }

    showLoading(true);
    document.getElementById('bgg-results').classList.add('hidden');

    try {
        // First try to search by barcode in BGG database
        let games = await searchBGGByBarcode(barcode);
        
        // If no results, try searching by UPC/EAN
        if (games.length === 0) {
            games = await searchBGGByUPC(barcode);
        }

        showLoading(false);
        displayBGGResults(games);
        
    } catch (error) {
        showLoading(false);
        console.error('BGG search error:', error);
        alert('Error searching BGG: ' + error.message);
    }
}

async function searchBGGByBarcode(barcode) {
    // For now, simulate BGG search with mock data
    // In a real implementation, you'd need a CORS proxy or server-side API
    return new Promise((resolve) => {
        setTimeout(() => {
            // Mock results based on common barcodes
            const mockResults = [
                { id: '1', name: 'Catan', year: '1995' },
                { id: '2', name: 'Ticket to Ride', year: '2004' },
                { id: '3', name: 'Splendor', year: '2014' }
            ];
            
            // Return mock result if barcode looks valid
            if (barcode.length >= 10) {
                resolve([mockResults[0]]); // Return first game as example
            } else {
                resolve([]);
            }
        }, 1000);
    });
}

async function searchBGGByUPC(upc) {
    return searchBGGByBarcode(upc);
}

function parseBGGXML(xmlText) {
    // Simplified parsing - in production would implement full BGG XML parsing
    return [];
}

function showLoading(show) {
    const loading = document.getElementById('bgg-loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

function displayBGGResults(games) {
    const resultsDiv = document.getElementById('bgg-results');
    
    if (games.length === 0) {
        resultsDiv.innerHTML = '<p>No board games found with this barcode. You can still add the item manually.</p>';
        resultsDiv.classList.remove('hidden');
        return;
    }

    const gamesHtml = games.map(game => `
        <div class="bgg-game" onclick="selectBGGGame('${game.name}', '${game.year}')">
            <div class="bgg-game-name">${game.name}</div>
            <div class="bgg-game-year">${game.year ? '(' + game.year + ')' : ''}</div>
        </div>
    `).join('');

    resultsDiv.innerHTML = `
        <p><strong>Found ${games.length} game(s):</strong></p>
        ${gamesHtml}
        <p style="font-size: 12px; margin-top: 10px; color: #666;">Tap a game to auto-fill the form</p>
    `;
    resultsDiv.classList.remove('hidden');
}

function selectBGGGame(name, year) {
    document.getElementById('title').value = name + (year ? ' (' + year + ')' : '');
    document.getElementById('category').value = 'boardgame';
    
    // Hide results
    document.getElementById('bgg-results').classList.add('hidden');
    
    // Focus on next field
    document.getElementById('condition').focus();
    
    alert('Game info loaded! Please fill in the remaining details.');
}

// Screen navigation
function showScreen(screenId) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.add('hidden');
    });
    
    // Show selected screen
    document.getElementById(screenId).classList.remove('hidden');
    
    // Update screen content
    if (screenId === 'home-screen') showItems();
    if (screenId === 'review') showReviewItems();
    if (screenId === 'inventory') showInventoryItems();
}

// Item management
function saveItem() {
    const title = document.getElementById('title').value;
    const category = document.getElementById('category').value;
    const condition = document.getElementById('condition').value;
    const refPrice = parseFloat(document.getElementById('reference-price').value);
    const priceRule = parseInt(document.getElementById('price-rule').value);
    const finalPrice = parseFloat(document.getElementById('final-price').value);
    const stock = parseInt(document.getElementById('stock').value);
    const sold = parseInt(document.getElementById('sold').value) || 0;
    const notes = document.getElementById('notes').value;

    if (!title || !category || !condition || !refPrice || !finalPrice || !stock) {
        alert('Please fill all required fields');
        return;
    }

    const item = {
        id: Date.now(),
        title,
        category,
        condition,
        referencePrice: refPrice,
        priceRule,
        finalPrice,
        stock,
        sold,
        notes,
        createdAt: new Date().toISOString()
    };

    items.push(item);
    saveData();
    clearForm();
    showScreen('home-screen');
    alert('Item saved successfully!');
}

function clearForm() {
    document.getElementById('barcode').value = '';
    document.getElementById('title').value = '';
    document.getElementById('category').value = '';
    document.getElementById('condition').value = '';
    document.getElementById('reference-price').value = '';
    document.getElementById('price-rule').value = '-50';
    document.getElementById('final-price').value = '';
    document.getElementById('stock').value = '';
    document.getElementById('sold').value = '0';
    document.getElementById('notes').value = '';
    
    // Reset BGG search
    document.getElementById('bgg-search-btn').disabled = true;
    document.getElementById('bgg-results').classList.add('hidden');
    document.getElementById('bgg-loading').classList.add('hidden');
}

function showItems() {
    const itemsList = document.getElementById('items-list');
    
    if (items.length === 0) {
        itemsList.innerHTML = '<div class="empty-state">No items added yet. Tap + to add your first item!</div>';
        return;
    }

    itemsList.innerHTML = items.map(item => `
        <div class="item-card">
            <div class="item-title">${item.title}</div>
            <div class="item-details">
                ${item.category} • ${item.condition} • €${item.finalPrice}<br>
                Stock: ${item.stock} | Sold: ${item.sold}
            </div>
        </div>
    `).join('');
}

function showReviewItems() {
    const reviewList = document.getElementById('review-list');
    const reviewItems = items.filter(item => item.stock > 0);
    
    if (reviewItems.length === 0) {
        reviewList.innerHTML = '<div class="empty-state">No items to review</div>';
        return;
    }

    reviewList.innerHTML = reviewItems.map(item => `
        <div class="item-card">
            <div class="item-title">${item.title}</div>
            <div class="item-details">
                Price: €${item.referencePrice} → €${item.finalPrice}<br>
                Available: ${item.stock - item.sold} units
            </div>
        </div>
    `).join('');
}

function showInventoryItems() {
    const inventoryList = document.getElementById('inventory-list');
    
    if (items.length === 0) {
        inventoryList.innerHTML = '<div class="empty-state">No inventory items</div>';
        return;
    }

    const totalValue = items.reduce((sum, item) => sum + (item.finalPrice * item.stock), 0);
    
    inventoryList.innerHTML = `
        <div class="item-card">
            <div class="item-title">Total Inventory Value</div>
            <div class="item-details">€${totalValue.toFixed(2)}</div>
        </div>
        ${items.map(item => `
            <div class="item-card">
                <div class="item-title">${item.title}</div>
                <div class="item-details">
                    Stock: ${item.stock} | Value: €${(item.finalPrice * item.stock).toFixed(2)}
                </div>
            </div>
        `).join('')}
    `;
}

function filterItems(searchText) {
    const itemsList = document.getElementById('items-list');
    
    if (!searchText.trim()) {
        showItems();
        return;
    }
    
    const filteredItems = items.filter(item => 
        item.title.toLowerCase().includes(searchText.toLowerCase()) ||
        item.category.toLowerCase().includes(searchText.toLowerCase()) ||
        (item.barcode && item.barcode.includes(searchText))
    );
    
    if (filteredItems.length === 0) {
        itemsList.innerHTML = '<div class="empty-state">No items match your search</div>';
        return;
    }

    itemsList.innerHTML = filteredItems.map(item => `
        <div class="item-card">
            <div class="item-title">${item.title}</div>
            <div class="item-details">
                ${item.category} • ${item.condition} • €${item.finalPrice}<br>
                Stock: ${item.stock} | Sold: ${item.sold}
            </div>
        </div>
    `).join('');
}

// Export/Import functions
function exportToSheets() {
    if (!settings.scriptUrl) {
        alert('Please set Google Apps Script URL in settings first');
        return;
    }
    
    // This would export to Google Sheets
    alert('Export to Google Sheets functionality - coming soon!');
}

function exportToJSON() {
    const dataStr = JSON.stringify(items, null, 2);
    const dataBlob = new Blob([dataStr], {type:'application/json'});
    
    // Create download link
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bgcatalog-export.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    // Show status
    const status = document.getElementById('export-status');
    status.textContent = `Exported ${items.length} items to JSON file`;
    status.style.display = 'block';
    setTimeout(() => status.style.display = 'none', 3000);
}

function importFromJSON() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const importedItems = JSON.parse(e.target.result);
                    
                    if (Array.isArray(importedItems)) {
                        items = importedItems;
                        saveData();
                        showItems();
                        
                        const status = document.getElementById('export-status');
                        status.textContent = `Imported ${items.length} items successfully!`;
                        status.style.display = 'block';
                        setTimeout(() => status.style.display = 'none', 3000);
                    } else {
                        alert('Invalid JSON format');
                    }
                } catch (error) {
                    alert('Error reading file: ' + error.message);
                }
            };
            reader.readAsText(file);
        }
    };
    
    input.click();
}

// Settings
function saveSettings() {
    settings.scriptUrl = document.getElementById('script-url').value;
    settings.imageQuality = parseInt(document.getElementById('image-quality').value);
    
    localStorage.setItem('bgcatalog_settings', JSON.stringify(settings));
    alert('Settings saved!');
    showScreen('home-screen');
}

// Data persistence
function saveData() {
    localStorage.setItem('bgcatalog_items', JSON.stringify(items));
}

function loadData() {
    const savedItems = localStorage.getItem('bgcatalog_items');
    if (savedItems) {
        items = JSON.parse(savedItems);
    }
    
    const savedSettings = localStorage.getItem('bgcatalog_settings');
    if (savedSettings) {
        settings = JSON.parse(savedSettings);
        document.getElementById('script-url').value = settings.scriptUrl || '';
        document.getElementById('image-quality').value = settings.imageQuality || 80;
    }
}