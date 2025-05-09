# Generated by Django 5.1.7 on 2025-04-17 06:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0039_wholesalesettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wholesaleitem',
            name='low_stock_threshold',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=6, null=True),
        ),
        migrations.AlterField(
            model_name='wholesaleitem',
            name='stock',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=6, null=True),
        ),
    ]
