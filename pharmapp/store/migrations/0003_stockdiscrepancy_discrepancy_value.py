# Generated by Django 5.1.5 on 2025-02-06 12:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_stockcheck_stockdiscrepancy'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockdiscrepancy',
            name='discrepancy_value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
