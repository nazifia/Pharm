# Generated by Django 5.1.5 on 2025-02-08 14:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0012_stockcheckitem_approved_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stockcheckitem',
            name='notes',
        ),
        migrations.AddField(
            model_name='wholesalestockcheck',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='wholesalestockcheck',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='wholesalestockcheckitem',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='wholesalestockcheckitem',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='wholesalestockcheckitem',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('adjusted', 'Adjusted')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='wholesalestockcheck',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wholesale_items', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='wholesalestockcheck',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='wholesalestockcheckitem',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.item'),
        ),
        migrations.AlterField(
            model_name='wholesalestockcheckitem',
            name='stock_check',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.wholesalestockcheck'),
        ),
    ]
