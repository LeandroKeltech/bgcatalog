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

def test_gameupc_lookup(barcode):
    print(f"Testando GameUPC lookup para barcode: {barcode}")
    print("=" * 60)
    
    try:
        # Test the external lookup directly
        results = BGGService._lookup_external_barcode(barcode)
        print(f"Resultados do GameUPC lookup: {len(results)}")
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. Nome: {result.get('name', 'N/A')}")
                print(f"   ID: {result.get('id', 'N/A')}")
                print(f"   Ano: {result.get('year', 'N/A')}")
                print()
        else:
            print("Nenhum resultado encontrado via GameUPC.")
            
        # Test the full barcode search (including GameUPC fallback)
        print("\n" + "=" * 40)
        print("Testando busca completa (com GameUPC fallback):")
        full_results = BGGService.search_by_barcode(barcode)
        print(f"Resultados da busca completa: {len(full_results)}")
        
        for i, result in enumerate(full_results, 1):
            print(f"{i}. Nome: {result.get('name', 'N/A')}")
            print(f"   ID: {result.get('id', 'N/A')}")
            print(f"   Ano: {result.get('year', 'N/A')}")
            print()
            
    except Exception as e:
        print(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Testar com o barcode específico
    test_gameupc_lookup("0029877030712")
    
    print("\n" + "=" * 60)
    print("Links para testar:")
    print(f"1. GameUPC manual: https://www.gameupc.com/search.php?s=0029877030712")
    print(f"2. BGG search: https://bgcatalog.fly.dev/bgg/search/")
    print(f"3. Barcode endpoint: https://bgcatalog.fly.dev/bgg/search/barcode/")