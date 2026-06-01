from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0005_entrada_nf_parcelas'),
    ]

    operations = [
        migrations.AddField(
            model_name='entradanf',
            name='custo_rateio_metodo',
            field=models.CharField(
                choices=[
                    ('valor', 'Valor dos itens'),
                    ('quantidade', 'Quantidade'),
                    ('peso', 'Peso'),
                ],
                default='valor',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='custo_incluir_ipi',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='custo_incluir_icms_st',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='custo_incluir_icms',
            field=models.BooleanField(
                default=False,
                help_text='Marcar apenas quando o ICMS normal nao for recuperavel.',
            ),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='custo_financeiro',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='custo_composto_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
