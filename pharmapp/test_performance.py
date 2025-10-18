#!/usr/bin/env python
"""
Performance testing script for PharmApp
Tests response times for common operations
"""

import os
import sys
import time
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from store.models import Item, Cart
from django.db import connection

User = get_user_model()

class PerformanceTest:
    def __init__(self):
        self.client = Client()
        
    def setup_test_user(self):
        """Create a test user if not exists"""
        try:
            user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            user = User.objects.create_user(
                username='testuser',
                password='testpass123',
                email='test@example.com'
            )
        return user
    
    def test_login_time(self):
        """Test login response time"""
        print("\n1. Testing login performance...")
        start = time.time()
        response = self.client.post('/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        end = time.time()
        response_time = end - start
        print(f"   Login response time: {response_time:.3f}s")
        return response_time
    
    def test_item_search_time(self):
        """Test item search performance"""
        print("\n2. Testing item search performance...")
        
        # Login first
        user = self.setup_test_user()
        self.client.force_login(user)
        
        # Test search
        start = time.time()
        response = self.client.get('/store/dispense_search_items/?q=test')
        end = time.time()
        response_time = end - start
        print(f"   Item search response time: {response_time:.3f}s")
        return response_time
    
    def test_cart_load_time(self):
        """Test cart loading performance"""
        print("\n3. Testing cart loading performance...")
        
        user = self.setup_test_user()
        self.client.force_login(user)
        
        start = time.time()
        response = self.client.get('/store/cart/')
        end = time.time()
        response_time = end - start
        print(f"   Cart load response time: {response_time:.3f}s")
        return response_time
    
    def test_dashboard_load_time(self):
        """Test dashboard loading performance"""
        print("\n4. Testing dashboard loading performance...")
        
        user = self.setup_test_user()
        self.client.force_login(user)
        
        start = time.time()
        response = self.client.get('/store/dashboard/')
        end = time.time()
        response_time = end - start
        print(f"   Dashboard load response time: {response_time:.3f}s")
        return response_time
    
    def test_database_query_count(self):
        """Test database query counts"""
        print("\n5. Testing database query performance...")
        
        user = self.setup_test_user()
        self.client.force_login(user)
        
        # Reset query count
        connection.queries_log.clear()
        
        start = time.time()
        response = self.client.get('/store/cart/')
        end = time.time()
        
        query_count = len(connection.queries)
        response_time = end - start
        print(f"   Cart page: {query_count} queries in {response_time:.3f}s")
        
        connection.queries_log.clear()
        
        start = time.time()
        response = self.client.get('/store/dashboard/')
        end = time.time()
        
        query_count = len(connection.queries)
        response_time = end - start
        print(f"   Dashboard: {query_count} queries in {response_time:.3f}s")
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("Starting performance tests...")
        
        times = []
        times.append(self.test_login_time())
        times.append(self.test_item_search_time())
        times.append(self.test_cart_load_time())
        times.append(self.test_dashboard_load_time())
        
        self.test_database_query_count()
        
        avg_time = sum(times) / len(times)
        print(f"\nAverage response time: {avg_time:.3f}s")
        
        if avg_time < 0.5:
            print("Performance: EXCELLENT")
        elif avg_time < 1.0:
            print("Performance: GOOD")
        elif avg_time < 2.0:
            print("Performance: ACCEPTABLE")
        else:
            print("Performance: NEEDS IMPROVEMENT")
        
        return avg_time

if __name__ == "__main__":
    tester = PerformanceTest()
    tester.run_all_tests()
