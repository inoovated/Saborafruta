from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_politicareplicacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='filial',
            name='participa_replicacao',
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text='Define se esta filial envia e recebe cadastros replicados.',
            ),
        ),
    ]
