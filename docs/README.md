# 🎲 BGCatalog WebApp

**Catálogo de Jogos de Tabuleiro com Scanner de Código de Barras**

Um webapp moderno para catalogar sua coleção de jogos de tabuleiro, com scanner de código de barras via câmera e sincronização com Google Sheets.

## ✨ **Funcionalidades**

- 📱 **Scanner de código de barras** via câmera do celular/computador
- 🎲 **Integração com BoardGameGeek** (BGG) para busca automática
- 📊 **Banco de dados Google Sheets** (sincronização na nuvem)
- 💾 **Funciona offline** (dados salvos localmente)
- 📈 **Estatísticas em tempo real**
- 🔍 **Busca e filtros avançados**
- 💰 **Cálculo automático de preços**
- 📤 **Export/Import** de dados
- 🌟 **PWA** (instalável como app)

## 🚀 **Como Usar**

### **1. Hospedagem Gratuita (GitHub Pages)**

1. **Fork este repositório**
2. **Ative GitHub Pages**:
   - Vá em Settings → Pages
   - Source: Deploy from branch
   - Branch: main → /webapp
3. **Acesse**: `https://SEU_USUARIO.github.io/bgcatalog`

### **2. Hospedagem Local**

```bash
# Opção 1: Abrir diretamente no navegador
# Navegue até a pasta webapp/ e abra index.html

# Opção 2: Servidor local (Python)
cd webapp
python -m http.server 8000
# Acesse: http://localhost:8000

# Opção 3: Servidor local (Node.js)
npx serve webapp
# Acesse: http://localhost:3000
```

### **3. Outras Opções**
- **Netlify**: Arraste a pasta `webapp` no netlify.com
- **Vercel**: Conecte o repositório no vercel.com

## 📊 **Configuração Google Sheets**

### **Passo 1: Criar API Key**

1. Acesse [Google Cloud Console](https://console.developers.google.com)
2. Crie um novo projeto ou selecione existente
3. Ative a **Google Sheets API**
4. Crie credenciais → **API Key**
5. Copie a API Key gerada

### **Passo 2: Criar Planilha**

1. Crie uma nova planilha no [Google Sheets](https://sheets.google.com)
2. Renomeie a primeira aba para `BGCatalog`
3. Torne a planilha **pública** (qualquer pessoa com link pode ver)
4. Copie o ID da planilha da URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   ```

### **Passo 3: Configurar no App**

1. Abra o webapp
2. Clique em **Configurações** (engrenagem)
3. Preencha:
   - **API Key**: Cole sua API Key do Google
   - **ID da Planilha**: Cole o ID copiado
   - **Nome da Aba**: `BGCatalog` (padrão)
4. Clique **Testar Conexão**
5. **Salvar Configuração**

## 📱 **Como Usar o Scanner**

### **No Celular (Chrome/Safari)**
1. Abra o webapp no navegador
2. Clique **+ Adicionar Item**
3. Clique **Scanner** 
4. Permita acesso à câmera
5. Aponte para o código de barras

### **Problemas com Câmera?**
- ✅ Use **Chrome** ou **Safari** (recomendado)
- ✅ Certifique-se que o site está em **HTTPS**
- ✅ Permita acesso à câmera quando solicitado
- ✅ Use o botão **Digitar Manualmente** como alternativa

## 🎯 **Como Funciona**

### **Fluxo de Uso**
1. **Scanner**: Escaneie código de barras de um jogo
2. **BGG**: App busca automaticamente no BoardGameGeek
3. **Seleção**: Clique no jogo para preencher dados
4. **Preço**: Define preço de referência e regra de desconto
5. **Salvar**: Item é salvo local + Google Sheets (se configurado)

### **Sincronização**
- 🔄 **Automática**: Sempre que você adiciona/edita itens
- 🔄 **Manual**: Botão "Sincronizar Agora" nas configurações
- 🔄 **Offline**: Tudo funciona sem internet, sync quando voltar online

### **Estrutura do Google Sheets**
```
| Title | Category | Condition | Barcode | Ref Price | Price Rule | Final Price | Stock | Sold | Notes | Created | Updated |
```

## 🛠️ **Tecnologias Utilizadas**

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Scanner**: QuaggaJS + WebRTC
- **Banco**: Google Sheets API + localStorage
- **BGG**: BoardGameGeek XML API
- **PWA**: Service Worker + Web Manifest

## 📋 **Estrutura de Arquivos**

```
webapp/
├── index.html          # Interface principal
├── css/
│   └── style.css       # Estilos responsivos
├── js/
│   ├── app.js          # Aplicação principal
│   ├── database-sheets.js   # Google Sheets + localStorage
│   ├── scanner.js      # Scanner de código de barras
│   └── bgg-api.js      # Integração BoardGameGeek
├── manifest.json       # PWA manifest
└── sw.js              # Service Worker (offline)
```

## ❗ **Limitações**

### **Google Sheets API (Leitura)**
- ✅ **Funciona**: Ler dados da planilha
- ❌ **Limitação**: Escrever dados requer Apps Script

### **Para Escrita Completa** (Opcional)
Se quiser sincronização bidirecional:
1. Crie um Google Apps Script
2. Publique como Web App
3. Configure URL no localStorage: `bgcatalog_webapp_url`

### **Scanner de Código**
- ✅ **Chrome/Safari**: Funciona perfeitamente
- ⚠️ **Firefox**: Limitações de WebRTC
- ❌ **Apps nativos**: Use entrada manual

## 🔧 **Solução de Problemas**

### **Scanner não funciona**
```javascript
// Abra F12 → Console e verifique:
navigator.mediaDevices.getUserMedia({video: true})
  .then(() => console.log("Câmera OK"))
  .catch(e => console.log("Erro:", e));
```

### **Google Sheets não sincroniza**
1. Verifique se a planilha está pública
2. Confirme a API Key e ID da planilha
3. Use "Testar Conexão" nas configurações

### **App offline**
- Todos os dados ficam salvos localmente
- Sincroniza automaticamente quando voltar online

## 📝 **Licença**

MIT License - Use livremente para projetos pessoais e comerciais.

## 🤝 **Contribuições**

Contribuições são bem-vindas! Abra issues e pull requests.

---

**🎲 Organize sua coleção de jogos como nunca antes! 🎲**