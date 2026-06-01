from django.db import migrations, models


def _colunas(connection, tabela):
    return {
        coluna.name
        for coluna in connection.introspection.get_table_description(
            connection.cursor(), tabela,
        )
    }


def criar_colunas_legadas(apps, schema_editor):
    connection = schema_editor.connection
    colunas_pedido = _colunas(connection, 'pedidos_compra')
    colunas_item = _colunas(connection, 'itens_entrada_nf')
    with connection.cursor() as cursor:
        if 'frete_valor' not in colunas_pedido:
            cursor.execute(
                'ALTER TABLE pedidos_compra '
                'ADD COLUMN frete_valor numeric(14, 2) NOT NULL DEFAULT 0'
            )
        if 'custo_unitario_total' not in colunas_item:
            cursor.execute(
                'ALTER TABLE itens_entrada_nf '
                'ADD COLUMN custo_unitario_total numeric(14, 4) NOT NULL DEFAULT 0'
            )


def sincronizar_colunas_legadas(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pedidos_compra
               SET frete_valor = valor_frete
             WHERE frete_valor <> valor_frete
            """
        )
        cursor.execute(
            """
            UPDATE itens_entrada_nf
               SET custo_unitario_total =
                   valor_unitario + CASE
                       WHEN quantidade <> 0 THEN valor_ipi / quantidade
                       ELSE 0
                   END
             WHERE custo_unitario_total <> (
                   valor_unitario + CASE
                       WHEN quantidade <> 0 THEN valor_ipi / quantidade
                       ELSE 0
                   END
             )
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(criar_colunas_legadas, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='pedidocompra',
                    name='frete_valor',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text='Campo legado mantido em sincronia com valor_frete.',
                        max_digits=14,
                    ),
                ),
                migrations.AddField(
                    model_name='itementradanf',
                    name='custo_unitario_total',
                    field=models.DecimalField(
                        decimal_places=4,
                        default=0,
                        help_text='Campo legado: custo unitario final com rateios.',
                        max_digits=14,
                    ),
                ),
            ],
        ),
        migrations.RunPython(sincronizar_colunas_legadas, migrations.RunPython.noop),
    ]
