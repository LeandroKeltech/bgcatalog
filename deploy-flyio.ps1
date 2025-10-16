# Script de Deploy para Fly.io
# Execute este script quando o builder do Fly.io estiver funcionando

Write-Host "Iniciando deploy no Fly.io..." -ForegroundColor Green

# Adiciona o flyctl ao PATH
$env:PATH += ";C:\Users\LPopperl\.fly\bin"

# Verifica se está logado
Write-Host "Verificando login..." -ForegroundColor Yellow
flyctl auth whoami

# Faz o deploy
Write-Host "Fazendo deploy..." -ForegroundColor Yellow
flyctl deploy --ha=false --wait-timeout 600

Write-Host "Deploy concluído!" -ForegroundColor Green
