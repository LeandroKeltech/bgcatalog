// ================================
// CONFIGURAÇÃO GOOGLE SHEETS
// ================================

// 🔧 CONFIGURE AQUI SUA PLANILHA PADRÃO:

window.BGCATALOG_CONFIG = {
    // Google Sheets API Key
    // 1. Acesse: https://console.developers.google.com
    // 2. Crie/selecione um projeto
    // 3. Ative "Google Sheets API"
    // 4. Crie credenciais → API Key
    // 5. Cole aqui:
    SHEETS_API_KEY: 'SUA_API_KEY_AQUI',
    
    // ID da Planilha Google Sheets
    // 1. Crie uma planilha no Google Sheets
    // 2. Torne-a pública (compartilhar → qualquer um com link pode ver)
    // 3. Copie o ID da URL: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
    // 4. Cole aqui:
    SPREADSHEET_ID: 'SEU_SPREADSHEET_ID_AQUI',
    
    // Nome da aba na planilha (opcional)
    SHEET_NAME: 'BGCatalog',
    
    // Configurações do App
    APP_NAME: 'BGCatalog',
    APP_VERSION: '1.0.0',
    
    // Configurações do Scanner
    SCANNER_ENABLED: true,
    
    // Configurações do BGG
    BGG_SEARCH_ENABLED: true,
    BGG_MOCK_DATA: true // Usar dados simulados se a API falhar
};

// ================================
// EXEMPLOS DE CONFIGURAÇÃO
// ================================

/*
// Exemplo 1: Configuração Completa
window.BGCATALOG_CONFIG = {
    SHEETS_API_KEY: 'AIzaSyB1234567890abcdefghijklmnop',
    SPREADSHEET_ID: '1ABC123xyz789_example_spreadsheet_id',
    SHEET_NAME: 'BGCatalog',
    APP_NAME: 'Meus Jogos',
    BGG_SEARCH_ENABLED: true
};

// Exemplo 2: Só Local (sem Google Sheets)
window.BGCATALOG_CONFIG = {
    SHEETS_API_KEY: '',
    SPREADSHEET_ID: '',
    SCANNER_ENABLED: true,
    BGG_SEARCH_ENABLED: false
};
*/