# Generated by Django 5.1.7 on 2025-04-26 06:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0052_alter_item_dosage_form_alter_item_unit_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='receipt',
            name='status',
            field=models.CharField(choices=[('Paid', 'Paid'), ('Partially Paid', 'Partially Paid'), ('Unpaid', 'Unpaid')], default='Paid', max_length=20),
        ),
        migrations.AlterField(
            model_name='wholesalereceipt',
            name='status',
            field=models.CharField(choices=[('Paid', 'Paid'), ('Partially Paid', 'Partially Paid'), ('Unpaid', 'Unpaid')], default='Paid', max_length=20),
        ),
    ]
