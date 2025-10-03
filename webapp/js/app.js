// ================================
// MAIN APP MODULE
// ================================

class BGCatalogApp {
    constructor() {
        this.currentItems = [];
        this.filteredItems = [];
        this.currentEditingId = null;
        this.searchTimeout = null;
    }

    // Initialize the application
    async init() {
        try {
            // Initialize database
            await database.init();
            console.log('Database initialized');

            // Load initial data
            await this.loadItems();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Update UI
            await this.updateStats();
            this.renderItems();
            
            // Hide loading screen and show app
            setTimeout(() => {
                document.getElementById('loading-screen').classList.add('hidden');
                document.getElementById('app').classList.remove('hidden');
            }, 1000);
            
            console.log('BGCatalog app initialized successfully');
            
        } catch (error) {
            console.error('App initialization failed:', error);
            showToast('Erro ao inicializar o aplicativo', 'error');
        }
    }

    // Set up event listeners
    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('search-input');
        searchInput.addEventListener('input', (e) => {
            this.handleSearch(e.target.value);
        });

        // Category filter
        const categoryFilter = document.getElementById('category-filter');
        categoryFilter.addEventListener('change', () => {
            this.applyFilters();
        });

        // Item form submission
        const itemForm = document.getElementById('item-form');
        itemForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveItem();
        });

        // Barcode input
        const barcodeInput = document.getElementById('barcode');
        barcodeInput.addEventListener('input', (e) => {
            this.onBarcodeInput(e.target.value);
        });

        // Price calculation
        const refPriceInput = document.getElementById('reference-price');
        const priceRuleInput = document.getElementById('price-rule');
        
        refPriceInput.addEventListener('input', () => this.calculateFinalPrice());
        priceRuleInput.addEventListener('input', () => this.calculateFinalPrice());

        // Close modals on background click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeAllModals();
                }
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // ESC to close modals
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
            // Ctrl+N to add new item
            if (e.ctrlKey && e.key === 'n') {
                e.preventDefault();
                this.showAddItem();
            }
        });

        console.log('Event listeners set up');
    }

    // Load items from database
    async loadItems() {
        try {
            this.currentItems = await database.getAllItems();
            this.filteredItems = [...this.currentItems];
            console.log('Loaded', this.currentItems.length, 'items');
        } catch (error) {
            console.error('Error loading items:', error);
            this.currentItems = [];
            this.filteredItems = [];
        }
    }

    // Update statistics
    async updateStats() {
        try {
            const stats = await database.getStatistics();
            
            document.getElementById('total-items').textContent = stats.totalItems;
            document.getElementById('total-value').textContent = `€${stats.totalValue.toFixed(2)}`;
            document.getElementById('total-sold').textContent = stats.totalSold;
            
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }

    // Render items list
    renderItems() {
        const itemsList = document.getElementById('items-list');
        const emptyState = document.getElementById('empty-state');
        
        if (this.filteredItems.length === 0) {
            itemsList.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }
        
        emptyState.classList.add('hidden');
        
        itemsList.innerHTML = this.filteredItems.map(item => `
            <div class="item-card" onclick="app.showItemDetails(${item.id})">
                <div class="item-header">
                    <div>
                        <div class="item-title">${this.escapeHtml(item.title)}</div>
                        <span class="item-category">${this.getCategoryLabel(item.category)}</span>
                    </div>
                </div>
                
                <div class="item-details">
                    <div class="item-detail">
                        <div class="item-detail-label">Condição</div>
                        <div class="item-detail-value">${this.getConditionLabel(item.condition)}</div>
                    </div>
                    <div class="item-detail">
                        <div class="item-detail-label">Preço</div>
                        <div class="item-detail-value">€${item.finalPrice.toFixed(2)}</div>
                    </div>
                    <div class="item-detail">
                        <div class="item-detail-label">Estoque</div>
                        <div class="item-detail-value">${item.stock}</div>
                    </div>
                    <div class="item-detail">
                        <div class="item-detail-label">Vendidos</div>
                        <div class="item-detail-value">${item.sold || 0}</div>
                    </div>
                </div>
                
                <div class="item-actions">
                    <button class="btn-secondary" onclick="event.stopPropagation(); app.editItem(${item.id})">
                        <span class="material-icons">edit</span>
                        Editar
                    </button>
                    <button class="btn-danger" onclick="event.stopPropagation(); app.deleteItem(${item.id})">
                        <span class="material-icons">delete</span>
                        Excluir
                    </button>
                </div>
            </div>
        `).join('');
    }

    // Handle search input
    handleSearch(query) {
        // Debounce search
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch(query);
        }, 300);
    }

    // Perform search
    async performSearch(query) {
        if (!query.trim()) {
            this.filteredItems = [...this.currentItems];
            this.applyFilters();
            return;
        }

        try {
            this.filteredItems = await database.searchItems(query);
            this.applyFilters();
        } catch (error) {
            console.error('Search error:', error);
            showToast('Erro na busca', 'error');
        }
    }

    // Apply filters
    applyFilters() {
        const categoryFilter = document.getElementById('category-filter').value;
        
        if (categoryFilter) {
            this.filteredItems = this.filteredItems.filter(item => 
                item.category === categoryFilter
            );
        }
        
        this.renderItems();
    }

    // Show add item modal
    showAddItem() {
        this.currentEditingId = null;
        document.getElementById('modal-title').textContent = 'Novo Item';
        this.clearForm();
        document.getElementById('item-modal').classList.add('active');
        document.getElementById('title').focus();
    }

    // Show edit item modal
    async editItem(id) {
        try {
            const item = await database.getItem(id);
            if (!item) {
                showToast('Item não encontrado', 'error');
                return;
            }
            
            this.currentEditingId = id;
            document.getElementById('modal-title').textContent = 'Editar Item';
            this.fillForm(item);
            document.getElementById('item-modal').classList.add('active');
        } catch (error) {
            console.error('Error editing item:', error);
            showToast('Erro ao carregar item', 'error');
        }
    }

    // Show item details (future feature)
    showItemDetails(id) {
        console.log('Show item details:', id);
        // Future: implement item details view
    }

    // Delete item
    async deleteItem(id) {
        if (!confirm('Tem certeza que deseja excluir este item?')) {
            return;
        }
        
        try {
            await database.deleteItem(id);
            await this.loadItems();
            await this.updateStats();
            this.renderItems();
            showToast('Item excluído com sucesso', 'success');
        } catch (error) {
            console.error('Error deleting item:', error);
            showToast('Erro ao excluir item', 'error');
        }
    }

    // Save item (add or update)
    async saveItem() {
        try {
            const formData = this.getFormData();
            
            if (!this.validateForm(formData)) {
                return;
            }
            
            if (this.currentEditingId) {
                // Update existing item
                formData.id = this.currentEditingId;
                await database.updateItem(formData);
                showToast('Item atualizado com sucesso', 'success');
            } else {
                // Add new item
                await database.addItem(formData);
                showToast('Item adicionado com sucesso', 'success');
            }
            
            // Refresh data and UI
            await this.loadItems();
            await this.updateStats();
            this.renderItems();
            this.closeItemModal();
            
        } catch (error) {
            console.error('Error saving item:', error);
            showToast('Erro ao salvar item', 'error');
        }
    }

    // Get form data
    getFormData() {
        return {
            barcode: document.getElementById('barcode').value.trim(),
            title: document.getElementById('title').value.trim(),
            category: document.getElementById('category').value,
            condition: document.getElementById('condition').value,
            referencePrice: parseFloat(document.getElementById('reference-price').value) || 0,
            priceRule: parseInt(document.getElementById('price-rule').value) || 0,
            finalPrice: parseFloat(document.getElementById('final-price').value) || 0,
            stock: parseInt(document.getElementById('stock').value) || 0,
            sold: parseInt(document.getElementById('sold').value) || 0,
            notes: document.getElementById('notes').value.trim()
        };
    }

    // Validate form
    validateForm(data) {
        if (!data.title) {
            showToast('Título é obrigatório', 'warning');
            document.getElementById('title').focus();
            return false;
        }
        
        if (!data.category) {
            showToast('Categoria é obrigatória', 'warning');
            document.getElementById('category').focus();
            return false;
        }
        
        if (!data.condition) {
            showToast('Condição é obrigatória', 'warning');
            document.getElementById('condition').focus();
            return false;
        }
        
        if (data.referencePrice <= 0) {
            showToast('Preço de referência deve ser maior que zero', 'warning');
            document.getElementById('reference-price').focus();
            return false;
        }
        
        if (data.finalPrice <= 0) {
            showToast('Preço final deve ser maior que zero', 'warning');
            document.getElementById('final-price').focus();
            return false;
        }
        
        if (data.stock < 0) {
            showToast('Estoque não pode ser negativo', 'warning');
            document.getElementById('stock').focus();
            return false;
        }
        
        return true;
    }

    // Fill form with item data
    fillForm(item) {
        document.getElementById('barcode').value = item.barcode || '';
        document.getElementById('title').value = item.title || '';
        document.getElementById('category').value = item.category || '';
        document.getElementById('condition').value = item.condition || '';
        document.getElementById('reference-price').value = item.referencePrice || '';
        document.getElementById('price-rule').value = item.priceRule || -50;
        document.getElementById('final-price').value = item.finalPrice || '';
        document.getElementById('stock').value = item.stock || '';
        document.getElementById('sold').value = item.sold || 0;
        document.getElementById('notes').value = item.notes || '';
        
        this.onBarcodeInput(item.barcode || '');
    }

    // Clear form
    clearForm() {
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
        
        // Reset BGG elements
        document.getElementById('bgg-search-btn').disabled = true;
        document.getElementById('bgg-results').classList.add('hidden');
        document.getElementById('bgg-loading').classList.add('hidden');
    }

    // Handle barcode input
    onBarcodeInput(barcode) {
        const searchBtn = document.getElementById('bgg-search-btn');
        
        if (barcode && barcode.length >= 8) {
            searchBtn.disabled = false;
        } else {
            searchBtn.disabled = true;
            document.getElementById('bgg-results').classList.add('hidden');
        }
    }

    // Calculate final price based on reference price and rule
    calculateFinalPrice() {
        const refPrice = parseFloat(document.getElementById('reference-price').value) || 0;
        const priceRule = parseInt(document.getElementById('price-rule').value) || 0;
        
        if (refPrice > 0) {
            const finalPrice = refPrice * (1 + priceRule / 100);
            document.getElementById('final-price').value = Math.max(0, finalPrice).toFixed(2);
        }
    }

    // Close item modal
    closeItemModal() {
        document.getElementById('item-modal').classList.remove('active');
        this.currentEditingId = null;
    }

    // Show settings modal
    async showSettings() {
        document.getElementById('settings-modal').classList.add('active');
        await this.loadSettingsForm();
        this.updateSyncStatus();
    }

    // Load settings into form
    async loadSettingsForm() {
        try {
            const settings = await database.getAllSettings();
            
            document.getElementById('sheets-api-key').value = settings.sheetsApiKey || '';
            document.getElementById('spreadsheet-id').value = settings.spreadsheetId || '';
            document.getElementById('sheet-name').value = settings.sheetName || 'BGCatalog';
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    // Update sync status display
    updateSyncStatus() {
        const status = database.getSyncStatus();
        
        // Online status
        const onlineEl = document.getElementById('sync-online-status');
        if (status.isOnline) {
            onlineEl.textContent = status.isConfigured ? 'Online - Configurado' : 'Online - Não Configurado';
            onlineEl.className = 'sync-value ' + (status.isConfigured ? 'configured' : 'not-configured');
        } else {
            onlineEl.textContent = 'Offline';
            onlineEl.className = 'sync-value offline';
        }
        
        // Last sync
        const lastSyncEl = document.getElementById('sync-last-time');
        if (status.lastSync) {
            const date = new Date(status.lastSync);
            lastSyncEl.textContent = date.toLocaleString('pt-BR');
        } else {
            lastSyncEl.textContent = 'Nunca';
        }
        
        // Items count
        document.getElementById('sync-items-count').textContent = status.itemsCount;
    }

    // Close settings modal
    closeSettings() {
        document.getElementById('settings-modal').classList.remove('active');
    }

    // Close all modals
    closeAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('active');
        });
        barcodeScanner.stopScanning();
    }

    // Export data
    async exportData() {
        try {
            const data = await database.exportData();
            const dataStr = JSON.stringify(data, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `bgcatalog-export-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            showToast('Dados exportados com sucesso', 'success');
        } catch (error) {
            console.error('Export error:', error);
            showToast('Erro ao exportar dados', 'error');
        }
    }

    // Import data
    async importData() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (file) {
                try {
                    const text = await file.text();
                    const data = JSON.parse(text);
                    
                    if (!confirm('Isso substituirá todos os dados existentes. Continuar?')) {
                        return;
                    }
                    
                    await database.importData(data);
                    
                    // Refresh app
                    await this.loadItems();
                    await this.updateStats();
                    this.renderItems();
                    
                    showToast('Dados importados com sucesso', 'success');
                } catch (error) {
                    console.error('Import error:', error);
                    showToast('Erro ao importar dados: ' + error.message, 'error');
                }
            }
        };
        
        input.click();
    }

    // Clear all data
    async clearAllData() {
        if (!confirm('Isso excluirá TODOS os dados permanentemente. Tem certeza?')) {
            return;
        }
        
        if (!confirm('Esta ação não pode ser desfeita. Continuar mesmo assim?')) {
            return;
        }
        
        try {
            await database.clearAllData();
            await this.loadItems();
            await this.updateStats();
            this.renderItems();
            showToast('Todos os dados foram excluídos', 'success');
        } catch (error) {
            console.error('Clear data error:', error);
            showToast('Erro ao limpar dados', 'error');
        }
    }

    // Utility methods
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }

    getCategoryLabel(category) {
        const labels = {
            boardgame: 'Jogo de Tabuleiro',
            furniture: 'Móveis',
            kitchen: 'Cozinha',
            others: 'Outros'
        };
        return labels[category] || category;
    }

    getConditionLabel(condition) {
        const labels = {
            new: 'Novo',
            good: 'Bom',
            acceptable: 'Aceitável',
            poor: 'Ruim'
        };
        return labels[condition] || condition;
    }
}

// ================================
// TOAST NOTIFICATIONS
// ================================

function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = {
        success: 'check_circle',
        error: 'error',
        warning: 'warning',
        info: 'info'
    }[type] || 'info';
    
    toast.innerHTML = `
        <span class="material-icons">${icon}</span>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto remove
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, duration);
}

// ================================
// GLOBAL FUNCTIONS FOR HTML
// ================================

function showAddItem() {
    app.showAddItem();
}

function showSettings() {
    app.showSettings();
}

function closeItemModal() {
    app.closeItemModal();
}

function closeSettings() {
    app.closeSettings();
}

function calculateFinalPrice() {
    app.calculateFinalPrice();
}

function handleSearch(query) {
    app.handleSearch(query);
}

function applyFilters() {
    app.applyFilters();
}

function exportData() {
    app.exportData();
}

function importData() {
    app.importData();
}

function clearAllData() {
    app.clearAllData();
}

// Google Sheets Configuration Functions
async function saveGoogleSheetsConfig() {
    try {
        const settings = {
            sheetsApiKey: document.getElementById('sheets-api-key').value.trim(),
            spreadsheetId: document.getElementById('spreadsheet-id').value.trim(),
            sheetName: document.getElementById('sheet-name').value.trim() || 'BGCatalog'
        };
        
        if (!settings.sheetsApiKey || !settings.spreadsheetId) {
            showToast('Por favor, preencha a API Key e o ID da planilha', 'warning');
            return;
        }
        
        await database.saveSettings(settings);
        showToast('Configuração do Google Sheets salva!', 'success');
        
        // Update sync status
        app.updateSyncStatus();
        
    } catch (error) {
        console.error('Error saving Google Sheets config:', error);
        showToast('Erro ao salvar configuração', 'error');
    }
}

async function testGoogleSheets() {
    const statusEl = document.getElementById('sheets-status');
    statusEl.innerHTML = '<span class="material-icons spinning">refresh</span> Testando conexão...';
    statusEl.className = 'sync-status';
    
    try {
        const apiKey = document.getElementById('sheets-api-key').value.trim();
        const spreadsheetId = document.getElementById('spreadsheet-id').value.trim();
        
        if (!apiKey || !spreadsheetId) {
            throw new Error('Preencha a API Key e o ID da planilha');
        }
        
        // Test the connection
        const url = `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}?key=${apiKey}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Erro da API: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        statusEl.innerHTML = `✅ Conexão bem-sucedida! Planilha: "${data.properties.title}"`;
        statusEl.className = 'sync-status success';
        
        showToast('Conexão com Google Sheets funcionando!', 'success');
        
    } catch (error) {
        console.error('Google Sheets test error:', error);
        statusEl.innerHTML = `❌ Erro: ${error.message}`;
        statusEl.className = 'sync-status error';
        showToast('Erro na conexão: ' + error.message, 'error');
    }
}

async function manualSync() {
    try {
        showToast('Sincronizando...', 'info');
        await database.manualSync();
        
        // Refresh app data
        await app.loadItems();
        await app.updateStats();
        app.renderItems();
        app.updateSyncStatus();
        
        showToast('Sincronização concluída!', 'success');
    } catch (error) {
        console.error('Manual sync error:', error);
        showToast('Erro na sincronização: ' + error.message, 'error');
    }
}

// Handle barcode result from scanner
function handleBarcodeResult(barcode) {
    document.getElementById('barcode').value = barcode;
    app.onBarcodeInput(barcode);
}

// ================================
// APP INITIALIZATION
// ================================

// Global app instance
const app = new BGCatalogApp();

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing BGCatalog...');
    app.init();
});

// Handle app lifecycle
window.addEventListener('beforeunload', () => {
    // Close database connection
    if (database) {
        database.close();
    }
});