from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0013_usernotification_usermailboxmessage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='image',
            field=models.ImageField(blank=True, max_length=255, null=True, upload_to='categories/'),
        ),
        migrations.AlterField(
            model_name='homeheroslide',
            name='image',
            field=models.ImageField(blank=True, max_length=255, null=True, upload_to='hero/'),
        ),
    ]
