# Generated by Django 5.1.7 on 2025-03-09 10:10

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0032_alter_receipt_sales'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='salesitem',
            name='brand',
        ),
        migrations.RemoveField(
            model_name='salesitem',
            name='dosage_form',
        ),
        migrations.RemoveField(
            model_name='salesitem',
            name='unit',
        ),
        migrations.AlterField(
            model_name='salesitem',
            name='quantity',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='salesitem',
            name='sales',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='store.sales'),
        ),
        migrations.AddConstraint(
            model_name='salesitem',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gte', 0)), name='quantity_not_negative'),
        ),
    ]
