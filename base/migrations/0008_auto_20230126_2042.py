# Generated by Django 3.2 on 2023-01-27 01:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_alter_event_draft_date'),
    ]

    operations = [
        migrations.RenameField(
            model_name='event',
            old_name='draft_date',
            new_name='draft_end_date',
        ),
        migrations.AddField(
            model_name='event',
            name='draft_start_date',
            field=models.DateTimeField(null=True),
        ),
    ]
