from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscal', '0002_manifesto_certificado_metadados'),
    ]

    operations = [
        migrations.AddField(
            model_name='manifestofiscalconfig',
            name='max_nsu',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
