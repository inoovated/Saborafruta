from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0012_categoria_regra_todas_categorias'),
    ]

    operations = [
        migrations.AddField(
            model_name='kitcategoriaregra',
            name='tipo_desconto',
            field=models.CharField(
                choices=[
                    ('preco_unitario', 'Preco unitario'),
                    ('percentual', 'Percentual'),
                    ('valor', 'Valor em R$'),
                    ('preco_final', 'Preco final'),
                ],
                default='percentual',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='kitcategoriaregra',
            name='valor_desconto',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14),
        ),
    ]
