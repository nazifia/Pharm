from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from store.models import Cart, Item
from userauth.models import User


@override_settings(SUBSCRIPTION_BYPASS_MOBILE='0800000001')
class AddItemAndDispenseFlow(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(mobile='0800000001', username='admin', password='pw')
        self.client.force_login(self.user)
        self.hx = {'HTTP_HX_REQUEST': 'true'}

    def _add_item(self, **overrides):
        data = {'name': 'Paracetamol', 'cost': '100', 'markup': '10', 'stock': '5',
                'exp_date': '2030-01-01', 'unit': 'Tab'}
        data.update(overrides)
        return self.client.post(reverse('store:add_item'), data, **self.hx)

    def test_add_item_empty_price_no_override(self):
        r = self._add_item(price='')  # used to raise Decimal(None)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Item.objects.get().price, Decimal('110.00'))

    def test_add_item_manual_price_override(self):
        r = self._add_item(price='150', manual_price_override='on')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Item.objects.get().price, Decimal('150.00'))

    def test_add_item_invalid_returns_422_json(self):
        r = self._add_item(cost='')
        self.assertEqual(r.status_code, 422)
        self.assertIn('cost', r.json()['errors'])
        self.assertEqual(Item.objects.count(), 0)

    def test_new_item_visible_in_dispense_search_immediately(self):
        self.client.get(reverse('store:dispense_search_items'), {'q': 'para'}, **self.hx)
        self._add_item()
        r = self.client.get(reverse('store:dispense_search_items'), {'q': 'para'}, **self.hx)
        self.assertContains(r, 'Paracetamol')

    def test_add_to_cart_over_stock_hx_returns_widget_with_error(self):
        item = Item.objects.create(name='X', cost=1, markup=0, stock=2, unit='Tab')
        url = reverse('store:add_to_cart', args=[item.id]) + '?from_dispense=true'
        r = self.client.post(url, {'quantity': '5', 'unit': 'Tab'}, **self.hx)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Not enough stock')
        self.assertContains(r, 'id="cart-summary-widget"')
        self.assertEqual(Cart.objects.count(), 0)
        r = self.client.post(url, {'quantity': 'abc', 'unit': 'Tab'}, **self.hx)
        self.assertContains(r, 'Invalid quantity')

    def test_receipt_refuses_when_stock_short(self):
        item = Item.objects.create(name='X', cost=1, markup=0, stock=1, unit='Tab')
        Cart.objects.create(user=self.user, item=item, quantity=3, price=item.price, unit='Tab')
        r = self.client.post(reverse('store:receipt'), {'payment_method': 'Cash', 'status': 'Paid'})
        self.assertRedirects(r, reverse('store:cart'), fetch_redirect_response=False)
        item.refresh_from_db()
        self.assertEqual(item.stock, 1)

    def test_receipt_stock_decrement_is_conditional_and_rolls_back(self):
        from unittest.mock import patch
        from store.models import Sales
        item = Item.objects.create(name='X', cost=1, markup=0, stock=3, unit='Tab')
        Cart.objects.create(user=self.user, item=item, quantity=3, price=item.price, unit='Tab')
        # Simulate another cashier selling 1 unit after the pre-check but before the decrement
        real_create = Sales.objects.create
        def steal_then_create(**kw):
            Item.objects.filter(pk=item.pk).update(stock=2)
            return real_create(**kw)
        with patch.object(Sales.objects, 'create', side_effect=steal_then_create):
            r = self.client.post(reverse('store:receipt'), {'payment_method': 'Cash', 'status': 'Paid'})
        self.assertRedirects(r, reverse('store:cart'), fetch_redirect_response=False)
        item.refresh_from_db()
        self.assertEqual(item.stock, 3)  # whole receipt transaction rolled back, nothing deducted
        self.assertEqual(Sales.objects.count(), 0)  # rolled back, no orphan sale

    def test_receipt_happy_path_deducts_stock(self):
        item = Item.objects.create(name='X', cost=1, markup=0, stock=3, unit='Tab')
        Cart.objects.create(user=self.user, item=item, quantity=2, price=item.price, unit='Tab')
        r = self.client.post(reverse('store:receipt'), {'payment_method': 'Cash', 'status': 'Paid'})
        self.assertEqual(r.status_code, 200, getattr(r, 'url', None))
        item.refresh_from_db()
        self.assertEqual(item.stock, 1)
        self.assertEqual(Cart.objects.count(), 0)
