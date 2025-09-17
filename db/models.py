import sqlite3
import uuid
from datetime import datetime

DB_PATH = 'catalog.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        categoria TEXT NOT NULL,
        titulo TEXT NOT NULL,
        descricao TEXT,
        condicao TEXT,
        estado TEXT,
        barcode TEXT,
        bgg_id TEXT,
        preco_referencia REAL NOT NULL,
        fonte_preco TEXT,
        regra_preco_percent INTEGER DEFAULT -50,
        preco_sugerido REAL,
        preco_final REAL NOT NULL,
        qty_estoque INTEGER DEFAULT 0,
        qty_vendida INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        imagem_path TEXT,
        notas TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id TEXT PRIMARY KEY,
        item_id TEXT,
        acao TEXT,
        campo TEXT,
        valor_antigo TEXT,
        valor_novo TEXT,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()
