from django.db import migrations, models


def copiar_regime_empresa_para_filial(apps, schema_editor):
    Filial = apps.get_model('core', 'Filial')
    for filial in Filial.objects.select_related('empresa').all():
        filial.regime_tributario = filial.empresa.regime_tributario
        filial.codigo_regime_tributario = filial.empresa.codigo_regime_tributario
        filial.save(update_fields=['regime_tributario', 'codigo_regime_tributario'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_alter_politicareplicacaofilial_created_at_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE filiais "
                    "ADD COLUMN IF NOT EXISTS regime_tributario varchar(20) NOT NULL DEFAULT ''; "
                    "ALTER TABLE filiais ALTER COLUMN regime_tributario DROP DEFAULT;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    "ALTER TABLE filiais "
                    "ADD COLUMN IF NOT EXISTS codigo_regime_tributario smallint NULL;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='filial',
                    name='regime_tributario',
                    field=models.CharField(
                        blank=True,
                        choices=[
                            ('simples_nacional', 'Simples Nacional'),
                            ('lucro_presumido', 'Lucro Presumido'),
                            ('lucro_real', 'Lucro Real'),
                            ('mei', 'MEI'),
                        ],
                        help_text='Regime fiscal especifico da filial. Se vazio, usa o regime da empresa.',
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='filial',
                    name='codigo_regime_tributario',
                    field=models.SmallIntegerField(
                        blank=True,
                        help_text='1=SN 2=SN_excesso 3=Normal. Se vazio, usa o codigo da empresa.',
                        null=True,
                    ),
                ),
            ],
        ),
        migrations.RunPython(copiar_regime_empresa_para_filial, migrations.RunPython.noop),
    ]
