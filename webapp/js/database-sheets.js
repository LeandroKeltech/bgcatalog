// ================================
// GOOGLE SHEETS DATABASE MODULE
// ================================

class GoogleSheetsDB {
    constructor() {
        // Get default configuration from config.js
        const config = window.BGCATALOG_CONFIG || {};
        
        // 🔧 CONFIGURAÇÃO PADRÃO (vem do config.js):
        this.defaultSheetsApiKey = config.SHEETS_API_KEY || '';
        this.defaultSpreadsheetId = config.SPREADSHEET_ID || '';
        this.defaultSheetName = config.SHEET_NAME || 'BGCatalog';
        
        // Configurações dinâmicas (sobrescreve os padrões se existir)
        this.sheetsApiKey = '';
        this.spreadsheetId = '';
        this.sheetName = this.defaultSheetName;
        this.cache = new Map();
        this.isOnline = navigator.onLine;
        this.localStorageKey = 'bgcatalog_local_data';
        
        // Listen for online/offline status
        window.addEventListener('online', () => {
            this.isOnline = true;
            console.log('App is online');
            this.syncWithSheets().catch(console.warn);
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            console.log('App is offline');
        });
    }

    // Initialize database
    async init() {
        console.log('Initializing Google Sheets database...');
        
        // Load settings
        await this.loadSettings();
        
        // Load local data first (for offline capability)
        this.loadLocalData();
        
        // Try to sync with Google Sheets if online and configured
        if (this.isOnline && this.isConfigured()) {
            try {
                await this.syncWithSheets();
            } catch (error) {
                console.warn('Could not sync with Google Sheets:', error);
            }
        }
        
        console.log('Database initialized successfully');
    }

    // Check if Google Sheets is properly configured
    isConfigured() {
        return this.sheetsApiKey && this.spreadsheetId;
    }

    // Load settings from localStorage
    async loadSettings() {
        const settings = JSON.parse(localStorage.getItem('bgcatalog_settings') || '{}');
        
        // Use user settings if available, otherwise use defaults
        this.sheetsApiKey = settings.sheetsApiKey || this.defaultSheetsApiKey;
        this.spreadsheetId = settings.spreadsheetId || this.defaultSpreadsheetId;
        this.sheetName = settings.sheetName || this.defaultSheetName;
        
        // Log configuration status
        if (this.defaultSheetsApiKey && this.defaultSpreadsheetId) {
            if (this.sheetsApiKey === this.defaultSheetsApiKey && this.spreadsheetId === this.defaultSpreadsheetId) {
                console.log('✅ Usando configuração padrão do Google Sheets');
            } else if (this.isConfigured()) {
                console.log('✅ Usando configuração personalizada do Google Sheets');
            }
        } else if (this.isConfigured()) {
            console.log('✅ Google Sheets configurado via settings');
        } else {
            console.log('⚠️ Google Sheets não configurado - funcionando apenas offline');
        }
    }

    // Save settings to localStorage
    async saveSettings(settings) {
        const currentSettings = JSON.parse(localStorage.getItem('bgcatalog_settings') || '{}');
        const newSettings = { ...currentSettings, ...settings };
        localStorage.setItem('bgcatalog_settings', JSON.stringify(newSettings));
        
        // Update instance variables
        this.sheetsApiKey = newSettings.sheetsApiKey || '';
        this.spreadsheetId = newSettings.spreadsheetId || '';
        this.sheetName = newSettings.sheetName || 'BGCatalog';
    }

    // Load data from localStorage
    loadLocalData() {
        try {
            const localData = localStorage.getItem(this.localStorageKey);
            if (localData) {
                const data = JSON.parse(localData);
                this.cache.set('items', data.items || []);
                console.log('Loaded', (data.items || []).length, 'items from local storage');
            } else {
                this.cache.set('items', []);
            }
        } catch (error) {
            console.error('Error loading local data:', error);
            this.cache.set('items', []);
        }
    }

    // Save data to localStorage
    saveLocalData() {
        try {
            const data = {
                items: this.cache.get('items') || [],
                lastSync: new Date().toISOString()
            };
            localStorage.setItem(this.localStorageKey, JSON.stringify(data));
        } catch (error) {
            console.error('Error saving local data:', error);
        }
    }

