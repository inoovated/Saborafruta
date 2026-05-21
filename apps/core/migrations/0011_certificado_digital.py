from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_parametros_sistema'),
    ]

    operations = [
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
    ]
