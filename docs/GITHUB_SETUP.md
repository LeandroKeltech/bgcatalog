# 🚀 Deploy BGCatalog no GitHub Pages

## ✅ **Passos Rápidos (5 minutos)**

### **1. Configure sua Planilha Google Sheets**

#### **Passo A: Criar API Key**
1. Acesse: [Google Cloud Console](https://console.developers.google.com)
2. Criar projeto ou selecionar existente
3. **Ativar APIs** → Buscar "Google Sheets API" → Ativar
4. **Credenciais** → Criar credenciais → **Chave da API**
5. Copiar a chave gerada

#### **Passo B: Criar Planilha**
1. Criar nova planilha: [Google Sheets](https://sheets.google.com)
2. **Renomear** primeira aba para: `BGCatalog`
3. **Compartilhar** → Alterar para "Qualquer pessoa com o link"
4. **Copiar ID da planilha** da URL:
   ```
   https://docs.google.com/spreadsheets/d/[ESTE_É_O_ID]/edit
   ```

### **2. Configurar o Código**

Edite o arquivo: `webapp/js/config.js`

```javascript
window.BGCATALOG_CONFIG = {
    SHEETS_API_KEY: 'AIzaSyBPuksi5DhFrpfhUMKdgRk0BlWNerzTKWk',          // ← Cole sua API Key
    SPREADSHEET_ID: '179Ai4uTT0qWcr4O-mLgMDwv4hdRRSD1f50tKmccbqhE',   // ← Cole o ID da planilha
    SHEET_NAME: 'BGCatalog'
};
```

### **3. Ativar GitHub Pages**

1. No seu repositório GitHub, vá em **Settings**
2. Scroll down até **Pages** (lado esquerdo)
3. **Source**: Deploy from a branch
4. **Branch**: `creation` (ou `main`)
5. **Folder**: `/webapp`
6. Clique **Save**

### **4. Acessar sua App**

GitHub vai gerar uma URL:
```
https://SEUUSUARIO.github.io/bgcatalog/
```

**Pronto! 🎉 Seu BGCatalog está online!**

---

## 🛠️ **Configuração Manual (Alternativa)**

Se preferir configurar direto no app (sem mexer no código):

1. Deixe o `config.js` como está (com valores vazios)
2. Acesse o app online
3. Clique **Configurações** (⚙️)
4. Preencha **Google Sheets** 
5. Clique **Testar Conexão** → **Salvar**

---

## 🔧 **Testando Localmente Antes**

```bash
# Navegue até a pasta
cd webapp

# Servidor Python
python -m http.server 8000

# Acesse: http://localhost:8000
```

---

## 📋 **Estrutura da Planilha (Automática)**

O app criará automaticamente estas colunas:

| Title | Category | Condition | Barcode | Ref Price | Price Rule | Final Price | Stock | Sold | Notes | Created | Updated |
|-------|----------|-----------|---------|-----------|------------|-------------|--------|------|-------|---------|---------|

---

## ⚠️ **Troubleshooting**

### **Erro: "API Key inválida"**
- Verifique se ativou a Google Sheets API
- Confirme se copiou a chave completa

### **Erro: "Planilha não encontrada"**
- Certifique-se que a planilha está **pública**
- Verifique o ID na URL (entre `/d/` e `/edit`)

### **Scanner não funciona**
- Use **Chrome** ou **Safari**
- Certifique-se que está em **HTTPS** (GitHub Pages usa HTTPS automático)
- Permita acesso à câmera quando solicitado

### **GitHub Pages não atualiza**
- Pode levar 5-10 minutos para propagar
- Force refresh (Ctrl+F5) no navegador

---

## 🎯 **Exemplo Completo**

```javascript
// Exemplo real no config.js:
window.BGCATALOG_CONFIG = {
    SHEETS_API_KEY: 'AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    SPREADSHEET_ID: '1ABC123def456GHI789jklMNO012pqrSTU345vwxYZ',
    SHEET_NAME: 'BGCatalog',
    APP_NAME: 'Meus Jogos de Tabuleiro'
};
```

**🎲 Agora você tem um catálogo online profissional! 🎲**