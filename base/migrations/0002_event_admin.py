# Generated by Django 4.1.5 on 2023-01-22 05:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='admin',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_of', to=settings.AUTH_USER_MODEL),
        ),
    ]