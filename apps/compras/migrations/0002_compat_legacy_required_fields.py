from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE pedidos_compra
                    ADD COLUMN IF NOT EXISTS frete_valor numeric(14, 2) NOT NULL DEFAULT 0;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql="""
                    ALTER TABLE itens_entrada_nf
                    ADD COLUMN IF NOT EXISTS custo_unitario_total numeric(14, 4) NOT NULL DEFAULT 0;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
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
        migrations.RunSQL(
            sql="""
            UPDATE pedidos_compra
               SET frete_valor = valor_frete
             WHERE frete_valor IS DISTINCT FROM valor_frete;
            UPDATE itens_entrada_nf
               SET custo_unitario_total =
                   valor_unitario + CASE
                       WHEN quantidade <> 0 THEN valor_ipi / quantidade
                       ELSE 0
                   END
             WHERE custo_unitario_total IS DISTINCT FROM (
                   valor_unitario + CASE
                       WHEN quantidade <> 0 THEN valor_ipi / quantidade
                       ELSE 0
                   END
             );
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
