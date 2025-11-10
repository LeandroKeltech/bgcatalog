"""
Script to reset the database schema - auto mode for deployment.
Run this with: python reset_db.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bgcatalog_project.settings')
django.setup()

from django.db import connection

def reset_database():
    """Drop all tables and recreate them."""
    with connection.cursor() as cursor:
        print("Dropping existing tables...")
        
        # Drop tables in correct order (respecting foreign keys)
        cursor.execute("DROP TABLE IF EXISTS catalog_stockreservation CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS catalog_boardgame CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS django_migrations CASCADE;")
        
        print("Tables dropped successfully!")

if __name__ == '__main__':
    reset_database()
    print("Database reset complete.")
