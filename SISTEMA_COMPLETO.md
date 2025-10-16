# 🎮 Board Game Catalog - Sistema Completo

## ✨ O que foi implementado

### 1. **Catálogo Público** (Site Principal)
- URL: https://bgcatalog.fly.dev/public/
- ✅ Visitantes podem ver todos os jogos disponíveis
- ✅ Botão "Add to Cart" em cada jogo
- ✅ Design responsivo e atraente

### 2. **Carrinho de Compras**
- URL: https://bgcatalog.fly.dev/cart/
- ✅ Adicionar jogos ao carrinho
- ✅ Alterar quantidades
- ✅ Remover itens
- ✅ Formulário para solicitar orçamento

### 3. **Sistema de Email**
- ✅ Quando o cliente finaliza o pedido no carrinho, um email é enviado para: **popperl@gmail.com**
- ✅ Email contém:
  - Nome, email e telefone do cliente
  - Lista completa de jogos solicitados
  - Quantidades e preços
  - Total do pedido
  - Mensagem do cliente

### 4. **Área Administrativa**
- URL: https://bgcatalog.fly.dev/admin-login/
- ✅ Login protegido por senha
- ✅ Painel completo de gerenciamento
- ✅ Estatísticas do catálogo
- ✅ Adicionar, editar e remover jogos
- ✅ Marcar jogos como vendidos
- ✅ Filtros e buscas avançadas

## 🔐 Credenciais de Acesso Administrativo

**Para acessar a área administrativa:**
- URL: https://bgcatalog.fly.dev/admin-login/
- **Username:** `admin`
- **Senha:** `bgpeterleandro`
- **Email:** popperl@gmail.com

## 📧 Configuração do Email (IMPORTANTE!)

Para que os emails funcionem, você precisa configurar as credenciais do Gmail no Fly.io:

### Passo 1: Criar Senha de App do Gmail

1. Acesse: https://myaccount.google.com/security
2. Ative a **verificação em 2 etapas** (se ainda não estiver ativa)
3. Vá em **"Senhas de app"**
4. Selecione **"Mail"** como app
5. Selecione **"Outro"** como dispositivo e digite "Fly.io"
6. Clique em **"Gerar"**
7. **Copie a senha gerada** (16 caracteres sem espaços)

### Passo 2: Configurar no Fly.io

Execute estes comandos no PowerShell:

```powershell
$env:PATH += ";C:\Users\LPopperl\.fly\bin"

# Configurar email backend
flyctl secrets set EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend" -a bgcatalog

# Configurar servidor SMTP do Gmail
flyctl secrets set EMAIL_HOST="smtp.gmail.com" -a bgcatalog
flyctl secrets set EMAIL_PORT="587" -a bgcatalog
flyctl secrets set EMAIL_USE_TLS="True" -a bgcatalog

# Configurar credenciais (SUBSTITUA pela senha de app que você copiou)
flyctl secrets set EMAIL_HOST_USER="popperl@gmail.com" -a bgcatalog
flyctl secrets set EMAIL_HOST_PASSWORD="sua_senha_app_aqui" -a bgcatalog
```

## 🚀 Fluxo Completo do Sistema

### Para Clientes (Visitantes):
1. Acessa https://bgcatalog.fly.dev/
2. Navega pelo catálogo de jogos
3. Clica em "Add to Cart" nos jogos desejados
4. Acessa o carrinho
5. Preenche formulário com seus dados
6. Clica em "Enviar Solicitação"
7. Recebe confirmação de que o pedido foi enviado

### Para Você (Administrador):
1. Recebe email em popperl@gmail.com com o pedido
2. Entra em contato com o cliente para confirmar
3. Acessa https://bgcatalog.fly.dev/admin-login/
4. Gerencia o catálogo:
   - Adiciona novos jogos
   - Edita preços e descontos
   - Marca jogos como vendidos
   - Atualiza estoque

## 📱 URLs do Sistema

| Função | URL | Acesso |
|--------|-----|--------|
| **Página Inicial** | https://bgcatalog.fly.dev/ | Todos |
| **Catálogo Público** | https://bgcatalog.fly.dev/public/ | Todos |
| **Carrinho** | https://bgcatalog.fly.dev/cart/ | Todos |
| **Login Admin** | https://bgcatalog.fly.dev/admin-login/ | Todos (precisa senha) |
| **Painel Admin** | https://bgcatalog.fly.dev/admin-panel/ | Apenas logados |

## 🎨 Recursos do Painel Administrativo

1. **Dashboard com Estatísticas:**
   - Total de jogos no catálogo
   - Jogos em estoque
   - Jogos vendidos
   - Valor total do inventário

2. **Gerenciamento de Jogos:**
   - Adicionar via Board Game Atlas API
   - Adicionar manualmente
   - Editar informações
   - Ajustar preços e descontos
   - Marcar como vendido
   - Excluir jogos

3. **Filtros e Buscas:**
   - Buscar por nome ou designer
   - Filtrar por condição
   - Filtrar por status (em estoque/vendido)
   - Ordenar por vários critérios

4. **Integração Google Sheets:**
   - Sincronizar catálogo com planilha

## 🔄 Deploy Automático

✅ **Deploy automático está configurado!**

Quando você fizer `git push` na branch `main`, o GitHub Actions automaticamente:
1. Faz build da aplicação
2. Faz deploy no Fly.io
3. Executa migrações
4. Cria usuário admin (se não existir)

**Para fazer uma atualização:**
```powershell
git add .
git commit -m "Sua mensagem"
git push
```

Aguarde 5-10 minutos e as mudanças estarão no ar!

## ✅ Status Atual

| Item | Status |
|------|--------|
| Catálogo Público | ✅ Funcionando |
| Carrinho de Compras | ✅ Funcionando |
| Sistema de Email | ⚠️ Precisa configurar Gmail |
| Área Administrativa | ✅ Funcionando |
| Deploy Automático | ✅ Configurado |
| Banco de Dados | ✅ PostgreSQL no Fly.io |
| Usuário Admin | ✅ Criado automaticamente |

## 🐛 Teste Tudo

### Teste o Carrinho:
1. Acesse https://bgcatalog.fly.dev/
2. Adicione alguns jogos ao carrinho
3. Vá para o carrinho
4. Preencha o formulário
5. Clique em "Enviar Solicitação"
6. **Verifique se recebeu o email em popperl@gmail.com**

### Teste o Admin:
1. Acesse https://bgcatalog.fly.dev/admin-login/
2. Entre com: `admin` / `bgpeterleandro`
3. Navegue pelo painel
4. Teste adicionar um jogo
5. Teste editar um jogo

## 📞 Suporte

Se algo não estiver funcionando:

1. **Verificar logs:**
   ```powershell
   $env:PATH += ";C:\Users\LPopperl\.fly\bin"
   flyctl logs -a bgcatalog
   ```

2. **Verificar status:**
   ```powershell
   flyctl status -a bgcatalog
   ```

3. **Reiniciar aplicação:**
   ```powershell
   flyctl apps restart bgcatalog
   ```

## 🎉 Pronto!

Seu sistema está completo e funcionando! Os clientes podem navegar, adicionar ao carrinho e solicitar orçamentos que chegarão direto no seu email.

**Não esqueça de configurar o email do Gmail!** Sem isso, os pedidos não chegarão para você.
