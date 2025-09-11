from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, date
from supplier.models import Supplier, Procurement, ProcurementItem, WholesaleProcurement, WholesaleProcurementItem
from userauth.models import Profile

User = get_user_model()


class SupplierAnalyticsTestCase(TestCase):
    """Test cases for supplier analytics functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test user with admin privileges
        self.user = User.objects.create_user(
            mobile='1234567890',
            password='testpass123'
        )

        # Create profile for user
        self.profile = Profile.objects.create(
            user=self.user,
            full_name='Test User',
            user_type='Admin'
        )

        # Create test suppliers
        self.supplier1 = Supplier.objects.create(
            name='Test Supplier 1',
            phone='1111111111',
            contact_info='Test Address 1'
        )

        self.supplier2 = Supplier.objects.create(
            name='Test Supplier 2',
            phone='2222222222',
            contact_info='Test Address 2'
        )

        # Create test procurements
        self.procurement1 = Procurement.objects.create(
            supplier=self.supplier1,
            created_by=self.user,
            date=date.today(),
            total=Decimal('1000.00'),
            status='completed'
        )

        self.procurement2 = Procurement.objects.create(
            supplier=self.supplier2,
            created_by=self.user,
            date=date.today(),
            total=Decimal('2000.00'),
            status='completed'
        )

        # Login user
        self.client.login(mobile='1234567890', password='testpass123')

    def test_supplier_monthly_analytics_view(self):
        """Test supplier monthly analytics view"""
        url = reverse('store:supplier_monthly_analytics')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supplier Monthly Analytics')
        self.assertContains(response, 'Test Supplier 1')
        self.assertContains(response, 'Test Supplier 2')

    def test_supplier_performance_dashboard_view(self):
        """Test supplier performance dashboard view"""
        url = reverse('store:supplier_performance_dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supplier Performance Dashboard')
        self.assertContains(response, 'Total Procurement Value')

    def test_enhanced_procurement_search_view(self):
        """Test enhanced procurement search view"""
        url = reverse('store:enhanced_procurement_search')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enhanced Procurement Search')
        self.assertContains(response, 'Advanced Search Filters')

    def test_supplier_comparison_view(self):
        """Test supplier comparison view"""
        url = reverse('store:supplier_comparison')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select Suppliers to Compare')

        # Test with suppliers selected
        url_with_suppliers = f"{url}?suppliers={self.supplier1.id}&suppliers={self.supplier2.id}"
        response = self.client.get(url_with_suppliers)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Supplier Comparison Results')

    def test_supplier_stats_api(self):
        """Test supplier statistics API"""
        url = reverse('store:supplier_stats_api', args=[self.supplier1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['supplier_id'], self.supplier1.id)
        self.assertEqual(data['supplier_name'], 'Test Supplier 1')
        self.assertEqual(data['retail_total'], 1000.0)
        self.assertEqual(data['retail_count'], 1)

    def test_quick_supplier_search_api(self):
        """Test quick supplier search API"""
        url = reverse('store:quick_supplier_search')
        response = self.client.get(url, {'q': 'Test'})

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['results'][0]['name'], 'Test Supplier 1')

    def test_analytics_views_require_login(self):
        """Test that analytics views require login"""
        self.client.logout()

        urls = [
            'store:supplier_monthly_analytics',
            'store:supplier_performance_dashboard',
            'store:enhanced_procurement_search',
            'store:supplier_comparison',
        ]

        for url_name in urls:
            url = reverse(url_name)
            response = self.client.get(url)
            self.assertRedirects(response, f'/login/?next={url}', status_code=302)


class SupplierAnalyticsIntegrationTestCase(TestCase):
    """Integration tests for supplier analytics with existing functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(
            mobile='9876543210',
            password='testpass123'
        )

        # Create profile
        self.profile = Profile.objects.create(
            user=self.user,
            full_name='Integration Test User',
            user_type='Admin'
        )

        self.client.login(mobile='9876543210', password='testpass123')

    def test_existing_supplier_list_functionality_preserved(self):
        """Test that existing supplier list functionality is preserved"""
        # Create a supplier
        supplier = Supplier.objects.create(
            name='Integration Test Supplier',
            phone='5555555555',
            contact_info='Integration Test Address'
        )

        # Test supplier list view
        url = reverse('store:supplier_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Integration Test Supplier')
        self.assertContains(response, 'Analytics')  # New analytics button
        self.assertContains(response, 'Performance')  # New performance button
        self.assertContains(response, 'Compare')  # New compare button

    def test_navigation_menu_includes_analytics(self):
        """Test that navigation menu includes new analytics options"""
        url = reverse('store:dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check that analytics links are in the navigation
        self.assertContains(response, 'Monthly Analytics')
        self.assertContains(response, 'Performance Dashboard')
        self.assertContains(response, 'Advanced Search')
        self.assertContains(response, 'Supplier Comparison')
