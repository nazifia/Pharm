# Generated by Django 5.1.5 on 2025-07-23 15:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0056_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Discount amount to be subtracted from subtotal', max_digits=12),
        ),
        migrations.AddField(
            model_name='salesitem',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Discount amount applied to this item', max_digits=10),
        ),
    ]