    // Sync with Google Sheets
    async syncWithSheets() {
        if (!this.isConfigured() || !this.isOnline) {
            console.log('Skipping sync - not configured or offline');
            return;
        }

        try {
            console.log('Syncing with Google Sheets...');
            
            // Get data from Google Sheets
            const sheetData = await this.getSheetData();
            
            if (sheetData && sheetData.length > 0) {
                // Convert sheet rows to items
                const items = this.parseSheetData(sheetData);
                this.cache.set('items', items);
                this.saveLocalData();
                console.log('Synced', items.length, 'items from Google Sheets');
            }
        } catch (error) {
            console.error('Sync error:', error);
            throw error;
        }
    }

    // Get data from Google Sheets
    async getSheetData() {
        const url = `https://sheets.googleapis.com/v4/spreadsheets/${this.spreadsheetId}/values/${this.sheetName}?key=${this.sheetsApiKey}`;
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Google Sheets API error: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        return data.values || [];
    }

    // Parse sheet data into items
    parseSheetData(sheetData) {
        if (sheetData.length <= 1) return []; // No data or just headers
        
        const items = [];
        
        for (let i = 1; i < sheetData.length; i++) {
            const row = sheetData[i];
            const item = {
                id: Date.now() + i, // Generate local ID
                title: row[0] || '',
                category: row[1] || '',
                condition: row[2] || '',
                barcode: row[3] || '',
                referencePrice: parseFloat(row[4]) || 0,
                priceRule: parseInt(row[5]) || 0,
                finalPrice: parseFloat(row[6]) || 0,
                stock: parseInt(row[7]) || 0,
                sold: parseInt(row[8]) || 0,
                notes: row[9] || '',
                createdAt: row[10] || new Date().toISOString(),
                updatedAt: row[11] || new Date().toISOString()
            };
            
            if (item.title) { // Only add if has title
                items.push(item);
            }
        }
        
        return items;
    }

    // Convert items to sheet format
    itemsToSheetData(items) {
        const headers = [
            'Title', 'Category', 'Condition', 'Barcode', 
            'Reference Price', 'Price Rule', 'Final Price', 
            'Stock', 'Sold', 'Notes', 'Created At', 'Updated At'
        ];
        
        const rows = [headers];
        
        items.forEach(item => {
            rows.push([
                item.title || '',
                item.category || '',
                item.condition || '',
                item.barcode || '',
                item.referencePrice || 0,
                item.priceRule || 0,
                item.finalPrice || 0,
                item.stock || 0,
                item.sold || 0,
                item.notes || '',
                item.createdAt || '',
                item.updatedAt || ''
            ]);
        });
        
        return rows;
    }

