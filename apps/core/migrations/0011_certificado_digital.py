from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Colunas certificado_digital e senha_certificado ja foram adicionadas
    pelo ramo main (0016_parametros_certificado_digital). Usamos
    SeparateDatabaseAndState para apenas atualizar o estado do Django.
    """

    dependencies = [
        ('core', '0010_parametros_sistema'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='parametrossistema',
                    name='certificado_digital',
                    field=models.FileField(
                        blank=True,
                        null=True,
                        upload_to='sistema/certificados/',
                        help_text='Arquivo do certificado digital (.pfx ou .p12).',
                    ),
                ),
                migrations.AddField(
                    model_name='parametrossistema',
                    name='senha_certificado',
                    field=models.CharField(
                        blank=True,
                        max_length=255,
                        help_text='Senha do certificado digital.',
                    ),
                ),
            ],
        ),
    ]
