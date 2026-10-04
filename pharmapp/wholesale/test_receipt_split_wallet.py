from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from customer.models import TransactionHistory, WholesaleCustomer
from store.models import WholesaleCart, WholesaleItem, WholesaleReceipt, WholesaleReceiptPayment
from userauth.models import User


@override_settings(SUBSCRIPTION_BYPASS_MOBILE='0800000002')
class WholesaleReceiptSplitWallet(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(mobile='0800000002', username='admin', password='pw')
        self.client.force_login(self.user)
        self.customer = WholesaleCustomer.objects.create(name='Acme', phone='1', address='Lagos')
        self.wallet = self.customer.wholesale_customer_wallet  # created by signal
        self.wallet.balance = Decimal('100.00')
        self.wallet.save()
        self.item = WholesaleItem.objects.create(name='X', cost=10, price=10, markup=0, stock=10, unit='Tab')
        WholesaleCart.objects.create(user=self.user, item=self.item, quantity=5, price=self.item.price, unit='Tab')
        s = self.client.session
        s['user_data'] = {f'user_{self.user.id}_customer_id': self.customer.id}
        s.save()

    def _post(self, **data):
        base = {'payment_type': 'split', 'split_status': 'Paid'}
        base.update(data)
        return self.client.post(reverse('wholesale:wholesale_receipt'), base)

    def _balance(self):
        self.wallet.refresh_from_db()
        return self.wallet.balance

    def test_split_wallet_and_cash(self):
        r = self._post(payment_method_1='Wallet', payment_amount_1='30',
                       payment_method_2='Cash', payment_amount_2='20')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._balance(), Decimal('70.00'))
        receipt = WholesaleReceipt.objects.get()
        self.assertEqual(receipt.payment_method, 'Split')
        self.assertEqual(WholesaleReceiptPayment.objects.filter(receipt=receipt).count(), 2)
        h = TransactionHistory.objects.get()
        self.assertEqual((h.amount, h.user, h.transaction_type), (Decimal('30.00'), self.user, 'purchase'))
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 5)
        self.assertFalse(WholesaleCart.objects.exists())

    def test_split_wallet_both_halves(self):
        self._post(payment_method_1='Wallet', payment_amount_1='10',
                   payment_method_2='Wallet', payment_amount_2='15')
        self.assertEqual(self._balance(), Decimal('75.00'))
        self.assertEqual(TransactionHistory.objects.count(), 2)
        self.assertTrue(all(t.user == self.user for t in TransactionHistory.objects.all()))

    def test_split_wallet_goes_negative_sets_flag(self):
        self._post(payment_method_1='Wallet', payment_amount_1='120',
                   payment_method_2='Cash', payment_amount_2='0')
        self.assertEqual(self._balance(), Decimal('-20.00'))
        self.assertTrue(WholesaleReceipt.objects.get().wallet_went_negative)

    def test_split_without_wallet_leaves_balance(self):
        self._post(payment_method_1='Cash', payment_amount_1='30',
                   payment_method_2='Transfer', payment_amount_2='20')
        self.assertEqual(self._balance(), Decimal('100.00'))
        self.assertFalse(TransactionHistory.objects.exists())

    def test_split_missing_method_redirects_without_receipt(self):
        r = self._post(payment_method_1='Wallet', payment_amount_1='30')
        self.assertRedirects(r, reverse('wholesale:wholesale_cart'), fetch_redirect_response=False)
        self.assertEqual(self._balance(), Decimal('100.00'))
        self.assertFalse(WholesaleReceipt.objects.exists())


@override_settings(SUBSCRIPTION_BYPASS_MOBILE='0800000002')
class CashierCompleteSplitWallet(TestCase):
    def setUp(self):
        from store.models import PaymentRequest, PaymentRequestItem
        self.user = User.objects.create_superuser(mobile='0800000002', username='admin', password='pw')
        self.client.force_login(self.user)
        self.customer = WholesaleCustomer.objects.create(name='Acme', phone='1', address='Lagos')
        self.wallet = self.customer.wholesale_customer_wallet
        self.wallet.balance = Decimal('100.00')
        self.wallet.save()
        item = WholesaleItem.objects.create(name='X', cost=10, price=10, markup=0, stock=10, unit='Tab')
        self.pr = PaymentRequest.objects.create(
            dispenser=self.user, wholesale_customer=self.customer, payment_type='wholesale',
            total_amount=Decimal('50.00'), status='accepted')
        PaymentRequestItem.objects.create(
            payment_request=self.pr, item_name='X', unit='Tab', quantity=5, unit_price=10,
            subtotal=50, wholesale_item=item)

    def _post(self, **data):
        return self.client.post(reverse('wholesale:complete_payment_request', args=[self.pr.request_id]), data)

    def test_split_wallet_wallet(self):
        self._post(payment_type='split', payment_method_1='Wallet', payment_amount_1='20',
                   payment_method_2='Wallet', payment_amount_2='30')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('50.00'))
        self.assertEqual(TransactionHistory.objects.count(), 2)
        self.assertEqual(WholesaleReceiptPayment.objects.count(), 2)

    def test_single_wallet(self):
        self._post(payment_type='single', payment_method='Wallet')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('50.00'))
        self.assertEqual(TransactionHistory.objects.get().amount, Decimal('50.00'))
        self.assertEqual(WholesaleReceiptPayment.objects.get().payment_method, 'Wallet')

    def test_split_wallet_cash_negative_flag(self):
        self.wallet.balance = Decimal('10.00')
        self.wallet.save()
        self._post(payment_type='split', payment_method_1='Wallet', payment_amount_1='20',
                   payment_method_2='Cash', payment_amount_2='30')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('-10.00'))
        self.assertTrue(WholesaleReceipt.objects.get().wallet_went_negative)


class DetailSplitFallback(TestCase):
    def test_detail_creates_default_split_payments(self):
        from store.models import Sales
        user = User.objects.create_superuser(mobile='0800000003', username='a2', password='pw')
        with override_settings(SUBSCRIPTION_BYPASS_MOBILE='0800000003'):
            self.client.force_login(user)
            sales = Sales.objects.create(user=user, total_amount=0)
            r = WholesaleReceipt.objects.create(sales=sales, total_amount=0, payment_method='Split', buyer_name='W')
            self.client.get(reverse('wholesale:wholesale_receipt_detail', args=[r.receipt_id]))
        self.assertEqual(
            sorted(WholesaleReceiptPayment.objects.filter(receipt=r).values_list('payment_method', flat=True)),
            ['Cash', 'Transfer'])
