from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE pedidos_venda
                    ADD COLUMN IF NOT EXISTS desconto_percentual numeric(5, 2) NOT NULL DEFAULT 0;
                    ALTER TABLE pedidos_venda
                    ADD COLUMN IF NOT EXISTS desconto_valor numeric(14, 2) NOT NULL DEFAULT 0;
                    ALTER TABLE pedidos_venda
                    ADD COLUMN IF NOT EXISTS acrescimo numeric(14, 2) NOT NULL DEFAULT 0;
                    ALTER TABLE itens_pedido_venda
                    ADD COLUMN IF NOT EXISTS desconto_percentual numeric(5, 2) NOT NULL DEFAULT 0;
                    ALTER TABLE itens_pedido_venda
                    ADD COLUMN IF NOT EXISTS desconto_valor numeric(14, 2) NOT NULL DEFAULT 0;
                    ALTER TABLE itens_pedido_venda
                    ADD COLUMN IF NOT EXISTS quantidade_reservada numeric(12, 3) NOT NULL DEFAULT 0;
                    ALTER TABLE itens_pedido_venda
                    ADD COLUMN IF NOT EXISTS quantidade_faturada numeric(12, 3) NOT NULL DEFAULT 0;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
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
        migrations.RunSQL(
            sql="""
            UPDATE pedidos_venda
               SET desconto_valor = valor_desconto,
                   acrescimo = valor_acrescimo
             WHERE desconto_valor IS DISTINCT FROM valor_desconto
                OR acrescimo IS DISTINCT FROM valor_acrescimo;
            UPDATE itens_pedido_venda
               SET desconto_percentual = percentual_desconto,
                   desconto_valor = valor_desconto,
                   quantidade_faturada = quantidade_atendida
             WHERE desconto_percentual IS DISTINCT FROM percentual_desconto
                OR desconto_valor IS DISTINCT FROM valor_desconto
                OR quantidade_faturada IS DISTINCT FROM quantidade_atendida;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
