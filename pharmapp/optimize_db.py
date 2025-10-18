#!/usr/bin/env python
"""
Manual database optimization script for PharmApp
Run this script to optimize database performance
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.db import connection


def create_performance_indexes():
    """Create performance indexes manually"""
    
    indexes = [
        # Item indexes
        "CREATE INDEX IF NOT EXISTS idx_item_name ON store_item(name);",
        "CREATE INDEX IF NOT EXISTS idx_item_brand ON store_item(brand);",
        "CREATE INDEX IF NOT EXISTS idx_item_stock ON store_item(stock);",
        
        # Cart indexes
        "CREATE INDEX IF NOT EXISTS idx_cart_user ON store_cart(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_cart_user_item ON store_cart(user_id, item_id);",
        
        # Receipt indexes
        "CREATE INDEX IF NOT EXISTS idx_receipt_user ON store_receipt(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_receipt_date ON store_receipt(date);",
    ]
    
    with connection.cursor() as cursor:
        for index_sql in indexes:
            try:
                print(f"Creating index: {index_sql}")
                cursor.execute(index_sql)
                print("+ Index created successfully")
            except Exception as e:
                print(f"- Failed to create index: {e}")
    
    print("\nDatabase optimization completed!")


def analyze_database():
    """Analyze database for query optimization"""
    
    tables = [
        'store_item',
        'store_cart', 
        'store_receipt',
        'wholesale_wholesaleitem',
        'wholesale_wholesalecart'
    ]
    
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f'ANALYZE {table};')
                print(f"+ Analyzed {table}")
            except Exception as e:
                print(f"- Failed to analyze {table}: {e}")


def vacuum_database():
    """Vacuum database to reclaim space"""
    
    with connection.cursor() as cursor:
        try:
            cursor.execute('VACUUM;')
            print("+ Database vacuumed successfully")
        except Exception as e:
            print(f"- Failed to vacuum database: {e}")


if __name__ == "__main__":
    print("Starting database optimization...")
    
    print("\n1. Creating performance indexes...")
    create_performance_indexes()
    
    print("\n2. Analyzing database...")
    analyze_database()
    
    print("\n3. Vacuuming database...")
    vacuum_database()
    
    print("\nOptimization complete!")
