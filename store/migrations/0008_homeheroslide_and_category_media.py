from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_contactmessage_newslettersubscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='categories/'),
        ),
        migrations.CreateModel(
            name='HomeHeroSlide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('badge', models.CharField(blank=True, max_length=120)),
                ('title', models.CharField(max_length=255)),
                ('title_accent', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='hero/')),
                ('cta_text', models.CharField(blank=True, max_length=80)),
                ('cta_link', models.CharField(blank=True, default='/products', max_length=255)),
                ('secondary_cta_text', models.CharField(blank=True, max_length=80)),
                ('secondary_cta_link', models.CharField(blank=True, default='/about', max_length=255)),
                ('promo', models.CharField(blank=True, max_length=120)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