    // Update Google Sheets with current data (requires Apps Script)
    async updateSheet(items) {
        if (!this.isConfigured() || !this.isOnline) {
            console.log('Cannot update sheet - not configured or offline');
            return;
        }

        try {
            const sheetData = this.itemsToSheetData(items);
            
            // Use Google Apps Script Web App URL for writing
            // This requires setting up an Apps Script that accepts POST requests
            const webAppUrl = localStorage.getItem('bgcatalog_webapp_url');
            
            if (!webAppUrl) {
                console.log('No Web App URL configured for writing to sheets');
                return;
            }

            const response = await fetch(webAppUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: 'updateSheet',
                    data: sheetData
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to update Google Sheets: ${response.status}`);
            }
            
            console.log('Google Sheets updated successfully');
        } catch (error) {
            console.error('Error updating Google Sheets:', error);
            // Don't throw error - just log it so app continues to work offline
        }
    }

    // CRUD Operations (all work offline with local storage)

    async getAllItems() {
        return this.cache.get('items') || [];
    }

    async addItem(item) {
        const items = this.cache.get('items') || [];
        const newItem = {
            ...item,
            id: Date.now(),
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        
        items.push(newItem);
        this.cache.set('items', items);
        this.saveLocalData();
        
        // Try to sync with Google Sheets in background
        if (this.isOnline && this.isConfigured()) {
            this.updateSheet(items).catch(console.warn);
        }
        
        return newItem;
    }

    async getItem(id) {
        const items = this.cache.get('items') || [];
        return items.find(item => item.id === id);
    }

    async updateItem(updatedItem) {
        const items = this.cache.get('items') || [];
        const index = items.findIndex(item => item.id === updatedItem.id);
        
        if (index === -1) {
            throw new Error('Item not found');
        }
        
        items[index] = {
            ...updatedItem,
            updatedAt: new Date().toISOString()
        };
        
        this.cache.set('items', items);
        this.saveLocalData();
        
        // Try to sync with Google Sheets
        if (this.isOnline && this.isConfigured()) {
            this.updateSheet(items).catch(console.warn);
        }
        
        return items[index];
    }

    async deleteItem(id) {
        const items = this.cache.get('items') || [];
        const filteredItems = items.filter(item => item.id !== id);
        
        this.cache.set('items', filteredItems);
        this.saveLocalData();
        
        // Try to sync with Google Sheets
        if (this.isOnline && this.isConfigured()) {
            this.updateSheet(filteredItems).catch(console.warn);
        }
    }

    async searchItems(query) {
        const items = this.cache.get('items') || [];
        const searchTerm = query.toLowerCase();
        
        return items.filter(item => 
            item.title.toLowerCase().includes(searchTerm) ||
            (item.barcode && item.barcode.includes(searchTerm)) ||
            item.category.toLowerCase().includes(searchTerm) ||
            (item.notes && item.notes.toLowerCase().includes(searchTerm))
        );
    }

    async getItemsByCategory(category) {
        const items = this.cache.get('items') || [];
        return items.filter(item => item.category === category);
    }

    async getStatistics() {
        const items = this.cache.get('items') || [];
        
        return {
            totalItems: items.length,
            totalValue: items.reduce((sum, item) => sum + (item.finalPrice * item.stock), 0),
            totalSold: items.reduce((sum, item) => sum + (item.sold || 0), 0),
            totalStock: items.reduce((sum, item) => sum + item.stock, 0),
            categories: items.reduce((acc, item) => {
                acc[item.category] = (acc[item.category] || 0) + 1;
                return acc;
            }, {}),
            conditions: items.reduce((acc, item) => {
                acc[item.condition] = (acc[item.condition] || 0) + 1;
                return acc;
            }, {}),
            averagePrice: items.length > 0 ? items.reduce((sum, item) => sum + item.finalPrice, 0) / items.length : 0
        };
    }

    // Export/Import for backup
    async exportData() {
        return {
            items: this.cache.get('items') || [],
            exportDate: new Date().toISOString(),
            source: 'BGCatalog Google Sheets Integration'
        };
    }

    async importData(data) {
        if (data.items && Array.isArray(data.items)) {
            // Regenerate IDs to avoid conflicts
            const items = data.items.map((item, index) => ({
                ...item,
                id: Date.now() + index,
                updatedAt: new Date().toISOString()
            }));
            
            this.cache.set('items', items);
            this.saveLocalData();
            
            // Try to sync with Google Sheets
            if (this.isOnline && this.isConfigured()) {
                this.updateSheet(items).catch(console.warn);
            }
        }
    }

    async clearAllData() {
        this.cache.set('items', []);
        this.saveLocalData();
        
        // Clear Google Sheets too
        if (this.isOnline && this.isConfigured()) {
            this.updateSheet([]).catch(console.warn);
        }
    }

    // Manual sync function
    async manualSync() {
        if (!this.isOnline) {
            throw new Error('Não é possível sincronizar offline');
        }
        
        if (!this.isConfigured()) {
            throw new Error('Google Sheets não configurado');
        }
        
        await this.syncWithSheets();
        return true;
    }

    // Get sync status
    getSyncStatus() {
        const localData = JSON.parse(localStorage.getItem(this.localStorageKey) || '{}');
        return {
            isOnline: this.isOnline,
            isConfigured: this.isConfigured(),
            lastSync: localData.lastSync || null,
            itemsCount: (this.cache.get('items') || []).length
        };
    }

    // Compatibility methods (keep same interface as IndexedDB version)
    async saveSetting(key, value) {
        const settings = { [key]: value };
        await this.saveSettings(settings);
    }

    async getSetting(key, defaultValue = null) {
        const settings = JSON.parse(localStorage.getItem('bgcatalog_settings') || '{}');
        return settings[key] !== undefined ? settings[key] : defaultValue;
    }

    async getAllSettings() {
        return JSON.parse(localStorage.getItem('bgcatalog_settings') || '{}');
    }

    close() {
        // No need to close anything for this implementation
        console.log('Database connection closed');
    }
}

// Export singleton instance
const database = new GoogleSheetsDB();