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

def test_barcode_variations():
    """Test different barcode format variations"""
    original_barcode = "0029877030712"
    
    print(f"Testing barcode variations for: {original_barcode}")
    print("=" * 60)
    
    # Generate variations manually to see what we're testing
    variations = []
    variations.append(original_barcode)  # Original: 0029877030712
    variations.append(original_barcode.lstrip('0'))  # Remove leading zeros: 29877030712
    variations.append(original_barcode[:-1])  # Remove check digit: 002987703071
    variations.append(original_barcode[:-1].lstrip('0'))  # Both: 2987703071
    
    if original_barcode.startswith('0') and len(original_barcode) == 13:
        variations.append(original_barcode[1:])  # EAN-13 to UPC-A: 029877030712
    
    # Remove duplicates
    unique_variations = list(dict.fromkeys([v for v in variations if v and len(v) >= 8]))
    
    print(f"Testing variations: {unique_variations}")
    print()
    
    # Test each variation manually to see what gets results
    for i, variation in enumerate(unique_variations, 1):
        print(f"{i}. Testing variation: {variation}")
        try:
            # Test direct BGG search first
            direct_results = BGGService.search_games(variation)
            if direct_results:
                print(f"   ✓ Direct BGG search found {len(direct_results)} results")
                for result in direct_results[:2]:
                    print(f"     - {result.get('name', 'N/A')} (ID: {result.get('id', 'N/A')})")
            else:
                print(f"   ✗ Direct BGG search: no results")
        except Exception as e:
            print(f"   ✗ Direct BGG search failed: {e}")
        print()
    
    print("=" * 60)
    print("Now testing full barcode lookup (with external APIs):")
    
    try:
        results = BGGService.search_by_barcode(original_barcode)
        print(f"Final results: {len(results)}")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('name', 'N/A')} (ID: {result.get('id', 'N/A')}, Year: {result.get('year', 'N/A')})")
    except Exception as e:
        print(f"Full lookup failed: {e}")
        import traceback
        traceback.print_exc()

def test_known_barcode():
    """Test with a known board game barcode"""
    # Let's try a common board game barcode
    test_codes = [
        "0029877030712",  # Your original
        "29877030712",    # Without leading zero
        "653569425502",   # Common Fantasy Flight Games prefix
        "841333103347",   # Stonemaier Games (Wingspan)
    ]
    
    for barcode in test_codes:
        print(f"\n{'='*50}")
        print(f"Testing known barcode: {barcode}")
        print('='*50)
        
        try:
            results = BGGService.search_by_barcode(barcode)
            if results:
                print(f"✓ Found {len(results)} results:")
                for result in results[:3]:
                    print(f"  - {result.get('name', 'N/A')} (ID: {result.get('id', 'N/A')})")
            else:
                print("✗ No results found")
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_barcode_variations()
    test_known_barcode()