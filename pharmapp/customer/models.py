from django.utils import timezone
from django.db import models
from userauth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver




# Create your models here.
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return f'{self.user.username if self.user else "No User"} {self.name} {self.phone} {self.address}'


@receiver(post_save, sender=Customer)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(customer=instance)


class Wallet(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.customer.name}'s wallet - balance {self.balance}"
    
    def add_funds(self, amount):
        self.balance += amount
        self.save()
        # Save transaction history
        TransactionHistory.objects.create(
            customer=self.customer,
            transaction_type='deposit',
            amount=amount,
            description='Funds added to wallet'
        )
    
    def reset_wallet(self):
        self.balance = 0
        self.save()



class WholesaleCustomer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return f'{self.user.username if self.user else "No User"} {self.name} {self.phone} {self.address}'


@receiver(post_save, sender=WholesaleCustomer)
def create_wholesale_wallet(sender, instance, created, **kwargs):
    if created:
        WholesaleCustomerWallet.objects.create(customer=instance)





class WholesaleCustomerWallet(models.Model):
    customer = models.OneToOneField(WholesaleCustomer, on_delete=models.CASCADE, related_name='wholesale_customer_wallet', unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.customer.name}'s wallet - balance {self.balance}"
    
    def add_funds(self, amount):
        self.balance += amount
        self.save()
        # Save transaction history
        TransactionHistory.objects.create(
            wholesale_customer=self.customer,
            transaction_type='deposit',
            amount=amount,
            description='Funds added to wallet'
        )
    
    def reset_wallet(self):
        self.balance = 0
        self.save()




class TransactionHistory(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('debit', 'Debit'),
        ('deposit', 'Deposit'),
        ('refund', 'Refund'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    wholesale_customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, related_name='wholesale_transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    description = models.TextField(null=True, blank=True)  # Optional field to describe the transaction

    def __str__(self):
        name = self.customer.name if self.customer else self.wholesale_customer.name
        return f"{name} - {self.transaction_type} - {self.amount} on {self.date}"
