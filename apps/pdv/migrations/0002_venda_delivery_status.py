from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Campos status_delivery, observacao_delivery e entregador ja foram
    adicionados pelo ramo main em pdv.0004_venda_delivery_status.
    Usamos SeparateDatabaseAndState + ADD COLUMN IF NOT EXISTS para nao falhar.
    """

    dependencies = [
        ('pdv', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE vendas_pdv "
                        "ADD COLUMN IF NOT EXISTS status_delivery varchar(20) NOT NULL DEFAULT 'novo', "
                        "ADD COLUMN IF NOT EXISTS observacao_delivery text NOT NULL DEFAULT '', "
                        "ADD COLUMN IF NOT EXISTS entregador varchar(100) NOT NULL DEFAULT ''; "
                        "ALTER TABLE vendas_pdv "
                        "ALTER COLUMN status_delivery DROP DEFAULT, "
                        "ALTER COLUMN observacao_delivery DROP DEFAULT, "
                        "ALTER COLUMN entregador DROP DEFAULT;"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='vendapdv',
                    name='status_delivery',
                    field=models.CharField(
                        blank=True,
                        choices=[
                            ('novo', 'Novo Pedido'),
                            ('preparando', 'Em Preparo'),
                            ('em_entrega', 'Saiu para Entrega'),
                            ('entregue', 'Entregue'),
                            ('cancelado', 'Cancelado'),
                        ],
                        default='novo',
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='vendapdv',
                    name='observacao_delivery',
                    field=models.TextField(blank=True),
                ),
                migrations.AddField(
                    model_name='vendapdv',
                    name='entregador',
                    field=models.CharField(blank=True, max_length=100),
                ),
            ],
        ),
    ]
