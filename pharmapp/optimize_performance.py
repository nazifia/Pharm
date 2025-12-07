#!/usr/bin/env python
"""
Performance optimization script for PharmApp
This script helps clear caches and optimize the database
"""
import os
import sys
import django

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.core.cache import cache
from django.db import connection
from userauth.models import ActivityLog


def clear_cache():
    """Clear all caches"""
    print("Clearing caches...")
    cache.clear()
    print("✓ Cache cleared successfully")


def analyze_slow_queries():
    """Analyze database query patterns"""
    print("\nAnalyzing database queries...")
    
    # Get most active users
    from django.db.models import Count
    active_users = ActivityLog.objects.values('user__username').annotate(
        action_count=Count('id')
    ).order_by('-action_count')[:10]
    
    print("Top 10 most active users:")
    for user in active_users:
        print(f"  - {user['user__username']}: {user['action_count']} actions")
    
    # Check activity log count
    total_activities = ActivityLog.objects.count()
    print(f"\nTotal activity log entries: {total_activities}")
    
    if total_activities > 10000:
        print("⚠️  Consider archiving old activity logs to improve performance")


def vacuum_database():
    """Optimize database (SQLite specific)"""
    print("\nOptimizing database...")
    with connection.cursor() as cursor:
        cursor.execute("VACUUM")
    print("✓ Database optimized (VACUUM completed)")


def check_indexes():
    """Check and report on database indexes"""
    print("\nChecking database indexes...")
    with connection.cursor() as cursor:
        # Check if our optimization indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' 
            AND name IN ('idx_activitylog_user_timestamp', 'idx_activitylog_timestamp')
        """)
        indexes = cursor.fetchall()
        
        if len(indexes) == 2:
            print("✓ All optimization indexes are present")
        elif len(indexes) == 1:
            print("⚠️  Only 1 of 2 optimization indexes is present")
        else:
            print("✗ Optimization indexes are missing - consider running migrations")


def main():
    """Main function"""
    print("PharmApp Performance Optimization Tool")
    print("=" * 40)
    
    try:
        clear_cache()
        analyze_slow_queries()
        check_indexes()
        
        # Only run vacuum in development
        if os.environ.get('DJANGO_SETTINGS_MODULE') == 'pharmapp.settings':
            vacuum_database()
        
        print("\n" + "=" * 40)
        print("✓ Performance optimization completed successfully!")
        print("\nRecommendations:")
        print("1. Monitor the slow queries in production")
        print("2. Consider implementing query result caching for frequently accessed data")
        print("3. Use Django's select_related and prefetch_related for complex queries")
        print("4. Consider using a more powerful database like PostgreSQL for production")
        
    except Exception as e:
        print(f"\n✗ Error during optimization: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
