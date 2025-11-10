"""
Script to reset the database schema.
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
        
        print("Tables dropped successfully!")
        print("\nNow run: python manage.py migrate")

if __name__ == '__main__':
    import sys
    
    response = input("This will DELETE ALL DATA. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        reset_database()
        print("\nDatabase reset complete. Run migrations now:")
        print("python manage.py migrate")
    else:
        print("Operation cancelled.")
