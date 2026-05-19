from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0016_promocao_quantidade_preco_promocional'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='promocao_tipo_desconto',
            field=models.CharField(
                choices=[
                    ('preco_final', 'Preco final'),
                    ('percentual', 'Percentual'),
                    ('valor', 'Valor em R$'),
                ],
                default='preco_final',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='produto',
            name='promocao_valor_desconto',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14),
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE produtos "
                "SET promocao_valor_desconto = preco_promocional "
                "WHERE preco_promocional IS NOT NULL AND preco_promocional > 0"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
