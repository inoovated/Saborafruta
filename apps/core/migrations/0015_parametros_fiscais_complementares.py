from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Campos ja adicionados pelo ramo main em 0013_parametros_fiscais_complementares.
    Usamos SeparateDatabaseAndState + ADD COLUMN IF NOT EXISTS para nao falhar
    caso as colunas ja existam.
    """

    dependencies = [
        ('core', '0014_parametros_sistema'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE parametros_sistema "
                        "ADD COLUMN IF NOT EXISTS email_envio_automatico boolean NOT NULL DEFAULT false, "
                        "ADD COLUMN IF NOT EXISTS email_resposta varchar(120) NOT NULL DEFAULT '', "
                        "ADD COLUMN IF NOT EXISTS informacoes_complementares_padrao text NOT NULL DEFAULT '', "
                        "ADD COLUMN IF NOT EXISTS nfce_csc_id varchar(20) NOT NULL DEFAULT '', "
                        "ADD COLUMN IF NOT EXISTS nfce_csc_token varchar(120) NOT NULL DEFAULT '', "
                        "ADD COLUMN IF NOT EXISTS texto_padrao_email text NOT NULL DEFAULT ''; "
                        "ALTER TABLE parametros_sistema "
                        "ALTER COLUMN email_resposta DROP DEFAULT, "
                        "ALTER COLUMN informacoes_complementares_padrao DROP DEFAULT, "
                        "ALTER COLUMN nfce_csc_id DROP DEFAULT, "
                        "ALTER COLUMN nfce_csc_token DROP DEFAULT, "
                        "ALTER COLUMN texto_padrao_email DROP DEFAULT, "
                        "ALTER COLUMN email_envio_automatico DROP DEFAULT; "
                        "ALTER TABLE parametros_documento_fiscal "
                        "ADD COLUMN IF NOT EXISTS enviar_email boolean NOT NULL DEFAULT false, "
                        "ADD COLUMN IF NOT EXISTS finalidade_nfe smallint NOT NULL DEFAULT 1, "
                        "ADD COLUMN IF NOT EXISTS indicador_consumidor_final smallint NOT NULL DEFAULT 1, "
                        "ADD COLUMN IF NOT EXISTS indicador_destino smallint NOT NULL DEFAULT 1, "
                        "ADD COLUMN IF NOT EXISTS informacoes_complementares text NOT NULL DEFAULT '', "
                        "ADD COLUMN IF NOT EXISTS modalidade_frete smallint NOT NULL DEFAULT 9, "
                        "ADD COLUMN IF NOT EXISTS presenca_comprador smallint NOT NULL DEFAULT 1, "
                        "ADD COLUMN IF NOT EXISTS tipo_operacao varchar(1) NOT NULL DEFAULT '1'; "
                        "ALTER TABLE parametros_documento_fiscal "
                        "ALTER COLUMN enviar_email DROP DEFAULT, "
                        "ALTER COLUMN finalidade_nfe DROP DEFAULT, "
                        "ALTER COLUMN indicador_consumidor_final DROP DEFAULT, "
                        "ALTER COLUMN indicador_destino DROP DEFAULT, "
                        "ALTER COLUMN informacoes_complementares DROP DEFAULT, "
                        "ALTER COLUMN modalidade_frete DROP DEFAULT, "
                        "ALTER COLUMN presenca_comprador DROP DEFAULT;"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='parametrossistema',
                    name='email_envio_automatico',
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name='parametrossistema',
                    name='email_resposta',
                    field=models.EmailField(blank=True, max_length=120),
                ),
                migrations.AddField(
                    model_name='parametrossistema',
                    name='informacoes_complementares_padrao',
                    field=models.TextField(blank=True),
                ),
                migrations.AddField(
                    model_name='parametrossistema',
                    name='nfce_csc_id',
                    field=models.CharField(blank=True, max_length=20),
                ),
                migrations.AddField(
                    model_name='parametrossistema',
                    name='nfce_csc_token',
                    field=models.CharField(blank=True, max_length=120),
                ),
                migrations.AddField(
                    model_name='parametrossistema',
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
            ],
        ),
    ]
