from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0043_merge_20250418_1943'),
    ]

    operations = [
        migrations.AlterField(
            model_name='salesitem',
            name='quantity',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name='wholesalesalesitem',
            name='quantity',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
    ]
