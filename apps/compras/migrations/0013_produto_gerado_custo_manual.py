from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0012_itementradanfprodutogerado'),
    ]

    operations = [
        migrations.AddField(
            model_name='itementradanfprodutogerado',
            name='custo_unitario_manual',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text='Custo unitario agregado informado manualmente para este produto gerado.',
                max_digits=14,
                null=True,
            ),
        ),
    ]
