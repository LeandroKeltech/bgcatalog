// ================================
// GOOGLE SHEETS DATABASE MODULE
// ================================

class GoogleSheetsDB {
    constructor() {
        this.sheetsApiKey = ''; // Will be set from settings
        this.spreadsheetId = ''; // Will be set from settings
        this.sheetName = 'BGCatalog';
        this.cache = new Map();
        this.isOnline = navigator.onLine;
        this.localStorageKey = 'bgcatalog_local_data';
        
        // Listen for online/offline status
        window.addEventListener('online', () => {
            this.isOnline = true;
            console.log('App is online');
            this.syncWithSheets();
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
        this.sheetsApiKey = settings.sheetsApiKey || '';
        this.spreadsheetId = settings.spreadsheetId || '';
        this.sheetName = settings.sheetName || 'BGCatalog';
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

    // CRUD Operations (all work offline with local storage)

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
            try {
                await this.updateSheet(items);
            } catch (error) {
                console.warn('Could not sync to Google Sheets:', error);
            }
        }
        
        return newItem;
    }

    // Get all items
    async getAllItems() {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.items);
            const store = transaction.objectStore(this.stores.items);
            const request = store.getAll();
            
            request.onsuccess = () => {
                console.log('Retrieved', request.result.length, 'items');
                resolve(request.result);
            };
            
            request.onerror = () => {
                console.error('Error getting items:', request.error);
                reject(request.error);
            };
        });
    }

    // Get item by ID
    async getItem(id) {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.items);
            const store = transaction.objectStore(this.stores.items);
            const request = store.get(id);
            
            request.onsuccess = () => {
                resolve(request.result);
            };
            
            request.onerror = () => {
                console.error('Error getting item:', request.error);
                reject(request.error);
            };
        });
    }

    // Update item
    async updateItem(item) {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.items, 'readwrite');
            const store = transaction.objectStore(this.stores.items);
            
            // Add updated timestamp
            const updatedItem = {
                ...item,
                updatedAt: new Date().toISOString()
            };
            
            const request = store.put(updatedItem);
            
            request.onsuccess = () => {
                console.log('Item updated:', item.id);
                resolve(updatedItem);
            };
            
            request.onerror = () => {
                console.error('Error updating item:', request.error);
                reject(request.error);
            };
        });
    }

    // Delete item
    async deleteItem(id) {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.items, 'readwrite');
            const store = transaction.objectStore(this.stores.items);
            const request = store.delete(id);
            
            request.onsuccess = () => {
                console.log('Item deleted:', id);
                resolve();
            };
            
            request.onerror = () => {
                console.error('Error deleting item:', request.error);
                reject(request.error);
            };
        });
    }

    // Search items by title or barcode
    async searchItems(query) {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.items);
            const store = transaction.objectStore(this.stores.items);
            const request = store.getAll();
            
            request.onsuccess = () => {
                const allItems = request.result;
                const searchTerm = query.toLowerCase();
                
                const filteredItems = allItems.filter(item => 
                    item.title.toLowerCase().includes(searchTerm) ||
                    (item.barcode && item.barcode.includes(searchTerm)) ||
                    item.category.toLowerCase().includes(searchTerm) ||
                    (item.notes && item.notes.toLowerCase().includes(searchTerm))
                );
                
                console.log('Search results:', filteredItems.length, 'items found');
                resolve(filteredItems);
            };
            
            request.onerror = () => {
                console.error('Error searching items:', request.error);
                reject(request.error);
            };
        });
    }

    // Get items by category
    async getItemsByCategory(category) {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.items);
            const store = transaction.objectStore(this.stores.items);
            const index = store.index('category');
            const request = index.getAll(category);
            
            request.onsuccess = () => {
                console.log('Items by category:', category, request.result.length);
                resolve(request.result);
            };
            
            request.onerror = () => {
                console.error('Error getting items by category:', request.error);
                reject(request.error);
            };
        });
    }

    // Get statistics
    async getStatistics() {
        try {
            const items = await this.getAllItems();
            
            const stats = {
                totalItems: items.length,
                totalValue: items.reduce((sum, item) => sum + (item.finalPrice * item.stock), 0),
                totalSold: items.reduce((sum, item) => sum + (item.sold || 0), 0),
                totalStock: items.reduce((sum, item) => sum + item.stock, 0),
                categories: {},
                conditions: {},
                averagePrice: 0
            };

            // Calculate category distribution
            items.forEach(item => {
                stats.categories[item.category] = (stats.categories[item.category] || 0) + 1;
                stats.conditions[item.condition] = (stats.conditions[item.condition] || 0) + 1;
            });

            // Calculate average price
            if (items.length > 0) {
                stats.averagePrice = items.reduce((sum, item) => sum + item.finalPrice, 0) / items.length;
            }

            return stats;
        } catch (error) {
            console.error('Error getting statistics:', error);
            throw error;
        }
    }

    // SETTINGS OPERATIONS

    // Save setting
    async saveSetting(key, value) {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.settings, 'readwrite');
            const store = transaction.objectStore(this.stores.settings);
            
            const setting = {
                key,
                value,
                updatedAt: new Date().toISOString()
            };
            
            const request = store.put(setting);
            
            request.onsuccess = () => {
                console.log('Setting saved:', key);
                resolve();
            };
            
            request.onerror = () => {
                console.error('Error saving setting:', request.error);
                reject(request.error);
            };
        });
    }

    // Get setting
    async getSetting(key, defaultValue = null) {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.settings);
            const store = transaction.objectStore(this.stores.settings);
            const request = store.get(key);
            
            request.onsuccess = () => {
                const result = request.result;
                resolve(result ? result.value : defaultValue);
            };
            
            request.onerror = () => {
                console.error('Error getting setting:', request.error);
                reject(request.error);
            };
        });
    }

    // Get all settings
    async getAllSettings() {
        return new Promise((resolve, reject) => {
            const transaction = this.getTransaction(this.stores.settings);
            const store = transaction.objectStore(this.stores.settings);
            const request = store.getAll();
            
            request.onsuccess = () => {
                const settings = {};
                request.result.forEach(setting => {
                    settings[setting.key] = setting.value;
                });
                resolve(settings);
            };
            
            request.onerror = () => {
                console.error('Error getting all settings:', request.error);
                reject(request.error);
            };
        });
    }

    // BACKUP AND RESTORE

    // Export all data
    async exportData() {
        try {
            const [items, settings] = await Promise.all([
                this.getAllItems(),
                this.getAllSettings()
            ]);
            
            return {
                version: this.dbVersion,
                exportDate: new Date().toISOString(),
                items,
                settings
            };
        } catch (error) {
            console.error('Error exporting data:', error);
            throw error;
        }
    }

    // Import data (replaces existing data)
    async importData(data) {
        try {
            // Clear existing data
            await this.clearAllData();
            
            // Import items
            if (data.items && Array.isArray(data.items)) {
                for (const item of data.items) {
                    // Remove ID to let IndexedDB generate new ones
                    const { id, ...itemData } = item;
                    await this.addItem(itemData);
                }
            }
            
            // Import settings
            if (data.settings && typeof data.settings === 'object') {
                for (const [key, value] of Object.entries(data.settings)) {
                    await this.saveSetting(key, value);
                }
            }
            
            console.log('Data imported successfully');
            return true;
        } catch (error) {
            console.error('Error importing data:', error);
            throw error;
        }
    }

    // Clear all data
    async clearAllData() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.items, this.stores.settings], 'readwrite');
            
            let completed = 0;
            const total = 2;
            
            const checkComplete = () => {
                completed++;
                if (completed === total) {
                    console.log('All data cleared');
                    resolve();
                }
            };
            
            // Clear items
            const itemsStore = transaction.objectStore(this.stores.items);
            const clearItemsRequest = itemsStore.clear();
            clearItemsRequest.onsuccess = checkComplete;
            clearItemsRequest.onerror = () => reject(clearItemsRequest.error);
            
            // Clear settings
            const settingsStore = transaction.objectStore(this.stores.settings);
            const clearSettingsRequest = settingsStore.clear();
            clearSettingsRequest.onsuccess = checkComplete;
            clearSettingsRequest.onerror = () => reject(clearSettingsRequest.error);
        });
    }

    // Close database connection
    close() {
        if (this.db) {
            this.db.close();
            this.db = null;
            console.log('Database connection closed');
        }
    }
}

// Export singleton instance
const database = new Database();

// Initialize database when module loads
database.init().catch(error => {
    console.error('Failed to initialize database:', error);
    // Fallback to localStorage if IndexedDB fails
    console.warn('Falling back to localStorage');
});