# Generated by Django 5.1.5 on 2025-02-16 10:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0022_remove_transferrequest_approved_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transferrequest',
            name='retail_item',
            field=models.ForeignKey(blank=True, help_text='Set when request originates from retail side.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='retail_items', to='store.item'),
        ),
        migrations.AlterField(
            model_name='transferrequest',
            name='wholesale_item',
            field=models.ForeignKey(blank=True, help_text='Set when request originates from wholesale side.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='wholesale_items', to='store.wholesaleitem'),
        ),
    ]
