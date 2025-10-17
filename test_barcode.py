#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bgcatalog_project.settings')
django.setup()

from catalog.bgg_service import BGGService

def test_barcode_search(barcode):
    print(f"Testando barcode: {barcode}")
    print("=" * 50)
    
    try:
        results = BGGService.search_by_barcode(barcode)
        print(f"Número de resultados encontrados: {len(results)}")
        print()
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. Nome: {result.get('name', 'N/A')}")
                print(f"   ID: {result.get('id', 'N/A')}")
                print(f"   Ano: {result.get('year', 'N/A')}")
                print()
        else:
            print("Nenhum resultado encontrado.")
            
        # Testar também busca direta no BGG
        print("\nTestando busca direta no BGG:")
        direct_results = BGGService.search_games(barcode)
        print(f"Resultados da busca direta: {len(direct_results)}")
        for result in direct_results[:3]:  # Mostrar apenas os primeiros 3
            print(f"- {result}")
            
    except Exception as e:
        print(f"Erro durante a busca: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Testar com o barcode específico
    test_barcode_search("0029877030712")
    
    print("\n" + "=" * 50)
    print("Links para testar manualmente:")
    print(f"1. Barcode scan endpoint: https://bgcatalog.fly.dev/bgg/search/barcode/")
    print(f"2. BGG search page: https://bgcatalog.fly.dev/bgg/search/")
    print(f"3. Admin panel: https://bgcatalog.fly.dev/admin/")