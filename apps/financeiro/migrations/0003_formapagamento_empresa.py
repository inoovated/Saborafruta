import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('financeiro', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='formapagamento',
            name='empresa',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='formas_pagamento',
                to='core.empresa',
            ),
            preserve_default=False,
        ),
    ]
