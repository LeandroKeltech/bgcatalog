# Configuração de Deploy Automático no Fly.io

## Passo 1: Criar o Token do Fly.io

Execute este comando no PowerShell:

```powershell
$env:PATH += ";C:\Users\LPopperl\.fly\bin"
flyctl tokens create deploy
```

Isso vai gerar um token. **COPIE E GUARDE** este token, você vai precisar dele no próximo passo.

## Passo 2: Adicionar o Token como Secret no GitHub

1. Acesse: https://github.com/LeandroKeltech/bgcatalog/settings/secrets/actions

2. Clique em **"New repository secret"**

3. Preencha:
   - **Name**: `FLY_API_TOKEN`
   - **Secret**: Cole o token que você copiou no Passo 1

4. Clique em **"Add secret"**

## Passo 3: Testar o Deploy Automático

Depois de configurar o secret, faça um commit qualquer:

```powershell
git add .
git commit -m "Test auto deploy"
git push
```

O GitHub Actions vai automaticamente:
1. Detectar o push na branch main
2. Fazer o build da aplicação
3. Fazer deploy no Fly.io

## Verificar o Status do Deploy

Você pode acompanhar o deploy em:
https://github.com/LeandroKeltech/bgcatalog/actions

## Como Funciona

- ✅ Toda vez que você fizer `git push` na branch **main**, o deploy acontece automaticamente
- ✅ O build é feito no GitHub Actions (não no depot builder local)
- ✅ Você receberá email se o deploy falhar
- ✅ O deploy demora cerca de 3-5 minutos

## Comandos Úteis

```powershell
# Ver status do app
flyctl status -a bgcatalog

# Ver logs em tempo real
flyctl logs -a bgcatalog

# Abrir o site
flyctl open -a bgcatalog
```

## Desabilitar Deploy Automático

Se você quiser desabilitar o deploy automático, delete o arquivo:
`.github/workflows/fly-deploy.yml`
