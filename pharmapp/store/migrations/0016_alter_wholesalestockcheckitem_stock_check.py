# Generated by Django 5.1.5 on 2025-02-08 15:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0015_alter_wholesalestockcheckitem_item'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wholesalestockcheckitem',
            name='stock_check',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wholesale_items', to='store.wholesalestockcheck'),
        ),
    ]
