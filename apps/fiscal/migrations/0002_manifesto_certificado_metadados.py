from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscal', '0001_manifesto_fiscal_base'),
    ]

    operations = [
        migrations.AddField(
            model_name='manifestofiscalconfig',
            name='certificado_cnpj',
            field=models.CharField(blank=True, max_length=14),
        ),
        migrations.AddField(
            model_name='manifestofiscalconfig',
            name='certificado_emissor',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='manifestofiscalconfig',
            name='certificado_thumbprint',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='manifestofiscalconfig',
            name='certificado_titular',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='manifestofiscalconfig',
            name='certificado_validade_fim',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manifestofiscalconfig',
            name='certificado_validade_inicio',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
