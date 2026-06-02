from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0013_produto_gerado_custo_manual'),
    ]

    operations = [
        migrations.AddField(
            model_name='itementradanf',
            name='quantidade_xml_original',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text='Quantidade original da nota antes de ajuste manual na conferencia.',
                max_digits=12,
                null=True,
            ),
        ),
    ]
