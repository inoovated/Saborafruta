import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    FormaPagamento.empresa ja existe desde financeiro.0002_initial.
    Usamos SeparateDatabaseAndState para apenas atualizar o estado do Django.
    """

    dependencies = [
        ('core', '0001_initial'),
        ('financeiro', '0002_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
            ],
        ),
    ]
