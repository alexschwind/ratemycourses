# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_rating_additional_notes_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rating',
            name='additional_notes',
        ),
    ]
