from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0009_item_entrada_cfop_xml'),
    ]

    operations = [
        migrations.AddField(
            model_name='entradanf',
            name='custo_usar_apenas_valor_nota',
            field=models.BooleanField(
                default=False,
                help_text='Ignora frete, seguro, adicionais, impostos e custo extra no custo agregado.',
            ),
        ),
    ]
