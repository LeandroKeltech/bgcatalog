# Configuração do Sistema de Carrinho e Área Administrativa

## 🎯 Funcionalidades Implementadas

### 1. **Catálogo Público** (para visitantes)
- ✅ Visualização de jogos disponíveis
- ✅ Botão "Add to Cart" em cada jogo
- ✅ Carrinho de compras funcional

### 2. **Carrinho de Compras**
- ✅ Adicionar jogos ao carrinho
- ✅ Atualizar quantidades
- ✅ Remover itens
- ✅ Formulário para enviar pedido por email
- ✅ Email enviado para: popperl@gmail.com

### 3. **Área Administrativa** (protegida por senha)
- ✅ Login: `/admin-login/`
- ✅ Painel administrativo: `/admin-panel/`
- ✅ Gerenciamento completo de jogos
- ✅ Estatísticas do catálogo
- ✅ Filtros e buscas

## 🔐 Credenciais de Acesso

**Usuário Admin:**
- Username: `admin`
- Senha: `bgpeterleandro`
- Email: popperl@gmail.com

## 📋 Passos para Ativar

### 1. Fazer Migrações do Banco de Dados

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Criar Usuário Administrativo

```bash
python manage.py shell < create_admin.py
```

Ou manualmente:
```bash
python manage.py createsuperuser
```

### 3. Configurar Email (IMPORTANTE!)

Adicione as seguintes variáveis de ambiente no Fly.io:

```bash
flyctl secrets set EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend" -a bgcatalog
flyctl secrets set EMAIL_HOST="smtp.gmail.com" -a bgcatalog
flyctl secrets set EMAIL_PORT="587" -a bgcatalog
flyctl secrets set EMAIL_USE_TLS="True" -a bgcatalog
flyctl secrets set EMAIL_HOST_USER="popperl@gmail.com" -a bgcatalog
flyctl secrets set EMAIL_HOST_PASSWORD="sua_senha_app_gmail" -a bgcatalog
```

**Importante:** Para usar Gmail, você precisa criar uma "Senha de App":
1. Acesse: https://myaccount.google.com/security
2. Ative a verificação em 2 etapas
3. Vá em "Senhas de app"
4. Crie uma senha para "Mail"
5. Use essa senha no `EMAIL_HOST_PASSWORD`

## 🚀 Fazer Deploy

```bash
git add .
git commit -m "Add shopping cart and admin panel"
git push
```

O GitHub Actions fará o deploy automaticamente!

## 📧 Como Funciona o Carrinho

1. **Cliente navega** pelo catálogo em `/public/`
2. **Adiciona jogos** ao carrinho clicando em "Add to Cart"
3. **Acessa o carrinho** em `/cart/`
4. **Preenche formulário** com:
   - Nome
   - Email
   - Telefone (opcional)
   - Mensagem (opcional)
5. **Clica em "Enviar Solicitação"**
6. **Email é enviado** para popperl@gmail.com com:
   - Dados do cliente
   - Lista de jogos solicitados
   - Quantidades e preços
   - Total do pedido

## 🔧 URLs do Sistema

| Função | URL | Acesso |
|--------|-----|--------|
| Catálogo Público | `/public/` | Todos |
| Carrinho | `/cart/` | Todos |
| Login Admin | `/admin-login/` | Todos |
| Painel Admin | `/admin-panel/` | Apenas autenticados |
| Adicionar Jogo | `/bgg/search/` | Apenas admin |
| Editar Jogo | `/game/<id>/edit/` | Apenas admin |

## ✅ Checklist de Deploy

- [ ] Fazer migrações: `python manage.py makemigrations && python manage.py migrate`
- [ ] Criar usuário admin: `python manage.py shell < create_admin.py`
- [ ] Configurar variáveis de email no Fly.io
- [ ] Fazer commit e push
- [ ] Testar carrinho no site
- [ ] Testar login administrativo
- [ ] Verificar recebimento de emails

## 🎨 Personalização

### Trocar Email de Destino

Edite em `settings.py`:
```python
ADMIN_EMAIL = 'seu_novo_email@example.com'
```

### Trocar Senha Admin

```bash
python manage.py changepassword admin
```

## 🐛 Problemas Comuns

### Email não está sendo enviado

1. Verifique se as variáveis de ambiente estão configuradas no Fly.io
2. Confirme que usou uma "Senha de App" do Gmail (não a senha normal)
3. Verifique os logs: `flyctl logs -a bgcatalog`

### Não consigo fazer login

1. Certifique-se de que o usuário admin foi criado
2. Use: Username: `admin`, Senha: `bgpeterleandro`
3. Se esqueceu a senha: `python manage.py changepassword admin`

### Carrinho vazio após adicionar itens

1. Verifique se o session middleware está habilitado
2. Limpe cookies do navegador
3. Verifique se há erros no console do navegador

## 📱 Testando Localmente

```bash
# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt

# Fazer migrações
python manage.py migrate

# Criar admin
python manage.py shell < create_admin.py

# Rodar servidor
python manage.py runserver

# Acessar:
# - Catálogo: http://localhost:8000/public/
# - Carrinho: http://localhost:8000/cart/
# - Admin: http://localhost:8000/admin-login/
```
