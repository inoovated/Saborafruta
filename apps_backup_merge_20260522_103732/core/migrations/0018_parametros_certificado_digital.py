from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_rename_registros_a_modulo'),
    ]

    operations = [
        migrations.AddField(
            model_name='parametrossistema',
            name='certificado_digital',
            field=models.FileField(
                blank=True,
                help_text='Arquivo do certificado digital A1 (.pfx ou .p12).',
                null=True,
                upload_to='sistema/certificados/',
            ),
        ),
        migrations.AddField(
            model_name='parametrossistema',
            name='senha_certificado',
            field=models.CharField(
                blank=True,
                help_text='Senha do certificado digital. Use apenas em ambiente controlado.',
                max_length=255,
            ),
        ),
    ]
