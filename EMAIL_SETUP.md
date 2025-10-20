# EMAIL CONFIGURATION GUIDE

## Problem
O sistema está configurado para usar `console.EmailBackend` que apenas mostra emails nos logs, mas não os envia de fato.

## Solution
Configure as seguintes variáveis de ambiente no Fly.io:

### 1. Configurar Gmail App Password
1. Acesse https://myaccount.google.com/security
2. Ative "2-Step Verification" se não estiver ativo
3. Vá em "App passwords"
4. Crie uma nova app password para "Mail"
5. Use essa senha (não a senha normal do Gmail)

### 2. Configurar variáveis no Fly.io
Execute estes comandos no terminal:

```bash
flyctl secrets set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend -a bgcatalog
flyctl secrets set EMAIL_HOST=smtp.gmail.com -a bgcatalog
flyctl secrets set EMAIL_PORT=587 -a bgcatalog
flyctl secrets set EMAIL_USE_TLS=True -a bgcatalog
flyctl secrets set EMAIL_HOST_USER=popperl@gmail.com -a bgcatalog
flyctl secrets set EMAIL_HOST_PASSWORD=your-16-digit-app-password -a bgcatalog
flyctl secrets set DEFAULT_FROM_EMAIL=popperl@gmail.com -a bgcatalog
```

### 3. Redeploy the app
```bash
flyctl deploy -a bgcatalog --region lhr
```

## Testing
Depois de configurar:
1. Faça um pedido de cotação no site
2. Verifique se o email chegou em popperl@gmail.com
3. Monitore os logs com: `flyctl logs -a bgcatalog`

## Alternative: Temporary fix with Console Backend
Se quiser manter os emails apenas nos logs por enquanto:
```bash
flyctl secrets set EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend -a bgcatalog
```

## Troubleshooting
- Verifique se o Gmail app password está correto
- Confirme que a verificação em 2 etapas está ativa no Gmail
- Verifique os logs do Fly.io para mensagens de erro de SMTP