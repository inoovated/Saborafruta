from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_fix_certificado_digital_coluna'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE parametros_sistema ADD COLUMN IF NOT EXISTS logo_url varchar(500) NOT NULL DEFAULT '';",
            reverse_sql="ALTER TABLE parametros_sistema DROP COLUMN IF EXISTS logo_url;",
        ),
        migrations.AddField(
            model_name='parametrossistema',
            name='logo_url',
            field=models.URLField(blank=True, help_text='URL externa da logo (alternativa ao upload). Não desaparece em redeploys.', max_length=500),
        ),
    ]
