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


def create_index_if_not_exists(cursor, index_name, table_name, columns, db_engine):
    """Create an index if it doesn't already exist, handling different database engines"""
    if db_engine.lower() == 'mysql':
        # MySQL: Check if index exists first
        cursor.execute("""
            SELECT COUNT(1) FROM information_schema.STATISTICS 
            WHERE table_schema = DATABASE() 
            AND table_name = %s 
            AND index_name = %s
        """, [table_name, index_name])
        
        if cursor.fetchone()[0] == 0:
            cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({columns})")
            return True
        return False
    else:
        # SQLite and others: Use IF NOT EXISTS syntax
        cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})")
        return True


def create_performance_indexes():
    """Create performance indexes manually"""
    
    db_engine = connection.vendor
    print(f"Detected database engine: {db_engine}")
    
    indexes = [
        # (index_name, table_name, columns)
        ("idx_item_name", "store_item", "name"),
        ("idx_item_brand", "store_item", "brand"),
        ("idx_item_stock", "store_item", "stock"),
        ("idx_cart_user", "store_cart", "user_id"),
        ("idx_cart_user_item", "store_cart", "user_id, item_id"),
        ("idx_receipt_user", "store_receipt", "user_id"),
        ("idx_receipt_date", "store_receipt", "date"),
    ]
    
    with connection.cursor() as cursor:
        for index_name, table_name, columns in indexes:
            try:
                print(f"Creating index: {index_name} ON {table_name}({columns})")
                created = create_index_if_not_exists(cursor, index_name, table_name, columns, db_engine)
                if created:
                    print("+ Index created successfully")
                else:
                    print("= Index already exists, skipped")
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
    
    db_engine = connection.vendor
    
    with connection.cursor() as cursor:
        for table in tables:
            try:
                if db_engine.lower() == 'mysql':
                    cursor.execute(f'ANALYZE TABLE {table}')
                else:
                    cursor.execute(f'ANALYZE {table}')
                print(f"+ Analyzed {table}")
            except Exception as e:
                print(f"- Failed to analyze {table}: {e}")


def vacuum_database():
    """Vacuum database to reclaim space (SQLite only, MySQL uses OPTIMIZE TABLE)"""
    
    db_engine = connection.vendor
    
    with connection.cursor() as cursor:
        try:
            if db_engine.lower() == 'mysql':
                # MySQL doesn't have VACUUM, use OPTIMIZE TABLE instead for key tables
                tables = ['store_item', 'store_cart', 'store_receipt', 'userauth_activitylog']
                for table in tables:
                    try:
                        cursor.execute(f'OPTIMIZE TABLE {table}')
                        print(f"+ Optimized table {table}")
                    except Exception as e:
                        print(f"- Failed to optimize {table}: {e}")
            else:
                cursor.execute('VACUUM;')
                print("+ Database vacuumed successfully")
        except Exception as e:
            print(f"- Failed to vacuum/optimize database: {e}")


if __name__ == "__main__":
    print("Starting database optimization...")
    
    print("\n1. Creating performance indexes...")
    create_performance_indexes()
    
    print("\n2. Analyzing database...")
    analyze_database()
    
    print("\n3. Vacuuming/Optimizing database...")
    vacuum_database()
    
    print("\nOptimization complete!")
