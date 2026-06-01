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
    colunas_pedido = _colunas(connection, 'pedidos_venda')
    colunas_item = _colunas(connection, 'itens_pedido_venda')
    with connection.cursor() as cursor:
        for nome, ddl in {
            'desconto_percentual': 'desconto_percentual numeric(5, 2) NOT NULL DEFAULT 0',
            'desconto_valor': 'desconto_valor numeric(14, 2) NOT NULL DEFAULT 0',
            'acrescimo': 'acrescimo numeric(14, 2) NOT NULL DEFAULT 0',
        }.items():
            if nome not in colunas_pedido:
                cursor.execute(f'ALTER TABLE pedidos_venda ADD COLUMN {ddl}')
        for nome, ddl in {
            'desconto_percentual': 'desconto_percentual numeric(5, 2) NOT NULL DEFAULT 0',
            'desconto_valor': 'desconto_valor numeric(14, 2) NOT NULL DEFAULT 0',
            'quantidade_reservada': 'quantidade_reservada numeric(12, 3) NOT NULL DEFAULT 0',
            'quantidade_faturada': 'quantidade_faturada numeric(12, 3) NOT NULL DEFAULT 0',
        }.items():
            if nome not in colunas_item:
                cursor.execute(f'ALTER TABLE itens_pedido_venda ADD COLUMN {ddl}')


def sincronizar_colunas_legadas(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pedidos_venda
               SET desconto_valor = valor_desconto,
                   acrescimo = valor_acrescimo
             WHERE desconto_valor <> valor_desconto
                OR acrescimo <> valor_acrescimo
            """
        )
        cursor.execute(
            """
            UPDATE itens_pedido_venda
               SET desconto_percentual = percentual_desconto,
                   desconto_valor = valor_desconto,
                   quantidade_faturada = quantidade_atendida
             WHERE desconto_percentual <> percentual_desconto
                OR desconto_valor <> valor_desconto
                OR quantidade_faturada <> quantidade_atendida
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(criar_colunas_legadas, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='pedidovenda',
                    name='desconto_percentual',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text='Campo legado mantido para compatibilidade do banco.',
                        max_digits=5,
                    ),
                ),
                migrations.AddField(
                    model_name='pedidovenda',
                    name='desconto_valor',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text='Campo legado mantido em sincronia com valor_desconto.',
                        max_digits=14,
                    ),
                ),
                migrations.AddField(
                    model_name='pedidovenda',
                    name='acrescimo',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text='Campo legado mantido em sincronia com valor_acrescimo.',
                        max_digits=14,
                    ),
                ),
                migrations.AddField(
                    model_name='itempedidovenda',
                    name='desconto_percentual',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text='Campo legado mantido em sincronia com percentual_desconto.',
                        max_digits=5,
                    ),
                ),
                migrations.AddField(
                    model_name='itempedidovenda',
                    name='desconto_valor',
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text='Campo legado mantido em sincronia com valor_desconto.',
                        max_digits=14,
                    ),
                ),
                migrations.AddField(
                    model_name='itempedidovenda',
                    name='quantidade_reservada',
                    field=models.DecimalField(
                        decimal_places=3,
                        default=0,
                        help_text='Campo legado sincronizado ao confirmar/liberar reserva.',
                        max_digits=12,
                    ),
                ),
                migrations.AddField(
                    model_name='itempedidovenda',
                    name='quantidade_faturada',
                    field=models.DecimalField(
                        decimal_places=3,
                        default=0,
                        help_text='Campo legado sincronizado ao faturar o pedido.',
                        max_digits=12,
                    ),
                ),
            ],
        ),
        migrations.RunPython(sincronizar_colunas_legadas, migrations.RunPython.noop),
    ]
