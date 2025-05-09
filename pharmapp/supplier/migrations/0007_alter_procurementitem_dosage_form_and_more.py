# Generated by Django 5.1.7 on 2025-04-24 21:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supplier', '0006_alter_procurementitem_dosage_form_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='procurementitem',
            name='dosage_form',
            field=models.CharField(choices=[('Tablet', 'Tablet'), ('Capsule', 'Capsule'), ('Cream', 'Cream'), ('Consumable', 'Consumable'), ('Galenical', 'Galenical'), ('Injection', 'Injection'), ('Infusion', 'Infusion'), ('Inhaler', 'Inhaler'), ('Suspension', 'Suspension'), ('Syrup', 'Syrup'), ('Drops', 'Drops'), ('Solution', 'Solution'), ('Eye-drop', 'Eye-drop'), ('Ear-drop', 'Ear-drop'), ('Eye-ointment', 'Eye-ointment'), ('Rectal', 'Rectal'), ('Vaginal', 'Vaginal'), ('Detergent', 'Detergent'), ('Drinks', 'Drinks'), ('Paste', 'Paste'), ('Patch', 'Patch'), ('Table-water', 'Table-water'), ('Food-item', 'Food-item'), ('Sweets', 'Sweets'), ('Soaps', 'Soaps'), ('Biscuits', 'Biscuits')], default='dosage_form', max_length=255),
        ),
        migrations.AlterField(
            model_name='wholesaleprocurementitem',
            name='dosage_form',
            field=models.CharField(choices=[('Tablet', 'Tablet'), ('Capsule', 'Capsule'), ('Cream', 'Cream'), ('Consumable', 'Consumable'), ('Galenical', 'Galenical'), ('Injection', 'Injection'), ('Infusion', 'Infusion'), ('Inhaler', 'Inhaler'), ('Suspension', 'Suspension'), ('Syrup', 'Syrup'), ('Drops', 'Drops'), ('Solution', 'Solution'), ('Eye-drop', 'Eye-drop'), ('Ear-drop', 'Ear-drop'), ('Eye-ointment', 'Eye-ointment'), ('Rectal', 'Rectal'), ('Vaginal', 'Vaginal'), ('Detergent', 'Detergent'), ('Drinks', 'Drinks'), ('Paste', 'Paste'), ('Patch', 'Patch'), ('Table-water', 'Table-water'), ('Food-item', 'Food-item'), ('Sweets', 'Sweets'), ('Soaps', 'Soaps'), ('Biscuits', 'Biscuits')], default='dosage_form', max_length=255),
        ),
    ]
