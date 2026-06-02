from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0010_entrada_nf_custo_usar_apenas_valor_nota'),
    ]

    operations = [
        migrations.AddField(
            model_name='itementradanf',
            name='custo_unitario_manual',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text='Custo unitario agregado informado manualmente na tela de custos.',
                max_digits=14,
                null=True,
            ),
        ),
    ]
