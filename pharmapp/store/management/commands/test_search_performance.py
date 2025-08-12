from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from store.models import Item, WholesaleItem, DispensingLog
from decimal import Decimal
import time
import statistics

User = get_user_model()

class Command(BaseCommand):
    help = 'Test search performance improvements'

    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=10,
            help='Number of test iterations to run'
        )

    def handle(self, *args, **options):
        iterations = options['iterations']
        self.stdout.write("🚀 Testing search performance improvements...")
        
        # Get or create a test user
        user = User.objects.first()
        if not user:
            self.stdout.write("❌ No users found. Please create a user first.")
            return
        
        client = Client()
        client.force_login(user)
        
        # Test data
        test_queries = ['A', 'AM', 'AML', 'AMLO', 'AMLOD']
        
        self.stdout.write(f"👤 Using user: {user.username}")
        self.stdout.write(f"🔄 Running {iterations} iterations per test")
        self.stdout.write(f"📊 Testing queries: {test_queries}")
        
        # Test 1: Item Search Performance
        self.stdout.write("\n📦 Testing Item Search Performance...")
        item_times = []
        
        for query in test_queries:
            query_times = []
            for i in range(iterations):
                start_time = time.time()
                response = client.get(reverse('store:search_item'), {'search': query}, 
                                    HTTP_HX_REQUEST='true')
                end_time = time.time()
                
                if response.status_code == 200:
                    query_times.append((end_time - start_time) * 1000)  # Convert to ms
                else:
                    self.stdout.write(f"❌ Failed request for query '{query}': {response.status_code}")
            
            if query_times:
                avg_time = statistics.mean(query_times)
                min_time = min(query_times)
                max_time = max(query_times)
                item_times.extend(query_times)
                
                self.stdout.write(f"  Query '{query}': {avg_time:.2f}ms avg (min: {min_time:.2f}ms, max: {max_time:.2f}ms)")
        
        # Test 2: Dispensing Log Search Performance
        self.stdout.write("\n📋 Testing Dispensing Log Search Performance...")
        dispensing_times = []
        
        for query in test_queries:
            query_times = []
            for i in range(iterations):
                start_time = time.time()
                response = client.get(reverse('store:dispensing_log'), {'item_name': query}, 
                                    HTTP_HX_REQUEST='true')
                end_time = time.time()
                
                if response.status_code == 200:
                    query_times.append((end_time - start_time) * 1000)  # Convert to ms
                else:
                    self.stdout.write(f"❌ Failed request for query '{query}': {response.status_code}")
            
            if query_times:
                avg_time = statistics.mean(query_times)
                min_time = min(query_times)
                max_time = max(query_times)
                dispensing_times.extend(query_times)
                
                self.stdout.write(f"  Query '{query}': {avg_time:.2f}ms avg (min: {min_time:.2f}ms, max: {max_time:.2f}ms)")
        
        # Test 3: Search Suggestions Performance
        self.stdout.write("\n💡 Testing Search Suggestions Performance...")
        suggestion_times = []
        
        for query in test_queries:
            query_times = []
            for i in range(iterations):
                start_time = time.time()
                response = client.get(reverse('store:dispensing_log_search_suggestions'), {'q': query})
                end_time = time.time()
                
                if response.status_code == 200:
                    query_times.append((end_time - start_time) * 1000)  # Convert to ms
                else:
                    self.stdout.write(f"❌ Failed request for query '{query}': {response.status_code}")
            
            if query_times:
                avg_time = statistics.mean(query_times)
                min_time = min(query_times)
                max_time = max(query_times)
                suggestion_times.extend(query_times)
                
                self.stdout.write(f"  Query '{query}': {avg_time:.2f}ms avg (min: {min_time:.2f}ms, max: {max_time:.2f}ms)")
        
        # Overall Statistics
        self.stdout.write("\n📈 Overall Performance Summary:")
        
        if item_times:
            self.stdout.write(f"  📦 Item Search: {statistics.mean(item_times):.2f}ms avg")
        
        if dispensing_times:
            self.stdout.write(f"  📋 Dispensing Log: {statistics.mean(dispensing_times):.2f}ms avg")
        
        if suggestion_times:
            self.stdout.write(f"  💡 Suggestions: {statistics.mean(suggestion_times):.2f}ms avg")
        
        # Database Statistics
        self.stdout.write("\n📊 Database Statistics:")
        self.stdout.write(f"  📦 Total Items: {Item.objects.count()}")
        self.stdout.write(f"  🏪 Total Wholesale Items: {WholesaleItem.objects.count()}")
        self.stdout.write(f"  📋 Total Dispensing Logs: {DispensingLog.objects.count()}")
        
        # Performance Recommendations
        self.stdout.write("\n💡 Performance Optimizations Applied:")
        self.stdout.write("  ✅ Database indexes on name, brand, dosage_form fields")
        self.stdout.write("  ✅ Composite indexes for multi-field searches")
        self.stdout.write("  ✅ Query optimization with istartswith + icontains")
        self.stdout.write("  ✅ Result limiting (30-50 items max)")
        self.stdout.write("  ✅ select_related for foreign keys")
        self.stdout.write("  ✅ Reduced HTMX delays (200ms for dispensing, 150ms for items)")
        self.stdout.write("  ✅ Minimum query length requirements")
        
        self.stdout.write(self.style.SUCCESS("\n🎉 Search performance test completed!"))
