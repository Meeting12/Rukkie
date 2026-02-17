from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_product_auto_metadata'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='auto_metadata',
        ),
    ]
