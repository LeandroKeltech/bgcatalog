"""
Script para testar várias APIs de board games e ver quais não estão bloqueadas pelo ESET
"""
import requests
import time
from colorama import init, Fore, Style

# Inicializar colorama para cores no terminal Windows
try:
    init(autoreset=True)
except:
    pass

def test_api(name, url, method='GET', headers=None, timeout=5):
    """Testa uma API e retorna o resultado"""
    try:
        print(f"\n{Fore.CYAN}Testando: {name}{Style.RESET_ALL}")
        print(f"URL: {url}")
        
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=timeout)
        else:
            response = requests.post(url, headers=headers, timeout=timeout)
        
        status = response.status_code
        
        if status == 200:
            print(f"{Fore.GREEN}✓ SUCESSO! Status: {status}{Style.RESET_ALL}")
            print(f"Tamanho da resposta: {len(response.content)} bytes")
            return True
        elif status == 403:
            print(f"{Fore.YELLOW}⚠ BLOQUEADO! Status: 403 Forbidden{Style.RESET_ALL}")
            return False
        else:
            print(f"{Fore.YELLOW}⚠ Status: {status}{Style.RESET_ALL}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"{Fore.RED}✗ ERRO SSL (ESET bloqueou): {str(e)[:100]}...{Style.RESET_ALL}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"{Fore.RED}✗ ERRO DE CONEXÃO: {str(e)[:100]}...{Style.RESET_ALL}")
        return False
    except requests.exceptions.Timeout:
        print(f"{Fore.RED}✗ TIMEOUT (demorou muito){Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}✗ ERRO: {str(e)[:100]}...{Style.RESET_ALL}")
        return False


def main():
    print(f"\n{Fore.MAGENTA}{'='*70}")
    print("TESTADOR DE APIs DE BOARD GAMES")
    print(f"{'='*70}{Style.RESET_ALL}\n")
    
    apis = [
        # BoardGameGeek - XML API
        {
            'name': 'BoardGameGeek XML API (HTTPS)',
            'url': 'https://boardgamegeek.com/xmlapi2/search?query=catan&type=boardgame'
        },
        {
            'name': 'BoardGameGeek XML API (HTTP)',
            'url': 'http://www.boardgamegeek.com/xmlapi2/search?query=catan&type=boardgame'
        },
        
        # Board Game Atlas - API gratuita com rate limit
        {
            'name': 'Board Game Atlas API',
            'url': 'https://api.boardgameatlas.com/api/search?name=catan&client_id=JLBr5npPhV'
        },
        
        # Board Game Atlas - endpoint alternativo
        {
            'name': 'Board Game Atlas API v2',
            'url': 'https://www.boardgameatlas.com/api/search?name=catan&pretty=true'
        },
        
        # Luding.org - base de dados europeia
        {
            'name': 'Luding.org (Europa)',
            'url': 'https://www.luding.org/cgi-bin/GameData.py/enGBJSON/GameData/Catan'
        },
        
        # Tabletop DB (alternativa)
        {
            'name': 'Tabletop DB',
            'url': 'https://www.tabletopdb.com/search?q=catan'
        },
        
        # BGG JSON API (não oficial)
        {
            'name': 'BGG JSON API (não oficial)',
            'url': 'https://bgg-json.azurewebsites.net/thing/13'
        },
        
        # APIs públicas de teste
        {
            'name': 'JSONPlaceholder (teste geral de HTTPS)',
            'url': 'https://jsonplaceholder.typicode.com/posts/1'
        },
        {
            'name': 'HTTPBin (teste de SSL)',
            'url': 'https://httpbin.org/get'
        },
        
        # Reddit API (como teste alternativo)
        {
            'name': 'Reddit API (teste)',
            'url': 'https://www.reddit.com/r/boardgames.json'
        },
    ]
    
    successful = []
    failed = []
    
    for api in apis:
        result = test_api(api['name'], api['url'])
        if result:
            successful.append(api['name'])
        else:
            failed.append(api['name'])
        time.sleep(0.5)  # Pequena pausa entre requisições
    
    # Resumo
    print(f"\n{Fore.MAGENTA}{'='*70}")
    print("RESUMO DOS TESTES")
    print(f"{'='*70}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}APIs que FUNCIONARAM ({len(successful)}):{Style.RESET_ALL}")
    for api in successful:
        print(f"  ✓ {api}")
    
    print(f"\n{Fore.RED}APIs que FALHARAM ({len(failed)}):{Style.RESET_ALL}")
    for api in failed:
        print(f"  ✗ {api}")
    
    print(f"\n{Fore.CYAN}Próximos passos:{Style.RESET_ALL}")
    if successful:
        print("  1. Use uma das APIs que funcionou")
        print("  2. Ou configure exceção no ESET para BoardGameGeek")
        print("  3. Ou use o modo manual de adicionar jogos")
    else:
        print("  1. Configure exceção no ESET para permitir conexões HTTPS do Python")
        print("  2. Ou use o modo manual de adicionar jogos (já implementado!)")
    
    print(f"\n{Fore.YELLOW}IMPORTANTE:{Style.RESET_ALL}")
    print("  Se TODAS as APIs HTTPS falharam, o problema é o ESET bloqueando SSL do Python.")
    print("  Solução: ESET > Configurações > Proteção da Internet > SSL/TLS > Adicionar exceção\n")


if __name__ == '__main__':
    main()
