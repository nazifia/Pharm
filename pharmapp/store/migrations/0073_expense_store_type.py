from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0072_add_buyer_info_to_payment_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='store_type',
            field=models.CharField(
                choices=[
                    ('retail', 'Retail'),
                    ('wholesale', 'Wholesale'),
                    ('general', 'General (Both)'),
                ],
                default='general',
                help_text='Which store this expense belongs to',
                max_length=10,
            ),
        ),
    ]
