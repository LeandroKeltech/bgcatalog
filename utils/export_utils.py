import requests
import json
import csv
from kivymd.toast import toast

def export_to_google_sheets(items, script_url):
    """
    Export items to Google Sheets via Apps Script.
    Returns (success: bool, message: str, count: int)
    """
    if not script_url:
        return False, "Apps Script URL not configured", 0
    
    if not items:
        return False, "No items to export", 0
    
    try:
        # Prepare data according to contract
        export_data = []
        for item in items:
            export_data.append({
                "ID": item.get("id"),
                "Categoria": item.get("categoria"),
                "Nome": item.get("titulo"),
                "Condição": item.get("condicao"),
                "Preço de Referência": item.get("preco_referencia"),
                "Fonte": item.get("fonte_preco"),
                "Regra(%)": item.get("regra_preco_percent"),
                "Preço Final": item.get("preco_final"),
                "Qtd Estoque": item.get("qty_estoque"),
                "Qtd Vendida": item.get("qty_vendida"),
                "Descrição": item.get("descricao"),
                "Imagem Path": item.get("imagem_path"),
                "Notas": item.get("notas"),
                "Timestamp": item.get("updated_at")
            })
        
        # Send to Apps Script
        response = requests.post(script_url, 
                               json={"items": export_data}, 
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok", False):
                return True, f"Exported successfully", len(export_data)
            else:
                return False, result.get("message", "Unknown error"), 0
        else:
            return False, f"HTTP {response.status_code}", 0
            
    except Exception as e:
        return False, f"Export failed: {e}", 0

def export_to_csv(items, filepath):
    """
    Export items to local CSV file.
    Returns (success: bool, message: str)
    """
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            if not items:
                return False, "No items to export"
            
            fieldnames = ["ID", "Categoria", "Nome", "Condição", "Preço de Referência", 
                         "Fonte", "Regra(%)", "Preço Final", "Qtd Estoque", "Qtd Vendida",
                         "Descrição", "Imagem Path", "Notas", "Timestamp"]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in items:
                writer.writerow({
                    "ID": item.get("id"),
                    "Categoria": item.get("categoria"),
                    "Nome": item.get("titulo"),
                    "Condição": item.get("condicao"),
                    "Preço de Referência": item.get("preco_referencia"),
                    "Fonte": item.get("fonte_preco"),
                    "Regra(%)": item.get("regra_preco_percent"),
                    "Preço Final": item.get("preco_final"),
                    "Qtd Estoque": item.get("qty_estoque"),
                    "Qtd Vendida": item.get("qty_vendida"),
                    "Descrição": item.get("descricao"),
                    "Imagem Path": item.get("imagem_path"),
                    "Notas": item.get("notas"),
                    "Timestamp": item.get("updated_at")
                })
        
        return True, f"CSV exported to {filepath}"
    except Exception as e:
        return False, f"CSV export failed: {e}"
