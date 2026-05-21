from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_parametros_sistema'),
    ]

    operations = [
        migrations.AddField(
            model_name='parametrosistema',
            name='email_envio_automatico',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parametrosistema',
            name='email_resposta',
            field=models.EmailField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='parametrosistema',
            name='informacoes_complementares_padrao',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='parametrosistema',
            name='nfce_csc_id',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='parametrosistema',
            name='nfce_csc_token',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='parametrosistema',
            name='texto_padrao_email',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='enviar_email',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='finalidade_nfe',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='indicador_consumidor_final',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='indicador_destino',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='informacoes_complementares',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='modalidade_frete',
            field=models.PositiveSmallIntegerField(default=9),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='presenca_comprador',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='parametrodocumentofiscal',
            name='tipo_operacao',
            field=models.CharField(blank=True, default='1', max_length=1),
        ),
    ]
