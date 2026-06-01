# Generated manually to keep product/replication changes scoped.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_filial_participa_replicacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='politicareplicacao',
            name='replicar_marcas',
            field=models.BooleanField(default=False),
        ),
    ]
