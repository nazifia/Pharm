# Generated by Django 5.1.5 on 2025-02-17 14:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('supplier', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='procurementitem',
            name='exp_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='procurementitem',
            name='markup',
            field=models.FloatField(choices=[(0, 'No markup'), (2.5, '2.5% markup'), (5, '5% markup'), (7.5, '7.5% markup'), (10, '10% markup'), (12.5, '12.5% markup'), (15, '15% markup'), (17.5, '17.5% markup'), (20, '20% markup'), (22.5, '22.5% markup'), (25, '25% markup'), (27.5, '27.5% markup'), (30, '30% markup'), (32.5, '32.5% markup'), (35, '35% markup'), (37.5, '37.5% markup'), (40, '40% markup'), (42.5, '42.5% markup'), (45, '45% markup'), (47.5, '47.5% markup'), (50, '50% markup'), (57.5, '57.5% markup'), (60, '60% markup'), (62.5, '62.5% markup'), (65, '65% markup'), (67.5, '67.5% markup'), (70, '70% markup'), (72.0, '72.% markup'), (75, '75% markup'), (77.5, '77.5% markup'), (80, '80% markup'), (82.5, '82.% markup'), (85, '85% markup'), (87.5, '87.5% markup'), (90, '90% markup'), (92.0, '92.% markup'), (95, '95% markup'), (97.5, '97.5% markup'), (100, '100% markup')], default=0),
        ),
        migrations.AddField(
            model_name='wholesaleprocurementitem',
            name='exp_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='wholesaleprocurementitem',
            name='markup',
            field=models.FloatField(choices=[(0, 'No markup'), (2.5, '2.5% markup'), (5, '5% markup'), (7.5, '7.5% markup'), (10, '10% markup'), (12.5, '12.5% markup'), (15, '15% markup'), (17.5, '17.5% markup'), (20, '20% markup'), (22.5, '22.5% markup'), (25, '25% markup'), (27.5, '27.5% markup'), (30, '30% markup'), (32.5, '32.5% markup'), (35, '35% markup'), (37.5, '37.5% markup'), (40, '40% markup'), (42.5, '42.5% markup'), (45, '45% markup'), (47.5, '47.5% markup'), (50, '50% markup'), (57.5, '57.5% markup'), (60, '60% markup'), (62.5, '62.5% markup'), (65, '65% markup'), (67.5, '67.5% markup'), (70, '70% markup'), (72.0, '72.% markup'), (75, '75% markup'), (77.5, '77.5% markup'), (80, '80% markup'), (82.5, '82.% markup'), (85, '85% markup'), (87.5, '87.5% markup'), (90, '90% markup'), (92.0, '92.% markup'), (95, '95% markup'), (97.5, '97.5% markup'), (100, '100% markup')], default=0),
        ),
    ]
