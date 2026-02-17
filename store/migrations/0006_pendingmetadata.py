from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_remove_auto_metadata'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingMetadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metadata', models.JSONField()),
                ('confidence', models.FloatField(default=0.0)),
                ('applied', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='pending_metadata', to='store.product')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
